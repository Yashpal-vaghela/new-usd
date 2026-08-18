import numpy as np
from voice_agent.audio.vad import SileroVADState, get_vad_session

class MockVADSession:
    def __init__(self, prob_sequence):
        self.prob_sequence = prob_sequence
        self.idx = 0

    def run(self, output_names, input_feed):
        prob = self.prob_sequence[self.idx % len(self.prob_sequence)]
        self.idx += 1
        return [np.array([[prob]], dtype=np.float32), np.zeros((2, 1, 128), dtype=np.float32)]

def test_silero_vad():
    print("Testing Silero VAD ONNX Session single-instance loading...")
    s1 = get_vad_session()
    s2 = get_vad_session()
    assert s1 is s2, "VAD session should be loaded only once (singleton)!"
    print("[OK] Model loaded only once successfully.")

    # Create two separate user VAD states
    user1_vad = SileroVADState(speech_threshold=0.5, silence_threshold=0.35, silence_duration_ms_target=700)
    user2_vad = SileroVADState(speech_threshold=0.5, silence_threshold=0.35, silence_duration_ms_target=700)
    assert user1_vad is not user2_vad, "VAD state should be separate per user!"
    print("[OK] Separate per-user VAD states verified.")

    # Create mock session with speech -> short pause -> speech -> continuous 700ms silence
    # 512 samples at 16kHz = 32ms per frame
    # 10 speech frames (320ms) -> 12 silence frames (384ms, <700ms) -> 5 speech frames (160ms) -> 23 silence frames (736ms, >700ms)
    probs = ([0.9] * 10) + ([0.1] * 12) + ([0.95] * 5) + ([0.05] * 25)
    mock_session = MockVADSession(probs)

    # Temporarily inject mock session for test
    import voice_agent.audio.vad as vad_module
    old_session = vad_module._session
    vad_module._session = mock_session

    try:
        frame_pcm = (np.sin(np.linspace(0, 32, 512)) * 10000).astype(np.int16).tobytes()

        # 1. Speech Start
        events = []
        for _ in range(10):
            ev, _ = user1_vad.process_chunk(frame_pcm)
            if ev:
                events.append(ev)


        assert "speech_start" in events, "speech_start event must be detected!"
        assert user1_vad.is_speaking, "User 1 should be marked as speaking!"
        print("[OK] Speech start detected correctly!")

        # 2. Short Pause (384ms silence < 700ms)
        end_events = []
        silence_frame = b"\x00\x00" * 512
        for _ in range(12):
            ev, _ = user1_vad.process_chunk(silence_frame)
            if ev:
                end_events.append(ev)

        assert "speech_end" not in end_events, "Short pause (< 700ms) must NOT trigger speech_end!"
        assert user1_vad.is_speaking, "User 1 must remain speaking during short pause!"
        print("[OK] Short pause (< 700ms) ignored correctly!")

        # 3. Resume Speech
        for _ in range(5):
            user1_vad.process_chunk(frame_pcm)

        # 4. Continuous 700ms silence
        end_events = []
        completed_audio = None
        for _ in range(25):
            ev, audio = user1_vad.process_chunk(silence_frame)
            if ev:
                end_events.append(ev)
            if audio:
                completed_audio = audio


        assert "speech_end" in end_events, "Continuous 700ms silence MUST trigger speech_end!"
        assert not user1_vad.is_speaking, "User 1 should no longer be speaking after speech_end!"
        assert completed_audio is not None and len(completed_audio) > 0, "Completed audio must be returned on speech_end!"
        print(f"[OK] Speech end detected after continuous 700ms silence! Audio size: {len(completed_audio)} bytes.")

        # 5. Verify User 2 isolation
        assert not user2_vad.is_speaking, "User 2 state must remain unaffected by User 1!"
        print("[OK] Per-user VAD state isolation verified!")

    finally:
        vad_module._session = old_session

    print("\nALL SILERO VAD ONNX TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_silero_vad()
