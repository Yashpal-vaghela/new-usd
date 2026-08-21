import os
import numpy as np
import onnxruntime as ort
from scipy.signal import butter, lfilter  # Added for thud filtering

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "silero_vad.onnx")
_session = None

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
        nyquist = 0.5 * sample_rate
        low_cutoff_hz = 200.0
        normal_cutoff = low_cutoff_hz / nyquist
        self.b_coeff, self.a_coeff = butter(4, normal_cutoff, btype='high', analog=False)
        
        self.reset()

    def reset(self):
        """
        Resets per-user RNN hidden state, sample buffer, and speaking flags.
        """
        self.onnx_state = np.zeros((2, 1, 128), dtype=np.float32)
        self.sr_tensor = np.array(self.sample_rate, dtype=np.int64)
        self.sample_buffer = np.array([], dtype=np.float32)
        
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

        # Apply High-Pass Filter to eliminate low frequency table bumps and mic taps (cast to float32 for ONNX)
        filtered_pcm = lfilter(self.b_coeff, self.a_coeff, pcm_float32).astype(np.float32)

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
