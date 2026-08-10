import os
import re
import json
import base64
import asyncio
import httpx
import websockets
from voice_agent.utils.constants import GEMINI_LIVE_MODEL, GEMINI_TEXT_MODEL
from voice_agent.utils.helpers import clean_assistant_text, clean_hallucinations
from voice_agent.navigation.commands import detect_best_tag, detect_best_tag_with_fallback
from voice_agent.audio.transcoder import wrap_pcm_to_wav_base64
from voice_agent.audio.transcriber import transcribe_voice_data

def sanitize_gemini_history(history):
    if not isinstance(history, list):
        return []
    sliced = history[-6:]
    sanitized = []
    current_role = None
    current_parts = []
    
    for turn in sliced:
        r = 'model' if turn.get('role') == 'model' else 'user'
        t = turn.get('parts', [{}])[0].get('text', "")
        if not t:
            continue
        if r == current_role:
            current_parts.append(t)
        else:
            if current_role is not None:
                sanitized.append({"role": current_role, "parts": [{"text": " \n ".join(current_parts)}]})
            current_role = r
            current_parts = [t]
            
    if current_role is not None:
        sanitized.append({"role": current_role, "parts": [{"text": " \n ".join(current_parts)}]})
        
    if sanitized and sanitized[0]["role"] == 'model':
        sanitized.pop(0)
        
    return sanitized

