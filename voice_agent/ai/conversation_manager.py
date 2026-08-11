import json
import base64
import asyncio
from voice_agent.utils.constants import INACTIVITY_TIMEOUT
from voice_agent.utils.helpers import clean_assistant_text, clean_hallucinations
from voice_agent.navigation.commands import detect_best_tag
from voice_agent.audio.transcriber import transcribe_voice_data

class ConversationManager:
    def __init__(self, session, send_json_callback, gemini_client):
        self.session = session
        self.send_json = send_json_callback
        self.gemini_client = gemini_client

    async def handle_audio_chunk(self, bytes_data):
        self.session.reset_activity_timer()
        # Stream incoming raw audio data to Gemini Live socket
        if self.session.gemini_ws:
            try:
                b64_data = base64.b64encode(bytes_data).decode('utf-8')
                audio_frame = {
                    "realtimeInput": {
                        "audio": {
                            "mimeType": "audio/pcm;rate=16000",
                            "data": b64_data
                        }
                    }
                }
                await self.session.gemini_ws.send(json.dumps(audio_frame))
            except Exception as e:
                print(f"Failed to send binary to Gemini: {e}")
        self.session.current_user_pcm_chunks.append(bytes_data)

    async def handle_client_json(self, data, system_prompt):
        self.session.reset_activity_timer()
        msg_type = data.get("type")
        
        if msg_type == 'text_input':
            self.session.latest_typed_user_text = data.get("text", "")
            self.session.latest_client_history = data.get("history", [])
            self.session.latest_client_is_voice_mode = data.get("isVoiceMode") != False
            
            if self.session.text_mode_task:
                self.session.text_mode_task.cancel()
                self.session.text_mode_task = None
                
            if not self.session.latest_client_is_voice_mode:
                # Interrupted voice stream, switch to text stream API
                self.session.is_interrupted = True
                self.session.chunk_index = 0
                self.session.display_str = ""
                self.session.full_bot_reply = ""
                self.session.live_pcm_buffer = bytearray()
                self.session.assistant_audio_buffer = bytearray()
                
                if self.session.gemini_ws:
                    try:
                        await self.session.gemini_ws.send(json.dumps({"clientContent": {"turnComplete": False}}))
                    except Exception:
                        pass
                    
                # Start Text Mode completion
                self.session.text_mode_task = asyncio.create_task(
                    self.gemini_client.stream_gemini_chat_reply(
                        self.session.latest_typed_user_text,
                        self.session.latest_client_history,
                        system_prompt
                    )
                )
            else:
                self.session.is_interrupted = False
                if self.session.gemini_ws and not self.session.initial_greeting_sent:
                    # Let connect_and_loop_gemini_live handle sending the initial greeting text
                    pass
                elif self.session.gemini_ws:
                    try:
                        fallback_text = self.session.latest_typed_user_text or "Hello"
                        await self.session.gemini_ws.send(json.dumps({
                            "clientContent": {
                                "turns": [{"role": "user", "parts": [{"text": fallback_text}]}],
                                "turnComplete": True
                            }
                        }))
                    except Exception:
                        pass
        
        elif msg_type == 'process_final':
            self.session.latest_client_history = data.get("history", [])
            self.session.latest_client_is_voice_mode = data.get("isVoiceMode") != False
            
            turn_id_for_this_speech = self.session.current_voice_turn_id
            pcm_buffer = b"".join(self.session.current_user_pcm_chunks) if self.session.current_user_pcm_chunks else b""
            self.session.current_user_pcm_chunks = []
            self.session.is_interrupted = False
                
            # Background transcription for the browser UI chat bubble
            native_text = clean_hallucinations(data.get("nativeTranscript", "").strip())
            if not native_text:
                native_text = clean_hallucinations(self.session.current_user_transcription.strip())
                
            if native_text:
                self.session.current_user_transcription = native_text
                fut = asyncio.Future()
                fut.set_result(native_text)
                self.session.user_transcription_task = fut
                await self.maybe_send_voice_transcript(turn_id_for_this_speech, native_text)
            else:
                self.session.user_transcription_task = asyncio.create_task(
                    self.transcribe_user_audio_async(pcm_buffer, turn_id_for_this_speech)
                )
        
        elif msg_type == 'start_of_speech':
            self.session.current_voice_turn_id += 1
            self.session.current_user_pcm_chunks = []
            self.session.last_sent_voice_transcript_turn_id = -1
            self.session.is_interrupted = False
            self.session.chunk_index = 0
            self.session.display_str = ""
            self.session.full_bot_reply = ""
            self.session.live_pcm_buffer = bytearray()
            self.session.assistant_audio_buffer = bytearray()
            self.session.current_user_transcription = ""
            self.session.user_transcription_task = None

    async def transcribe_user_audio_async(self, pcm_bytes, turn_id):
        try:
            lang = self.session.current_language or 'hi-IN'
            raw_text = await transcribe_voice_data(pcm_bytes, 16000, lang)
            text = clean_hallucinations(raw_text).strip()
            self.session.current_user_transcription = text
            await self.maybe_send_voice_transcript(turn_id, text)
            return text
        except Exception as e:
            print(f"User transcription error: {e}")
            return ""

    async def maybe_send_voice_transcript(self, turn_id, text):
        if not text:
            return
        if turn_id == self.session.last_sent_voice_transcript_turn_id:
            return
        self.session.last_sent_voice_transcript_turn_id = turn_id
        await self.send_json({"type": "user_spoken_text", "text": text})

    async def transcribe_and_sync_bot_text(self, audio_bytes):
        try:
            user_text = ""
            if self.session.user_transcription_task:
                try:
                    user_text = await self.session.user_transcription_task
                except Exception:
                    pass
            if not user_text:
                user_text = self.session.current_user_transcription or "Voice Message"
                
            lang = self.session.current_language or 'en-IN'
            bot_text = await transcribe_voice_data(audio_bytes, 24000, language_code=lang)
            if not bot_text:
                bot_text = "(Voice message played)"
            clean_text = clean_assistant_text(bot_text)
            best_tag = detect_best_tag(user_text, clean_text)
            
            await self.send_json({
                "type": "bot_spoken_text",
                "text": clean_text,
                "tag": best_tag
            })
        except Exception as e:
            await self.send_json({"type": "bot_spoken_text", "text": "(Voice message played)"})

    async def inactivity_monitor_loop(self, close_ws_callback):
        while self.session.is_client_connected:
            try:
                now = asyncio.get_event_loop().time()
                elapsed = now - self.session.last_activity_time
                if elapsed >= INACTIVITY_TIMEOUT:
                    print("⏳ Inactivity timeout reached. Disconnecting client...")
                    await self.send_json({"type": "error", "error": "Session timed out due to inactivity."})
                    await close_ws_callback()
                    break
                
                # Sleep for the remaining time or a minimum of 1 second
                sleep_time = max(1.0, INACTIVITY_TIMEOUT - elapsed)
                await asyncio.sleep(sleep_time)
            except Exception as e:
                print(f"Error in inactivity monitor: {e}")
                break
