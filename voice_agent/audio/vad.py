import os
import math
import numpy as np
import onnxruntime as ort

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "silero_vad.onnx")
_session = None

def _design_butterworth_4th_highpass(cutoff_hz=200.0, sample_rate=16000):
    """
    Designs a 4th-order Butterworth high-pass filter as 2 cascaded biquads (Direct Form II Transposed).
    Eliminates external scipy dependency and Windows DLL loading issues while maintaining high precision.
    """
    w0 = 2.0 * math.pi * cutoff_hz / sample_rate
    cos_w0 = math.cos(w0)
    sin_w0 = math.sin(w0)

    # Q factors for 4th-order Butterworth (poles at pi/8 and 3*pi/8)
    q_factors = [
        1.0 / (2.0 * math.cos(math.pi / 8.0)),       # ~0.5411961
        1.0 / (2.0 * math.cos(3.0 * math.pi / 8.0))  # ~1.3065630
    ]

    sections = []
    for q in q_factors:
        alpha = sin_w0 / (2.0 * q)
        b0 = (1.0 + cos_w0) / 2.0
        b1 = -(1.0 + cos_w0)
        b2 = (1.0 + cos_w0) / 2.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha
        b = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float32)
        a = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float32)
        sections.append((b, a))
    return sections


def get_vad_session():
    """
    Loads and returns the single global ONNX Runtime session for Silero VAD.
    The model is loaded only once across the application lifetime.
    """
    global _session
    if _session is None:
        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        _session = ort.InferenceSession(MODEL_PATH, sess_options=opts)
    return _session


class SileroVADState:
    def __init__(self, sample_rate=16000, speech_threshold=0.85, silence_threshold=0.35, 
                 silence_duration_ms_target=700, min_rms_threshold=0.035, min_speech_frames=6):
        self.sample_rate = sample_rate
        
        # 1. Stricter thresholds to ignore breathy "ahm" or weak background noises
        self.speech_threshold = speech_threshold        # Raised from 0.70 to 0.85
        self.silence_threshold = silence_threshold      # Lowered from 0.45 to 0.35 for stability
        self.silence_duration_ms_target = silence_duration_ms_target 
        
        # 2. Higher volume floor to filter out far away speakers and low room noises
        self.min_rms_threshold = min_rms_threshold      # Raised from 0.015 to 0.035
        
        # 3. Longer speech verification timeline to skip short spikes like thuds or sighs
        self.min_speech_frames = min_speech_frames      # Raised from 3 (~96ms) to 6 (~192ms)
        
        # 4. Butterworth filter coefficients to clear thuds (Cuts out sub-200Hz bass)
        self.filter_sections = _design_butterworth_4th_highpass(cutoff_hz=200.0, sample_rate=self.sample_rate)
        
        self.reset()

    @staticmethod
    def _apply_biquad(b, a, x, state):
        """
        Applies a biquad section using Direct Form II Transposed for streaming stability and continuous state.
        """
        s1, s2 = state[0], state[1]
        y = np.empty_like(x)
        b0, b1, b2 = b[0], b[1], b[2]
        a1, a2 = a[1], a[2]
        for n in range(len(x)):
            xn = x[n]
            yn = b0 * xn + s1
            s1 = b1 * xn - a1 * yn + s2
            s2 = b2 * xn - a2 * yn
            y[n] = yn
        state[0] = s1
        state[1] = s2
        return y

    def reset(self):
        """
        Resets per-user RNN hidden state, sample buffer, speaking flags, and filter states.
        """
        self.onnx_state = np.zeros((2, 1, 128), dtype=np.float32)
        self.sr_tensor = np.array(self.sample_rate, dtype=np.int64)
        self.sample_buffer = np.array([], dtype=np.float32)
        self.filter_states = [[0.0, 0.0] for _ in self.filter_sections]
        
        self.is_speaking = False
        self.continuous_silence_ms = 0
        self.speech_frames_count = 0
        self.collected_pcm_bytes = bytearray()

    def process_chunk(self, bytes_data: bytes):
        """
        Processes an incoming PCM16 16kHz audio chunk with High-Pass Filtering.
        Returns:
            tuple: (event, completed_audio_bytes)
            event: "speech_start", "speech_end", or None
        """
        if not bytes_data:
            return None, None

        # Convert raw 16-bit PCM bytes to float32 samples normalized to [-1.0, 1.0]
        pcm_int16 = np.frombuffer(bytes_data, dtype=np.int16)
        pcm_float32 = pcm_int16.astype(np.float32) / 32768.0

        # Apply High-Pass Filter to eliminate low frequency table bumps and mic taps (streaming biquads)
        filtered_pcm = pcm_float32
        for i, (b, a) in enumerate(self.filter_sections):
            filtered_pcm = self._apply_biquad(b, a, filtered_pcm, self.filter_states[i])

        # Append filtered samples to leftovers buffer
        self.sample_buffer = np.concatenate((self.sample_buffer, filtered_pcm))

        session = get_vad_session()
        window_size = 512  # 32ms window at 16kHz
        frame_duration_ms = (window_size / self.sample_rate) * 1000.0  # 32.0 ms

        event = None

        while len(self.sample_buffer) >= window_size:
            frame = self.sample_buffer[:window_size]
            self.sample_buffer = self.sample_buffer[window_size:]

            # Calculate RMS volume on clean, filtered sound
            rms = float(np.sqrt(np.mean(frame ** 2)))

            input_tensor = np.expand_dims(frame, axis=0)

            # Run Silero VAD model inference
            outputs = session.run(None, {
                'input': input_tensor,
                'state': self.onnx_state,
                'sr': self.sr_tensor
            })

            speech_prob = float(outputs[0].squeeze())
            self.onnx_state = outputs[1]  # Update RNN hidden state

            # Ignore audio frame if volume falls below safety threshold
            if rms < self.min_rms_threshold:
                speech_prob = 0.0

            # Evaluate state changes
            if speech_prob >= self.speech_threshold:
                self.continuous_silence_ms = 0
                self.speech_frames_count += 1
                
                # Double-check: Requires ~192ms of real vocal data to confirm intent
                if not self.is_speaking and self.speech_frames_count >= self.min_speech_frames:
                    self.is_speaking = True
                    event = "speech_start"
            elif speech_prob < self.silence_threshold:
                self.speech_frames_count = 0
                if self.is_speaking:
                    self.continuous_silence_ms += frame_duration_ms
                    if self.continuous_silence_ms >= self.silence_duration_ms_target:
                        self.is_speaking = False
                        event = "speech_end"

        if self.is_speaking:
            self.collected_pcm_bytes.extend(bytes_data)

        completed_audio = None
        if event == "speech_end":
            completed_audio = bytes(self.collected_pcm_bytes)
            self.collected_pcm_bytes = bytearray()
            self.reset()

        return event, completed_audio
