def is_affirmative_submit(text):
    if not text:
        return False
    tl = text.lower().strip()
    tl = re.sub(r"[\s.,!?\\/]+$", "", tl)
    if tl in [
        "submit", "yes", "yea", "yep", "yeah", "ok", "okay", "sure", "done", "please do", "confirm", "proceed",
        "હા", "હા કરી દો", "હા કરી દ્યો", "ચોક્કસ", "ભલે", "ઠીક છે", "હાજી", "કરી દ્યો", "કરી દો", "સબમિટ", "હા સબમિટ", "સબમિટ કરો", "સબમિટ કરી દો", "સબમિટ કરી દ્યો",
        "हाँ", "हाँ कर दो", "कर दो", "अवश्य", "ज़रूर", "सबमिट", "हाँ सबमिट", "सबमिट करो", "सबमिट कर दीजिए", "सबमिट कर दो", "हाँजी",
        "हो", "हो करा", "करा", "नक्की", "चालेल", "सबमिट", "सबमिट करा", "हो सबमिट करा",
        "হ্যাঁ", "হ্যাঁ করুন", "করুন", "অবশ্যই", "সাবমিট", "সাবমিট করুন", "হ্যাঁ সাবমিট করুন",
        "ஆம்", "சரி", "கண்டிப்பாக", "சமர்ப்பிக்கவும்", "சப்மிட்", "சப்மிட் பண்ணுங்க", "ஆம் சப்மிட் பண்ணுங்க",
        "అవును", "సరే", "తప్పకుండా", "సమర్పించండి", "సబ్మిట్", "సబ్మిట్ చేయండి", "అవును సబ్మిట్ చేయండి",
        "ಹೌದು", "ಸರಿ", "ಖಂಡಿತ", "ಸಲ್ಲಿಸಿ", "ಸಬ್ಮಿಟ್", "ಸಬ್ಮಿಟ್ ಮಾಡಿ", "ಹೌದು ಸಬ್ಮಿಟ್ ಮಾಡಿ",
        "അതെ", "ശരി", "തീർച്ചയായും", "സമർപ്പിക്കുക", "സബ്മിറ്റ്", "സബ്മിറ്റ് ചെയ്യുക", "അതെ സബ്മിറ്റ് ചെയ്യുക",
        "ਹਾਂ", "ਹਾਂਜੀ", "ਜ਼ਰੂਰ", "ਦਰਜ ਕਰੋ", "ਸਬਮਿਟ", "ਸਬਮਿਟ ਕਰੋ", "ਹਾਂ ਸਬਮਿਟ ਕਰੋ",
        "ହଁ", "ହଁ କରନ୍ତୁ", "ନିଶ୍ଚୟ", "ଦାଖଲ କରନ୍ତୁ", "ସବମିଟ୍", "ସବମିଟ୍ କରନ୍ତୁ", "ହଁ ସବମିଟ୍ କରନ୍ତୁ",
        "haan", "ha", "haa", "ha ji", "haan ji", "kar do", "kardo", "kari do", "kari dyo", "kar dyo", "haa kari dyo",
        "yes submit", "chalega", "thik chhe", "theek hai", "bhaley", "chokkas", "zarur", "zaroor", "submit karo", "submit kar do", "submit kari dyo", "submit madi", "submit pannunga", "submit cheyandi", "submit koro", "submit karantu"
    ]:
        return True
    edit_words = ["change", "update", "edit", "instead", "no my", "no, my", "spelling", "mistake"]
    if any(ew in tl for ew in edit_words):
        return False
    for phrase in [
        "submit", "confirm", "book", "kari dyo", "kari do", "kar do", "kardo", "submitt",
        "કરી દ્યો", "કરી દો", "સબમિટ", "કર દો", "कर दो", "सबमिट", "करा", "করুন", "சமர்ப்பிக்கவும்", "సమర్పించండి", "ಸಲ್ಲಿಸಿ", "സമർപ്പിക്കുക", "ਦਰਜ ਕਰੋ", "ଦାଖଲ କରନ୍ତୁ",
        "mari booking", "મારી બુકિંગ", "મારી અપૉઇન્ટમેન્ટ", "मेरी बुकिंग"
    ]:
        if phrase in tl:
            return True
    return False

