import time
import asyncio
from voice_agent.utils.constants import DEFAULT_LANGUAGE
from voice_agent.audio.vad import SileroVADState

class Session:
    def __init__(self):
        self.is_client_connected = True
        self.vad_state = SileroVADState()
        self.pending_action_tag = None
        self.chunk_index = 0
        self.display_str = ""
        self.full_bot_reply = ""
        
        # Audio buffers
        self.live_pcm_buffer = bytearray()
        self.assistant_audio_buffer = bytearray()
        
        # Flags & conversation states
        self.is_interrupted = False
        self.latest_typed_user_text = ""
        self.latest_client_history = []
        self.latest_client_is_voice_mode = True
        self.current_user_pcm_chunks = []
        self.current_voice_turn_id = 0
        self.last_sent_voice_transcript_turn_id = -1
        self.current_language = DEFAULT_LANGUAGE
        self.current_user_transcription = ""
        self.initial_greeting_sent = False
        self.last_review_summary_slots = {}
        self.last_review_summary_text = ""
        
        # Long-term Session Memory
        self.user_name = ""
        self.name_confirmed = False
        self.user_concern = ""
        self.consultation_agreed = False
        self.asking_for_field = None
        self.slot_just_updated = False
        self.booking_slots = {
            "first_name": "",
            "last_name": "",
            "email": "--",
            "phone": "",
            "city": "",
            "message": "",
            "doctor_name": "",
            "is_booking_active": False,
            "is_submitted": False
        }
        
        # Timing trackers
        self.last_activity_time = time.time()
        
        # Async tasks
        self.user_transcription_task = None
        self.text_mode_task = None
        self.inactivity_task = None
        
        # Gemini WebSocket connection and background listener task
        self.gemini_ws = None
        self.gemini_recv_task = None
        self._setup_complete_event = None

    @property
    def setup_complete_event(self):
        if not hasattr(self, '_setup_complete_event') or self._setup_complete_event is None:
            self._setup_complete_event = asyncio.Event()
        return self._setup_complete_event

    @setup_complete_event.setter
    def setup_complete_event(self, val):
        self._setup_complete_event = val

    def reset_activity_timer(self):
        self.last_activity_time = time.time()
