import os
import numpy as np
import onnxruntime as ort

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
    """
    Maintains per-user VAD hidden state, audio sample buffer,
    speech detection thresholds, RMS noise floor filtering,
    and silence duration tracking.
    """
    def __init__(self, sample_rate=16000, speech_threshold=0.70, silence_threshold=0.45, 
                 silence_duration_ms_target=700, min_rms_threshold=0.015, min_speech_frames=3):
        self.sample_rate = sample_rate
        self.speech_threshold = speech_threshold        # 0.70 threshold filters out background voice noise
        self.silence_threshold = silence_threshold      # 0.45 threshold for silence
        self.silence_duration_ms_target = silence_duration_ms_target  # 700ms continuous silence target
        self.min_rms_threshold = min_rms_threshold      # Filters out low-volume / distant background speech
        self.min_speech_frames = min_speech_frames      # Requires 3 consecutive frames (~96ms) of speech
        
        self.reset()


    def reset(self):
        """
        Resets per-user RNN hidden state, sample buffer, and speaking flags.
        """
        # ONNX model RNN hidden state tensor shape: [2, 1, 128], float32
        self.onnx_state = np.zeros((2, 1, 128), dtype=np.float32)
        self.sr_tensor = np.array(self.sample_rate, dtype=np.int64)
        self.sample_buffer = np.array([], dtype=np.float32)
        
        self.is_speaking = False
        self.continuous_silence_ms = 0
        self.speech_frames_count = 0
        self.collected_pcm_bytes = bytearray()

    def process_chunk(self, bytes_data: bytes):
        """
        Processes an incoming PCM16 16kHz audio chunk.
        Returns:
            tuple: (event, completed_audio_bytes)
            event: "speech_start", "speech_end", or None
        """
        if not bytes_data:
            return None, None

        # Convert raw 16-bit PCM bytes to float32 samples normalized to [-1.0, 1.0]
        pcm_int16 = np.frombuffer(bytes_data, dtype=np.int16)
        pcm_float32 = pcm_int16.astype(np.float32) / 32768.0

        # Append to leftover sample buffer
        self.sample_buffer = np.concatenate((self.sample_buffer, pcm_float32))

        session = get_vad_session()
        window_size = 512  # 32ms window at 16kHz
        frame_duration_ms = (window_size / self.sample_rate) * 1000.0  # 32.0 ms

        event = None

        while len(self.sample_buffer) >= window_size:
            frame = self.sample_buffer[:window_size]
            self.sample_buffer = self.sample_buffer[window_size:]

            # Calculate Root Mean Square (RMS) volume to filter low-volume background voices
            rms = float(np.sqrt(np.mean(frame ** 2)))

            input_tensor = np.expand_dims(frame, axis=0)

            # Run Silero VAD ONNX model inference
            outputs = session.run(None, {
                'input': input_tensor,
                'state': self.onnx_state,
                'sr': self.sr_tensor
            })

            speech_prob = float(outputs[0].squeeze())
            self.onnx_state = outputs[1]  # Update RNN hidden state for next frame

            # Ignore audio if volume is below minimum energy threshold (background voice filter)
            if rms < self.min_rms_threshold:
                speech_prob = 0.0

            if speech_prob >= self.speech_threshold:
                self.continuous_silence_ms = 0
                self.speech_frames_count += 1
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