import os
import re
import json
import base64
import asyncio
import httpx
import websockets
from websockets.exceptions import ConnectionClosed
from voice_agent.utils.constants import GEMINI_LIVE_MODEL, GEMINI_TEXT_MODEL
from voice_agent.utils.helpers import clean_assistant_text, clean_hallucinations, extract_slots_from_review_summary
from voice_agent.navigation.commands import detect_best_tag, detect_best_tag_with_fallback
from voice_agent.audio.transcoder import wrap_pcm_to_wav_base64
from voice_agent.audio.transcriber import transcribe_voice_data
from voice_agent.services.appointment_service import submit_consultation_appointment, CERTIFIED_CITIES

APPOINTMENT_TOOL_DECLARATION = {
    "functionDeclarations": [
        {
            "name": "submit_appointment_booking",
            "description": "Submits a finalized patient dental consultation appointment booking to the Ultimate Smile Design clinic team after details (first_name, last_name, email, phone, city, message, doctor_name) have been verified with the patient.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "first_name": {"type": "STRING", "description": "Patient's confirmed first name"},
                    "last_name": {"type": "STRING", "description": "Patient's last name (or empty if not provided)"},
                    "email": {"type": "STRING", "description": "Patient's email address (optional, leave empty string if not provided)"},
                    "phone": {"type": "STRING", "description": "Patient's confirmed 10-digit phone number"},
                    "city": {"type": "STRING", "description": "Patient's confirmed city"},
                    "message": {"type": "STRING", "description": "Patient's dental concern or consultation request notes"},
                    "doctor_name": {"type": "STRING", "description": "USD Certified Dentist/Doctor name requested for the consultation (must be a verified USD certified smile designer)"},
                    "is_cancel": {"type": "BOOLEAN", "description": "Whether the user requested to cancel the booking (true) or submit it (false)"}
                },
                "required": ["first_name", "phone", "city", "message", "doctor_name"]
            }
        }
    ]
}

def log_live_voice_conversation(user_text, bot_text, slots):
    fn = slots.get('first_name') or '-'
    ln = slots.get('last_name') or '-'
    name_str = f"{fn} {ln}".strip() if ln != '-' else fn
    city_str = slots.get('city') or '-'
    doc_str = slots.get('doctor_name') or '-'
    msg_str = slots.get('message') or '-'
    phone_str = slots.get('phone') or '-'
    sub_str = "YES (Submitted to CRM)" if slots.get('is_submitted') else "No"

    sep = "=" * 70
    log_msg = (
        f"\n{sep}\n"
        f"⚡ [VOICE MODE - GEMINI LIVE]\n"
        f"👤 USER : {user_text}\n"
        f"🤖 RIYA : {bot_text}\n"
        f"📋 SLOTS: Name: {name_str} | City: {city_str} | Doctor: {doc_str} | Concern: {msg_str} | Phone: {phone_str} | Submitted: {sub_str}\n"
        f"{sep}\n"
    )
    print(log_msg, flush=True)

def sanitize_gemini_history(history):
    if not isinstance(history, list):
        return []
    sliced = history
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
        sanitized.insert(0, {"role": "user", "parts": [{"text": "Hello"}]})
        
    return sanitized

def get_gemini_api_key():
    key = os.getenv("GEMINI_API_KEY_NEW", "")
    return key.strip()

