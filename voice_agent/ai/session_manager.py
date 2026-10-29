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
        self.is_ios = False
        self.ios_debug = False
        self.ios_debug_path = None
        self.latest_typed_user_text = ""
        self.latest_client_history = []
        self.latest_client_is_voice_mode = True
        self.current_user_pcm_chunks = []
        self.current_voice_turn_id = 0
        self.last_sent_voice_transcript_turn_id = -1
        self.current_language = DEFAULT_LANGUAGE
        self.is_language_established = False
        self.has_user_spoken = False
        self.current_user_transcription = ""
        self.initial_greeting_sent = False
        self.last_review_summary_slots = {}
        self.last_review_summary_text = ""
        self.consumed_summary_texts = set()  # summaries already used for a submission, never reused
        self.last_consumed_summary_slots = {}  # reusable only on an explicit "re-submit"
        
        # Long-term Session Memory
        self.call_id = None
        self.conversation_type = "voice_agent"
        self.transcript_history = []
        self.user_name = ""
        self.name_confirmed = False
        self.user_concern = ""
        self.consultation_agreed = False
        self.consultation_offered = False
        self.consultation_declined = False
        self.profession_asked = False
        self.asking_for_field = None
        self.slot_just_updated = False
        self.recommended_dentists = []
        self.dentist_page_offset = 0
        self.pincode_asked_for_dentist = False
        self.last_recommended_pincode = ""
        self.doctor_guidance_asked = False
        self.city_pincode_mismatch = False
        self.city_pincode_mismatch_data = None
        self.city_updated_need_pincode = False
        self.city_pincode_locked = False
        self.travel_destination_city = None
        self.is_travel_booking_turn = False
        self.user_state = None
        self.state_clarification_needed = None
        self.submitted_lead_id = None
        self.slots_edited_after_submit = False
        self.booking_slots = {
            "first_name": "",
            "last_name": "",
            "email": "--",
            "phone": "",
            "city": "",
            "pincode": "",
            "message": "",
            "doctor_name": "",
            "is_booking_active": False,
            "is_submitted": False,
            "submission_id": None
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

    def add_transcript_turn(self, role, text):
        if not text or not isinstance(text, str) or not text.strip():
            return
        clean_t = text.strip()
        if clean_t.startswith("SYSTEM INSTRUCTION") or clean_t == "...":
            return
        if self.transcript_history and self.transcript_history[-1] == (role, clean_t):
            return
        self.transcript_history.append((role, clean_t))

    def clear_voice_intercept_flags(self):
        """One-shot flags that only the text pipeline consumes. In voice mode Gemini Live already answered the
        turn from audio, so leftovers would fire much later (e.g. on the silence nudge) as unrelated canned replies."""
        self.pincode_invalid = False
        self.phone_invalid = False
        self.city_updated_need_pincode = False
        self.state_clarification_needed = None
        self.pincode_just_updated = False
        self.is_other_dentists_requested = False

    def get_history_turns(self, max_turns=20):
        """Server-side transcript in client-history format. Voice turns never carry client history, so slot parsing falls back to this."""
        return [
            {"role": role, "parts": [{"text": text}]}
            for role, text in self.transcript_history[-max_turns:]
        ]

    def get_full_transcript(self):
        res = ""
        # 1. First priority: transcript_history turns
        if self.transcript_history:
            lines = []
            for role, text in self.transcript_history:
                speaker = "User" if role.lower() == "user" else "Assistant (Riya)"
                lines.append(f"{speaker}: {text}\n")
            res = "\n".join(lines).strip()

        # 2. Fallback: latest_client_history turns
        if not res and self.latest_client_history and isinstance(self.latest_client_history, list):
            lines = []
            for turn in self.latest_client_history:
                if isinstance(turn, dict):
                    role = turn.get("role", "model")
                    speaker = "User" if role.lower() == "user" else "Assistant (Riya)"
                    parts = turn.get("parts", [])
                    txt = parts[0].get("text", "") if parts and isinstance(parts[0], dict) else ""
                    if txt and not txt.startswith("SYSTEM INSTRUCTION"):
                        lines.append(f"{speaker}: {txt}\n")
            res = "\n".join(lines).strip()

        # 3. Include any in-flight uncommitted user or bot speech at disconnect time
        extra_lines = []
        in_flight_user = getattr(self, 'current_user_transcription', None)
        if in_flight_user and in_flight_user.strip():
            u_clean = in_flight_user.strip()
            if not self.transcript_history or self.transcript_history[-1] != ("user", u_clean):
                if f"User: {u_clean}" not in res:
                    extra_lines.append(f"User: {u_clean}\n")
        in_flight_bot = getattr(self, 'full_bot_reply', None)
        if in_flight_bot and in_flight_bot.strip():
            b_clean = in_flight_bot.strip()
            if not self.transcript_history or self.transcript_history[-1] != ("model", b_clean):
                if f"Assistant (Riya): {b_clean}" not in res:
                    extra_lines.append(f"Assistant (Riya): {b_clean}\n")

        if extra_lines:
            base = (res + "\n\n") if res else ""
            res = (base + "\n".join(extra_lines)).strip()

        return res

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