class GeminiClient:
    def __init__(self, session, send_json_callback, transcribe_bot_audio_callback):
        self.session = session
        self.send_json = send_json_callback
        self.transcribe_bot_audio = transcribe_bot_audio_callback
        
        api_key = os.getenv("GEMINI_API_KEY_voice")
        self.gemini_ws_url = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={api_key}"

    async def connect_and_loop(self, system_prompt):
        while self.session.is_client_connected:
            try:
                print("⚡ Connecting to Native Gemini Live API...")
                async with websockets.connect(self.gemini_ws_url) as ws:
                    self.session.gemini_ws = ws
                    print("✅ Connected to Native Gemini Live API (v1beta)")
                    
                    setup_message = {
                        "setup": {
                            "model": GEMINI_LIVE_MODEL,
                            "generationConfig": {
                                "responseModalities": ["AUDIO"],
                                "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Aoede"}}}
                            },
                            "systemInstruction": {"parts": [{"text": system_prompt}]}
                        }
                    }
                    await ws.send(json.dumps(setup_message))
                    
                    # Trigger initial greeting natively
                    await asyncio.sleep(0.25)
                    if self.session.latest_client_history:
                        history_to_inject = sanitize_gemini_history(self.session.latest_client_history)
                        await ws.send(json.dumps({
                            "clientContent": {
                                "turns": history_to_inject,
                                "turnComplete": False
                            }
                        }))
                        self.session.initial_greeting_sent = True
                    else:
                        # Wait for client's initial message containing custom greeting system instruction
                        for _ in range(20):
                            if self.session.latest_typed_user_text:
                                break
                            await asyncio.sleep(0.1)
                        
                        initial_text = self.session.latest_typed_user_text or "Hello! Please briefly introduce yourself to the patient."
                        await ws.send(json.dumps({
                            "clientContent": {
                                "turns": [{"role": "user", "parts": [{"text": initial_text}]}],
                                "turnComplete": True
                            }
                        }))
                        self.session.initial_greeting_sent = True
                    
                    # Recv loop
                    while self.session.is_client_connected:
                        raw_data = await ws.recv()
                        await self.handle_gemini_message(raw_data)
            except Exception as e:
                print(f"⚠️ Gemini Live WS Error or Disconnect: {e}")
                if self.session.is_client_connected:
                    await self.send_json({"type": "idle"})
                    await asyncio.sleep(1.0)
                else:
                    break

    async def handle_gemini_message(self, raw_data):
        try:
            response = json.loads(raw_data)
            if "serverContent" in response:
                server_content = response["serverContent"]
                
                if self.session.is_interrupted:
                    if server_content.get("turnComplete"):
                        self.session.is_interrupted = False
                    return
                
                if "modelTurn" in server_content:
                    parts = server_content["modelTurn"].get("parts", [])
                    for part in parts:
                        if "inlineData" in part:
                            incoming_pcm = base64.b64decode(part["inlineData"]["data"])
                            self.session.live_pcm_buffer.extend(incoming_pcm)
                            self.session.assistant_audio_buffer.extend(incoming_pcm)
                            
                        if "text" in part:
                            text_chunk = part["text"]
                            self.session.display_str += text_chunk
                            self.session.full_bot_reply += text_chunk
                            
                            # Update conversation language based on the bot's tag
                            lang_match = re.search(r"\[(hi|bn|ta|te|mr|gu|kn|ml|pa|or|en)-IN\]", self.session.full_bot_reply, re.IGNORECASE)
                            if lang_match:
                                self.session.current_language = f"{lang_match.group(1).lower()}-IN"
                            
                            best_tag = detect_best_tag(self.session.latest_typed_user_text, self.session.display_str)
                            await self.send_json({
                                "type": "text_stream",
                                "text": clean_assistant_text(self.session.display_str),
                                "tag": best_tag
                            })
                            
                        # If a natural punctuation boundary is reached or buffer is large enough
                        if (re.search(r"[.,?!।\n]", part.get("text", "")) or len(self.session.live_pcm_buffer) >= 12000) and len(self.session.live_pcm_buffer) > 0:
                            wav_base64 = wrap_pcm_to_wav_base64(self.session.live_pcm_buffer, 24000)
                            await self.send_json({
                                "type": "audio_chunk",
                                "audioBase64": wav_base64,
                                "index": self.session.chunk_index
                            })
                            self.session.chunk_index += 1
                            self.session.live_pcm_buffer = bytearray()
                
                if server_content.get("turnComplete"):
                    if len(self.session.live_pcm_buffer) > 0:
                        wav_base64 = wrap_pcm_to_wav_base64(self.session.live_pcm_buffer, 24000)
                        await self.send_json({
                            "type": "audio_chunk",
                            "audioBase64": wav_base64,
                            "index": self.session.chunk_index
                        })
                        self.session.chunk_index += 1
                        self.session.live_pcm_buffer = bytearray()
                    
                    current_assistant_audio = bytes(self.session.assistant_audio_buffer)
                    self.session.assistant_audio_buffer = bytearray()
                    
                    # Resolve user transcription asynchronously if it's running
                    user_text = ""
                    if self.session.user_transcription_task:
                        try:
                            user_text = await asyncio.wait_for(asyncio.shield(self.session.user_transcription_task), timeout=1.0)
                        except Exception:
                            pass
                    if not user_text:
                        user_text = self.session.current_user_transcription or "Voice Message"
                    
                    if len(current_assistant_audio) > 0:
                        # Use the native Gemini Live transcription if available
                        bot_text_to_send = self.session.full_bot_reply or "..."
                        clean_text = clean_assistant_text(bot_text_to_send) if self.session.full_bot_reply else "..."
                        
                        final_tag, new_pending = detect_best_tag_with_fallback(
                            user_text, clean_text, self.session.pending_action_tag
                        )
                        self.session.pending_action_tag = new_pending
                        
                        await self.send_json({
                            "type": "reply_complete",
                            "userText": user_text,
                            "botText": clean_text,
                            "tag": final_tag,
                            "totalChunks": self.session.chunk_index
                        })
                        
                        # Reset indices
                        self.session.chunk_index = 0
                        
                        # Background Bot STT transcription only if we did not get native transcription
                        if not self.session.full_bot_reply:
                            asyncio.create_task(self.transcribe_bot_audio(current_assistant_audio))
                            
                        self.session.display_str = ""
                        self.session.full_bot_reply = ""
                    else:
                        await self.send_json({"type": "idle"})
                        self.session.chunk_index = 0
                        self.session.display_str = ""
                        self.session.full_bot_reply = ""
                    
                    self.session.reset_activity_timer()
                    self.session.latest_client_history = []
        except Exception as e:
            print(f"❌ Error parsing Gemini WS frame: {e}")

    async def stream_gemini_chat_reply(self, user_text, history, system_prompt):
        try:
            api_key = os.getenv("GEMINI_API_KEY_voice")
            contents = sanitize_gemini_history(history)
            safe_text = user_text or ""
            
            if contents and contents[-1]["role"] == "user":
                if safe_text:
                    contents[-1]["parts"][0]["text"] += " \n " + safe_text
            else:
                if safe_text:
                    contents.append({"role": "user", "parts": [{"text": safe_text}]})
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_TEXT_MODEL}:streamGenerateContent?alt=sse&key={api_key}"
            payload = {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": contents,
                "generationConfig": {"temperature": 0.2}
            }
            
            display_str = ""
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", url, json=payload, timeout=30.0) as response:
                    if response.status_code != 200:
                        raise Exception(f"Gemini REST failure: {response.status_code}")
                        
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line.startswith("data: "):
                            continue
                        payload_data = line[6:]
                        if not payload_data:
                            continue
                        
                        try:
                            json_data = json.loads(payload_data)
                            delta = json_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            if delta:
                                display_str += delta
                                clean_text = clean_assistant_text(display_str)
                                await self.send_json({
                                    "type": "text_stream",
                                    "text": clean_text
                                })
                        except Exception:
                            pass
            
            final_text = clean_assistant_text(display_str.strip() or "Okay.")
            
            final_tag, new_pending = detect_best_tag_with_fallback(
                user_text, final_text, self.session.pending_action_tag
            )
            self.session.pending_action_tag = new_pending
                    
            await self.send_json({
                "type": "reply_complete",
                "userText": user_text or "Text Input",
                "botText": final_text,
                "tag": final_tag,
                "totalChunks": 0
            })
            self.session.reset_activity_timer()
        except Exception as e:
            print(f"Error in Gemini text fallback: {e}")
            await self.send_json({"type": "error", "error": str(e)})
