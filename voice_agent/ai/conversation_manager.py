import os
import json
import base64
import asyncio
import httpx
from voice_agent.utils.constants import INACTIVITY_TIMEOUT
from voice_agent.utils.helpers import clean_assistant_text, clean_hallucinations
from voice_agent.navigation.commands import detect_best_tag, detect_best_tag_with_fallback
from voice_agent.audio.transcriber import transcribe_voice_data

class ConversationManager:
    def __init__(self, session, send_json_callback, gemini_client):
        self.session = session
        self.send_json = send_json_callback
        self.gemini_client = gemini_client

    async def handle_audio_chunk(self, bytes_data):
        self.session.reset_activity_timer()
        self.session.current_user_pcm_chunks.append(bytes_data)

        # ⚡ OFFICIAL GEMINI LIVE DIRECT STREAMING (Automatic Server-Side Neural VAD) ⚡
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
                print(f"Failed to send audio chunk to Gemini: {e}")

    async def stream_chat_text_response(self, user_text, history, system_prompt):
        """⚡ Blazing fast sub-second Gemini 3.5 Flash Lite streaming specifically for Chat Mode ⚡"""
        api_key = os.getenv("GEMINI_API_KEY_NEW") or os.getenv("GEMINI_API_KEY")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:streamGenerateContent?alt=sse&key={api_key}"
        
        contents = []
        if history:
            for turn in history[-6:]:
                role = "model" if turn.get("role") in ["model", "assistant"] else "user"
                parts = turn.get("parts", [])
                if parts and isinstance(parts, list) and "text" in parts[0] and parts[0]["text"]:
                    contents.append({"role": role, "parts": [{"text": parts[0]["text"]}]})
        contents.append({"role": "user", "parts": [{"text": user_text}]})
        
        payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system_prompt}]}
        }
        
        full_text = ""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                async with client.stream("POST", url, json=payload) as resp:
                    if resp.status_code == 200:
                        async for line in resp.aiter_lines():
                            if line.startswith("data: "):
                                try:
                                    chunk_data = json.loads(line[6:])
                                    candidates = chunk_data.get("candidates", [])
                                    if candidates and "content" in candidates[0]:
                                        parts = candidates[0]["content"].get("parts", [])
                                        for p in parts:
                                            chunk_txt = p.get("text", "")
                                            if chunk_txt:
                                                full_text += chunk_txt
                                                best_tag = detect_best_tag(user_text, full_text)
                                                await self.send_json({
                                                    "type": "bot_text_chunk",
                                                    "text": chunk_txt,
                                                    "tag": best_tag,
                                                    "turnId": self.session.current_voice_turn_id
                                                })
                                except Exception:
                                    pass
                    else:
                        print(f"Chat stream API status: {resp.status_code}")
        except Exception as e:
            print(f"Chat stream error: {e}")
            
        clean_text = clean_assistant_text(full_text)
        final_tag, new_pending = detect_best_tag_with_fallback(
            user_text, clean_text or "...", self.session.pending_action_tag
        )
        self.session.pending_action_tag = new_pending
        
        await self.send_json({
            "type": "bot_spoken_text",
            "text": clean_text or full_text,
            "tag": final_tag,
            "turnId": self.session.current_voice_turn_id
        })
        await self.send_json({
            "type": "reply_complete",
            "userText": user_text,
            "botText": clean_text or full_text,
            "tag": final_tag,
            "totalChunks": 1
        })

    async def handle_client_json(self, data, system_prompt):
        self.session.reset_activity_timer()
        msg_type = data.get("type")

        if msg_type == 'heartbeat':
            return
        
        if msg_type == 'start_of_speech':
            self.session.vad_state.is_speaking = True
            await self.send_json({"type": "user_speaking_status", "is_speaking": True})
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
            return

        if msg_type == 'text_input':
            self.session.latest_typed_user_text = data.get("text", "")
            self.session.latest_client_history = data.get("history", [])
            self.session.latest_client_is_voice_mode = data.get("isVoiceMode") != False
            
            user_text = self.session.latest_typed_user_text or "Hello"
            self.session.is_interrupted = False
            self.session.chunk_index = 0
            self.session.display_str = ""
            self.session.full_bot_reply = ""
            self.session.live_pcm_buffer = bytearray()
            self.session.assistant_audio_buffer = bytearray()
            
            # In Chat Mode: Stream instantly via Gemini 3.5 Flash Lite for sub-second UI response
            if not self.session.latest_client_is_voice_mode:
                asyncio.create_task(self.stream_chat_text_response(user_text, self.session.latest_client_history, system_prompt))
                return

            # In Voice Mode: Send turn to persistent Gemini Live WebSocket
            if self.session.gemini_ws:
                try:
                    await self.session.gemini_ws.send(json.dumps({
                        "clientContent": {
                            "turns": [{"role": "user", "parts": [{"text": user_text}]}],
                            "turnComplete": True
                        }
                    }))
                    self.session.initial_greeting_sent = True
                except Exception as e:
                    print(f"Failed to send text turn to Gemini Live: {e}")
        
        elif msg_type == 'process_final':
            self.session.vad_state.is_speaking = False
            self.session.latest_client_history = data.get("history", [])
            self.session.latest_client_is_voice_mode = data.get("isVoiceMode") != False
            
            turn_id_for_this_speech = self.session.current_voice_turn_id
            pcm_buffer = b"".join(self.session.current_user_pcm_chunks) if self.session.current_user_pcm_chunks else b""
            self.session.current_user_pcm_chunks = []
            self.session.is_interrupted = False
            
            # Extract client transcription if provided by browser STT
            native_text = clean_hallucinations(data.get("nativeTranscript", "").strip())
            if not native_text:
                native_text = clean_hallucinations(self.session.current_user_transcription.strip())
                
            if native_text and self.session.gemini_ws:
                try:
                    await self.session.gemini_ws.send(json.dumps({
                        "clientContent": {
                            "turns": [{"role": "user", "parts": [{"text": native_text}]}],
                            "turnComplete": True
                        }
                    }))
                except Exception as e:
                    print(f"Failed to send speech transcript turn to Gemini Live: {e}")
            elif self.session.gemini_ws:
                # Raw audio streaming finalization
                try:
                    await self.session.gemini_ws.send(json.dumps({
                        "realtimeInput": {
                            "audioStreamEnd": True
                        }
                    }))
                except Exception:
                    pass
                
            # Background transcription for the browser UI chat bubble
            if native_text:
                self.session.current_user_transcription = native_text
                fut = asyncio.Future()
                fut.set_result(native_text)
                self.session.user_transcription_task = fut
                await self.maybe_send_voice_transcript(turn_id_for_this_speech, native_text)
            elif pcm_buffer:
                self.session.user_transcription_task = asyncio.create_task(
                    self.transcribe_user_audio_async(pcm_buffer, turn_id_for_this_speech)
                )
        
        elif msg_type == 'start_of_speech':
            self.session.vad_state.is_speaking = True
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
                is_voice = getattr(self.session, 'latest_client_is_voice_mode', True)
                current_timeout = 40 if is_voice else 120
                if elapsed >= current_timeout:
                    print("⏳ Inactivity timeout reached. Disconnecting client...")
                    await self.send_json({"type": "error", "error": "Session timed out due to inactivity."})
                    await close_ws_callback()
                    break
                
                # Sleep for the remaining time or a minimum of 1 second
                sleep_time = max(1.0, current_timeout - elapsed)
                await asyncio.sleep(sleep_time)
            except Exception as e:
                print(f"Error in inactivity monitor: {e}")
                break
