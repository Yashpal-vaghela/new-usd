# Constants for voice agent application

INACTIVITY_TIMEOUT = 30  # seconds of inactivity before disconnecting
SILENCE_TIMEOUT = 12     # seconds of user silence before sending nudge

GEMINI_LIVE_MODEL = "models/gemini-3.1-flash-live-preview"
GEMINI_TEXT_MODEL = "gemini-2.5-flash"

DEFAULT_LANGUAGE = "en-IN"

SAMPLE_RATE_LIVE = 24000  # sample rate for assistant audio output
SAMPLE_RATE_USER = 16000  # sample rate for user audio input