class GeminiClient:
    def __init__(self, session, send_json_callback, transcribe_bot_audio_callback):
        self.session = session
        self.send_json = send_json_callback
        self.transcribe_bot_audio = transcribe_bot_audio_callback
        
        api_key = get_gemini_api_key()
        self.gemini_ws_url = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={api_key}"

    async def connect_and_loop(self, system_prompt):
        while self.session.is_client_connected:
            recv_task = None
            try:
                api_key = get_gemini_api_key()
                ws_url = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={api_key}"
                print("[INFO] Connecting to Native Gemini Live API...")
                async with websockets.connect(ws_url) as ws:
                    self.session.gemini_ws = ws
                    print("[INFO] Connected to Native Gemini Live API (v1beta)")
                    
                    self.session.setup_complete_event.clear()
                    
                    # Session Resumption: Seamlessly preserve conversation context across reconnects
                    resumption_config = {}
                    resumption_handle = getattr(self.session, 'gemini_resumption_handle', None)
                    if resumption_handle and self.session.latest_client_history:
                        print(f"[INFO] Resuming Gemini Live Session with handle: {resumption_handle[:20]}...")
                        resumption_config = {"handle": resumption_handle}
                    else:
                        self.session.gemini_resumption_handle = None

                    live_system_prompt = system_prompt
                    active_mem = []
                    if self.session.user_name:
                        active_mem.append(f"- CURRENT CONFIRMED PATIENT NAME: {self.session.user_name}")
                    if self.session.booking_slots.get("city"):
                        active_mem.append(f"- CURRENT CONFIRMED PATIENT CITY: {self.session.booking_slots.get('city')}")
                    if self.session.booking_slots.get("phone"):
                        active_mem.append(f"- CURRENT CONFIRMED 10-DIGIT PHONE: {self.session.booking_slots.get('phone')}")
                    if self.session.booking_slots.get("doctor_name"):
                        active_mem.append(f"- CURRENT CONFIRMED DOCTOR: {self.session.booking_slots.get('doctor_name')}")
                    if self.session.user_concern:
                        active_mem.append(f"- CURRENT CONFIRMED DENTAL CONCERN: {self.session.user_concern}")
                    if self.session.booking_slots.get("is_submitted"):
                        active_mem.append("- APPOINTMENT ALREADY SUBMITTED: Do NOT re-ask for booking details.")
                    if active_mem:
                        live_system_prompt += f"\n\n=========================================\nACTIVE PATIENT MEMORY (HIGH PRIORITY OVERRIDE):\n" + "\n".join(active_mem) + "\n========================================="

                    setup_message = {
                        "setup": {
                            "model": GEMINI_LIVE_MODEL,
                            "generationConfig": {
                                "responseModalities": ["AUDIO"],
                                "speechConfig": {
                                    "voiceConfig": {
                                        "prebuiltVoiceConfig": {
                                            "voiceName": "Leda"
                                        }
                                    }
                                }
                            },
                            "realtimeInputConfig": {
                                "automaticActivityDetection": {
                                    "disabled": False,
                                    "prefixPaddingMs": 400,
                                    "silenceDurationMs": 1200
                                }
                            },
                            "tools": [APPOINTMENT_TOOL_DECLARATION],
                            "sessionResumption": resumption_config,
                            "outputAudioTranscription": {},
                            "systemInstruction": {"parts": [{"text": live_system_prompt}]}
                        }
                    }
                    await ws.send(json.dumps(setup_message))
                    self.session.initial_greeting_sent = False
                    
                    # Start the receive loop task
                    recv_task = asyncio.create_task(self.gemini_recv_loop(ws))
                    
                    # Await setupComplete frame from Gemini Live with a timeout
                    try:
                        await asyncio.wait_for(self.session.setup_complete_event.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        print("[WARN] Timeout waiting for Gemini Live setupComplete!")
                    
                    # If this is a fresh connection with prior history, seed the context
                    if not resumption_handle and self.session.latest_client_history:
                        history_to_inject = sanitize_gemini_history(self.session.latest_client_history)
                        await ws.send(json.dumps({
                            "clientContent": {
                                "turns": history_to_inject,
                                "turnComplete": False
                            }
                        }))
                        self.session.initial_greeting_sent = True
                    
                    # Await the receive loop to finish cleanly when connection closes or GoAway occurs
                    await recv_task
                        
            except ConnectionClosed as e:
                print(f"[INFO] Gemini Live WS Connection closed: {e}")
            except Exception as e:
                print(f"[ERROR] Gemini Live WS Error: {e}")
            finally:
                self.session.gemini_ws = None
                if recv_task and not recv_task.done():
                    recv_task.cancel()
                    
            if not self.session.is_client_connected:
                break
                
            print("[INFO] Gemini Live connection reset. Automatically reconnecting & resuming session...")
            await asyncio.sleep(0.3)

    async def gemini_recv_loop(self, ws):
        try:
            async for raw_message in ws:
                if not self.session.is_client_connected:
                    break
                    
                response = json.loads(raw_message)
                
                # SESSION RESUMPTION UPDATES (Store fresh handle for zero-interruption reconnects)
                if "sessionResumptionUpdate" in response:
                    update = response["sessionResumptionUpdate"]
                    if update.get("resumable") and update.get("newHandle"):
                        self.session.gemini_resumption_handle = update["newHandle"]
                        print(f"[INFO] Stored Gemini Live Resumption Handle: {self.session.gemini_resumption_handle[:20]}...")
                    continue

                # GOAWAY SIGNAL: Server signals upcoming connection closure. Cleanly close to trigger instant resumption
                if "goAway" in response:
                    go_away = response["goAway"]
                    time_left = go_away.get("timeLeft", "unknown")
                    print(f"[WARN] Gemini Live GoAway received (time left: {time_left}). Triggering clean session resumption...")
                    await ws.close()
                    break

                if "setupComplete" in response:
                    print("[INFO] Gemini Live Setup Complete!")
                    self.session.setup_complete_event.set()
                    continue

                # ⚡ TOOL CALL HANDLING (Direct Appointment Submission via Ultimate Smile Design API) ⚡
                if "toolCall" in response:
                    tool_call = response["toolCall"]
                    function_calls = tool_call.get("functionCalls", [])
                    function_responses = []
                    for fc in function_calls:
                        func_name = fc.get("name")
                        func_id = fc.get("id")
                        args = fc.get("args", {})
                        print(f"[INFO] Gemini Live invoked Tool Call: {func_name} with args: {args}")
                        if func_name == "submit_appointment_booking":
                            sum_slots = extract_slots_from_review_summary(self.session.full_bot_reply or self.session.display_str)
                            if sum_slots:
                                for k, v in sum_slots.items():
                                    if v:
                                        self.session.booking_slots[k] = v
                                if sum_slots.get("user_name"):
                                    self.session.user_name = sum_slots["user_name"]
                                if sum_slots.get("user_concern"):
                                    self.session.user_concern = sum_slots["user_concern"]
                            full_args = dict(args)
                            for k, v in self.session.booking_slots.items():
                                if v and v != "-" and str(v).lower() not in ["none", "null"]:
                                    full_args[k] = v
                            full_args["submission_id"] = self.session.booking_slots.get("submission_id")
                            result = await submit_consultation_appointment(full_args)
                            if result.get("status") == "success":
                                self.session.booking_slots["is_submitted"] = True
                                if "details" in result and "data" in result["details"] and "id" in result["details"]["data"]:
                                    if not self.session.booking_slots.get("submission_id"):
                                        self.session.booking_slots["submission_id"] = result["details"]["data"]["id"]
                                for k, v in full_args.items():
                                    if v is not None:
                                        self.session.booking_slots[k] = str(v)
                                await self.send_json({
                                    "type": "sync_slots",
                                    "slots": self.session.booking_slots
                                })
                            function_responses.append({
                                "name": func_name,
                                "id": func_id,
                                "response": {"result": result}
                            })
                        else:
                            function_responses.append({
                                "name": func_name,
                                "id": func_id,
                                "response": {"result": {"status": "error", "message": f"Unknown tool: {func_name}"}}
                            })
                    
                    tool_response_message = {
                        "toolResponse": {
                            "functionResponses": function_responses
                        }
                    }
                    await ws.send(json.dumps(tool_response_message))
                    print("[INFO] Sent tool response back to Gemini Live WebSocket")
                    continue
                    
                server_content = response.get("serverContent", {})
                if not server_content:
                    continue
                    
                # OFFICIAL GEMINI VAD BARGE-IN / INTERRUPTION HANDLING
                if server_content.get("interrupted"):
                    print("[INFO] Gemini Official VAD Interruption / Barge-in Detected!")
                    self.session.is_interrupted = True
                    self.session.display_str = ""
                    self.session.full_bot_reply = ""
                    self.session.assistant_audio_buffer = bytearray()
                    self.session.live_pcm_buffer = bytearray()
                    
                    # Cut off assistant playback in frontend immediately
                    await self.send_json({
                        "type": "interrupted",
                        "turnId": self.session.current_voice_turn_id
                    })
                        
                    await asyncio.sleep(0.05)
                    if self.session.is_client_connected:
                        self.session.is_interrupted = False
                    else:
                        return
                
                if self.session.is_interrupted:
                    if server_content.get("turnComplete") or "outputTranscription" in server_content or "modelTurn" in server_content:
                        self.session.is_interrupted = False
                    else:
                        return
                
                # NATIVE GEMINI LIVE REAL-TIME TRANSCRIPTIONS (REAL-TIME STREAMING SUBTITLES)
                if "outputTranscription" in server_content:
                    raw_chunk = server_content["outputTranscription"].get("text", "")
                    bot_chunk = re.sub(r"\d{1,2}:\d{2}(:\d{2})?(\.\d+)?\s*-->\s*\d{1,2}:\d{2}(:\d{2})?(\.\d+)?", "", raw_chunk)
                    bot_chunk = re.sub(r"^\s*\d{1,2}:\d{2}(:\d{2})?\s*$", "", bot_chunk)
                    if bot_chunk:
                        self.session.full_bot_reply += bot_chunk
                        self.session.display_str += bot_chunk
                        
                        # Update conversation language based on the bot's tag
                        lang_match = re.search(r"\[(hi|bn|ta|te|mr|gu|kn|ml|pa|or|en)-IN\]", self.session.full_bot_reply, re.IGNORECASE)
                        if lang_match:
                            self.session.current_language = f"{lang_match.group(1).lower()}-IN"
                            
                        best_tag = detect_best_tag(self.session.latest_typed_user_text, self.session.display_str)
                        await self.send_json({
                            "type": "bot_text_chunk",
                            "text": bot_chunk,
                            "tag": best_tag,
                            "turnId": self.session.current_voice_turn_id
                        })

                if "inputTranscription" in server_content:
                    raw_user_chunk = server_content["inputTranscription"].get("text", "")
                    user_chunk = clean_hallucinations(raw_user_chunk)
                    if user_chunk:
                        self.session.current_user_transcription += user_chunk
                        if getattr(self, 'conversation_manager', None):
                            self.conversation_manager.update_session_memory(self.session.current_user_transcription, self.session.latest_client_history)
                        await self.send_json({
                            "type": "user_text_chunk",
                            "text": user_chunk,
                            "turnId": self.session.current_voice_turn_id,
                            "slots": dict(self.session.booking_slots),
                            "userName": self.session.user_name,
                            "userConcern": self.session.user_concern,
                            "userCity": self.session.booking_slots.get("city"),
                            "userDoctor": self.session.booking_slots.get("doctor_name"),
                            "userPhone": self.session.booking_slots.get("phone")
                        })

                if "modelTurn" in server_content:
                    parts = server_content["modelTurn"].get("parts", [])
                    for part in parts:
                        if "functionCall" in part:
                            fc = part["functionCall"]
                            func_name = fc.get("name")
                            args = fc.get("args", {})
                            if func_name == "submit_appointment_booking":
                                sum_slots = extract_slots_from_review_summary(self.session.full_bot_reply or self.session.display_str)
                                if sum_slots:
                                    for k, v in sum_slots.items():
                                        if v:
                                            self.session.booking_slots[k] = v
                                    if sum_slots.get("user_name"):
                                        self.session.user_name = sum_slots["user_name"]
                                    if sum_slots.get("user_concern"):
                                        self.session.user_concern = sum_slots["user_concern"]
                                full_args = dict(self.session.booking_slots)
                                full_args.update(args)
                                full_args["submission_id"] = self.session.booking_slots.get("submission_id")
                                res = await submit_consultation_appointment(full_args)
                                if res.get("status") == "success":
                                    self.session.booking_slots["is_submitted"] = True
                                    if "details" in res and "data" in res["details"] and "id" in res["details"]["data"]:
                                        if not self.session.booking_slots.get("submission_id"):
                                            self.session.booking_slots["submission_id"] = res["details"]["data"]["id"]
                                    for k, v in full_args.items():
                                        if v is not None:
                                            self.session.booking_slots[k] = str(v)
                                    await self.send_json({
                                        "type": "sync_slots",
                                        "slots": self.session.booking_slots
                                    })
                                print(f"[INFO] Gemini Live modelTurn part invoked submit_appointment_booking with args: {full_args}, result: {res}")

                        if "text" in part and part["text"]:
                            raw_txt = part["text"]
                            bot_chunk = re.sub(r"\d{1,2}:\d{2}(:\d{2})?(\.\d+)?\s*-->\s*\d{1,2}:\d{2}(:\d{2})?(\.\d+)?", "", raw_txt)
                            bot_chunk = re.sub(r"^\s*\d{1,2}:\d{2}(:\d{2})?\s*$", "", bot_chunk)
                            if bot_chunk and bot_chunk not in self.session.full_bot_reply:
                                self.session.full_bot_reply += bot_chunk
                                self.session.display_str += bot_chunk
                                best_tag = detect_best_tag(self.session.latest_typed_user_text, self.session.display_str)
                                await self.send_json({
                                    "type": "bot_text_chunk",
                                    "text": bot_chunk,
                                    "tag": best_tag,
                                    "turnId": self.session.current_voice_turn_id
                                })

                        if "inlineData" in part:
                            incoming_pcm = base64.b64decode(part["inlineData"]["data"])
                            self.session.live_pcm_buffer.extend(incoming_pcm)
                            self.session.assistant_audio_buffer.extend(incoming_pcm)
                            
                        # Stream audio chunks with smooth buffer alignment (9600 bytes = 200ms of 24kHz 16-bit PCM)
                        if len(self.session.live_pcm_buffer) >= 9600:
                            send_len = len(self.session.live_pcm_buffer) - (len(self.session.live_pcm_buffer) % 2)
                            send_bytes = self.session.live_pcm_buffer[:send_len]
                            self.session.live_pcm_buffer = self.session.live_pcm_buffer[send_len:]
                            wav_base64 = wrap_pcm_to_wav_base64(send_bytes, 24000)
                            await self.send_json({
                                "type": "audio_chunk",
                                "audioBase64": wav_base64,
                                "index": self.session.chunk_index
                            })
                            self.session.chunk_index += 1
                
                if server_content.get("turnComplete"):
                    if len(self.session.live_pcm_buffer) > 0:
                        send_len = len(self.session.live_pcm_buffer) - (len(self.session.live_pcm_buffer) % 2)
                        if send_len > 0:
                            send_bytes = self.session.live_pcm_buffer[:send_len]
                            self.session.live_pcm_buffer = bytearray()
                            wav_base64 = wrap_pcm_to_wav_base64(send_bytes, 24000)
                            await self.send_json({
                                "type": "audio_chunk",
                                "audioBase64": wav_base64,
                                "index": self.session.chunk_index
                            })
                            self.session.chunk_index += 1
                    
                    current_assistant_audio = bytes(self.session.assistant_audio_buffer)
                    self.session.assistant_audio_buffer = bytearray()
                    
                    # Resolve user transcription with fallback
                    user_text = ""
                    if self.session.user_transcription_task:
                        try:
                            user_text = await asyncio.wait_for(asyncio.shield(self.session.user_transcription_task), timeout=0.6)
                        except Exception:
                            if self.session.user_transcription_task.done():
                                try:
                                    user_text = self.session.user_transcription_task.result()
                                except Exception:
                                    pass
                    if not user_text:
                        user_text = self.session.current_user_transcription or self.session.latest_typed_user_text or ""
                    
                    bot_text_to_send = self.session.full_bot_reply or ""
                    clean_text = clean_assistant_text(bot_text_to_send) if bot_text_to_send else ""
                    
                    if getattr(self, 'conversation_manager', None):
                        if user_text and user_text != "Message":
                            self.conversation_manager.update_session_memory(user_text, self.session.latest_client_history)
                        if clean_text:
                            temp_h = list(self.session.latest_client_history or []) + [{"role": "model", "parts": [{"text": clean_text}]}]
                            self.conversation_manager.update_session_memory("", temp_h)

                    # ⚡ Synchronize any review summary slots from bot response ⚡
                    summary_slots = extract_slots_from_review_summary(clean_text or bot_text_to_send)
                    if summary_slots:
                        self.session.last_review_summary_slots = dict(summary_slots)
                        self.session.last_review_summary_text = clean_text or bot_text_to_send
                        for k, v in summary_slots.items():
                            if v and str(v).lower() not in ["none", "null", "-", "--"]:
                                if k in ["first_name", "last_name", "user_name"]:
                                    if not self.session.user_name:
                                        self.session.booking_slots[k] = v
                                else:
                                    self.session.booking_slots[k] = v
                        if summary_slots.get("user_name") and not self.session.user_name:
                            self.session.user_name = summary_slots["user_name"]
                        if (summary_slots.get("user_concern") or summary_slots.get("message")) and not self.session.user_concern:
                            self.session.user_concern = summary_slots.get("user_concern") or summary_slots.get("message")
                        await self.send_json({
                            "type": "sync_slots",
                            "slots": self.session.booking_slots
                        })

                    # ⚡ Fast-path submission in Voice Mode if user affirms or model confirms ⚡
                    bot_reply_lower = (self.session.full_bot_reply or "").lower()
                    is_model_confirmed = any(w in bot_reply_lower for w in ["successfully submitted", "appointment request has been", "appointment has been submitted", "સફળતાપૂર્વક સબમિટ", "સબમિટ થઈ ગઈ છે", "સબમિટ કરવામાં આવી", "सफलतापूर्वक सबमिट", "सबमिट हो गई"])
                    is_user_affirmed = is_affirmative_submit(user_text)

                    if (is_model_confirmed or is_user_affirmed) and not self.session.booking_slots.get("is_submitted"):
                        confirmed_slots = dict(getattr(self.session, "last_review_summary_slots", {}) or {})
                        slots_to_send = dict(self.session.booking_slots)
                        if self.session.user_name:
                            u_parts = self.session.user_name.split()
                            slots_to_send["first_name"] = u_parts[0]
                            slots_to_send["last_name"] = " ".join(u_parts[1:]) if len(u_parts) > 1 else "-"
                        if self.session.user_concern:
                            slots_to_send["message"] = self.session.user_concern
                        
                        has_fn = bool(slots_to_send.get("first_name") and slots_to_send["first_name"].lower() not in ["", "none", "null", "patient", "user"])
                        has_city = bool(slots_to_send.get("city") and any(c.lower() == str(slots_to_send["city"]).strip().lower() for c in CERTIFIED_CITIES))
                        has_doc = bool(slots_to_send.get("doctor_name") and slots_to_send["doctor_name"] not in ["", "none", "null", "usd certified smile designer"])
                        has_msg = bool(slots_to_send.get("message") and len(slots_to_send["message"].strip()) >= 2)
                        has_phone = bool(slots_to_send.get("phone") and len("".join(filter(str.isdigit, str(slots_to_send["phone"])))) == 10)

                        if (has_fn and has_city and has_doc and has_msg and has_phone) or bool(confirmed_slots):
                            slots_to_send["submission_id"] = self.session.booking_slots.get("submission_id")
                            res = await submit_consultation_appointment(slots_to_send)
                            if res.get("status") == "success":
                                self.session.booking_slots["is_submitted"] = True
                                if "details" in res and "data" in res["details"] and "id" in res["details"]["data"]:
                                    if not self.session.booking_slots.get("submission_id"):
                                        self.session.booking_slots["submission_id"] = res["details"]["data"]["id"]
                                await self.send_json({
                                    "type": "sync_slots",
                                    "slots": self.session.booking_slots
                                })
                                print(f"[INFO] Fast-path appointment submitted in Voice Mode: {slots_to_send}")

                    if len(current_assistant_audio) > 0 or len(clean_text) > 0:
                        final_tag, new_pending = detect_best_tag_with_fallback(
                            user_text, clean_text or "...", self.session.pending_action_tag
                        )
                        self.session.pending_action_tag = new_pending
                        
                        await self.send_json({
                            "type": "bot_spoken_text",
                            "text": clean_text or "...",
                            "tag": final_tag,
                            "turnId": self.session.current_voice_turn_id
                        })
                        
                        log_live_voice_conversation(user_text, clean_text or "...", dict(self.session.booking_slots))
                        await self.send_json({
                            "type": "reply_complete",
                            "userText": user_text,
                            "botText": clean_text or "...",
                            "tag": final_tag,
                            "totalChunks": self.session.chunk_index,
                            "slots": dict(self.session.booking_slots),
                            "userName": self.session.user_name,
                            "userConcern": self.session.user_concern,
                            "userCity": self.session.booking_slots.get("city"),
                            "userDoctor": self.session.booking_slots.get("doctor_name"),
                            "userPhone": self.session.booking_slots.get("phone")
                        })
                        
                        # Background Bot STT transcription only if we did not get native transcription and have audio
                        if not self.session.full_bot_reply and len(current_assistant_audio) > 0:
                            asyncio.create_task(self.transcribe_bot_audio(current_assistant_audio))
                            
                    else:
                        await self.send_json({"type": "idle"})
                    
                    # ⚡ RESET FOR NEXT VOICE TURN (Distinct chat bubble & clear transcription accumulator) ⚡
                    self.session.chunk_index = 0
                    self.session.display_str = ""
                    self.session.full_bot_reply = ""
                    self.session.current_user_transcription = ""
                    self.session.current_voice_turn_id += 1
                    self.session.reset_activity_timer()
                    self.session.latest_client_history = []
        except Exception as e:
            print(f"[ERROR] Error parsing Gemini WS frame: {e}")

    async def stream_gemini_chat_reply(self, user_text, history, system_prompt):
        try:
            api_key = os.getenv("GEMINI_API_KEY_NEW") or os.getenv("GEMINI_API_KEY")
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
            best_tag = detect_best_tag(user_text, "")
            
            max_retries = 3
            success = False
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    display_str = "" # Reset on retry
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
                                        await self.send_json({
                                            "type": "bot_text_chunk",
                                            "text": delta,
                                            "tag": best_tag
                                        })
                                except Exception:
                                    pass
                    success = True
                    break
                except Exception as e:
                    last_error = e
                    if "50" in str(e) or "429" in str(e): # Handle 5xx and 429
                        print(f"[WARNING] Gemini API error: {e}. Retrying {attempt+1}/{max_retries}...")
                        await asyncio.sleep(2 * (attempt + 1))
                    else:
                        raise e
            
            if not success:
                raise last_error
            
            final_text = clean_assistant_text(display_str.strip() or "Okay.")
            final_tag, new_pending = detect_best_tag_with_fallback(
                user_text, final_text, self.session.pending_action_tag
            )
            self.session.pending_action_tag = new_pending
            
            await self.send_json({
                "type": "bot_spoken_text",
                "text": final_text,
                "tag": final_tag
            })
                    
            await self.send_json({
                "type": "reply_complete",
                "userText": user_text or "Text Input",
                "botText": final_text,
                "tag": final_tag,
                "totalChunks": 0
            })
            self.session.reset_activity_timer()
        except Exception as e:
            print(f"[ERROR] Chat mode text generation error: {e}")
            fallback_text = "I'm sorry, I am having trouble processing that right now. Please try asking again."
            await self.send_json({
                "type": "bot_spoken_text",
                "text": fallback_text
            })
            await self.send_json({
                "type": "reply_complete",
                "userText": user_text or "Text Input",
                "botText": fallback_text,
                "tag": final_tag if 'final_tag' in locals() else None,
                "totalChunks": 0
            })
            self.session.reset_activity_timer()

    async def transcribe_interrupted_bot_text(self, audio_bytes, turn_id):
        try:
            lang = self.session.current_language or 'en-IN'
            bot_text = await transcribe_voice_data(audio_bytes, 24000, language_code=lang)
            if bot_text:
                clean_text = clean_assistant_text(bot_text).strip()
                if clean_text:
                    if not clean_text.endswith("..."):
                        clean_text += " ..."
                    best_tag = detect_best_tag(self.session.latest_typed_user_text, clean_text)
                    await self.send_json({
                        "type": "bot_spoken_text",
                        "text": clean_text,
                        "tag": best_tag,
                        "turnId": turn_id
                    })
        except Exception as e:
            print(f"Error transcribing interrupted bot text: {e}")
