import os
import json
import asyncio
import base64
import threading
import uuid
from urllib.parse import parse_qs
from asgiref.sync import sync_to_async
from django.core.files.base import ContentFile
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from voice_agent.models import VoiceRecordingLog
from voice_agent.ai.session_manager import Session
from voice_agent.ai.conversation_manager import ConversationManager
from voice_agent.gemini.client import GeminiClient
from voice_agent.ai.prompt_builder import get_system_prompt
from voice_agent.views import dispatch_feedback_email
from voice_agent.utils.ios_debug import ios_debug_log

class VoiceAgentConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.session = Session()

        # iOS clients connect with ?platform=ios so the Gemini VAD can be tuned for weaker iOS echo cancellation
        query = parse_qs(self.scope.get("query_string", b"").decode())
        self.session.is_ios = query.get("platform", [""])[0] == "ios"

        # ⚡ Dynamically build prompt instructions and retrieve cached knowledge base
        self.system_prompt = get_system_prompt()
        
        # ⚡ Create client endpoints and NLU orchestrators
        self.gemini_client = GeminiClient(
            session=self.session,
            send_json_callback=self.send_json,
            transcribe_bot_audio_callback=self.transcribe_bot_audio_via_manager
        )
        
        self.conversation_manager = ConversationManager(
            session=self.session,
            send_json_callback=self.send_json,
            gemini_client=self.gemini_client
        )
        self.gemini_client.conversation_manager = self.conversation_manager
        
        # Accept ASGI WebSocket connection
        await self.accept()
        print("[INFO] Client connected via WebSocket")
        
        # ⚡ Spawn native Gemini Live connection loop
        self.session.gemini_recv_task = asyncio.create_task(
            self.gemini_client.connect_and_loop(self.system_prompt)
        )
        
        # ⚡ Spawn inactivity timer monitoring loop
        self.session.inactivity_task = asyncio.create_task(
            self.conversation_manager.inactivity_monitor_loop(self.close)
        )

    async def disconnect(self, close_code):
        self.session.is_client_connected = False
        ios_debug_log(self.session, "disconnect", code=close_code)
        
        # Cancel all background tasks
        if self.session.inactivity_task:
            self.session.inactivity_task.cancel()
        if self.session.text_mode_task:
            self.session.text_mode_task.cancel()
        if self.session.gemini_recv_task:
            self.session.gemini_recv_task.cancel()
        if self.session.user_transcription_task:
            self.session.user_transcription_task.cancel()
            
        # Close native Live WebSocket connection
        if self.session.gemini_ws:
            try:
                await self.session.gemini_ws.close()
            except Exception:
                pass
                
        print("[INFO] Client disconnected")

        # ⚡ Auto-save conversation transcript to VoiceRecordingLog on Disconnect / Hard Refresh / Close ⚡
        try:
            transcript_text = self.session.get_full_transcript()
            if transcript_text and transcript_text.strip():
                import uuid
                from voice_agent.models import VoiceRecordingLog
                from asgiref.sync import sync_to_async
                
                call_id = getattr(self.session, 'call_id', None) or f"call_{uuid.uuid4().hex[:10]}"
                conv_type = getattr(self.session, 'conversation_type', 'voice_agent')
                
                @sync_to_async
                def save_disconnect_log():
                    is_sub = bool(getattr(self.session, 'booking_slots', {}).get("is_submitted"))
                    is_cnc = bool(getattr(self.session, 'booking_slots', {}).get("is_cancel"))
                    doc_lbl = getattr(self.session, 'booking_slots', {}).get("doctor_name") or "USD Dentist"
                    sub_id = getattr(self.session, 'booking_slots', {}).get("submission_id")
                    sub_lbl = f"Lead #{sub_id}" if sub_id else ""

                    default_save_type = 'submit_feedback' if is_sub else 'without_submit'
                    if is_cnc:
                        default_rating = f"Appointment Cancelled ({sub_lbl})" if sub_lbl else "Appointment Cancelled"
                    elif is_sub:
                        default_rating = f"Appointment Booked: {doc_lbl} ({sub_lbl})" if sub_lbl else f"Appointment Booked: {doc_lbl}"
                    else:
                        default_rating = 'Call Ended (Page Refreshed)'

                    log_record, created = VoiceRecordingLog.objects.get_or_create(
                        call_id=call_id,
                        defaults={
                            'rating': default_rating,
                            'transcript': transcript_text,
                            'save_type': default_save_type,
                            'conversation_type': conv_type
                        }
                    )
                    if not created:
                        if is_sub:
                            log_record.save_type = 'submit_feedback'
                            log_record.rating = default_rating
                        curr_len = len((log_record.transcript or "").strip())
                        new_len = len(transcript_text.strip())
                        if new_len >= curr_len:
                            log_record.transcript = transcript_text
                        log_record.save()
                    print(f"[INFO] Saved VoiceRecordingLog #{log_record.id} on WebSocket disconnect (created={created}, save_type={log_record.save_type})")

                await save_disconnect_log()
        except Exception as e:
            print(f"[WARN] Error saving disconnect log: {e}")

    async def receive(self, text_data=None, bytes_data=None):
        if bytes_data:
            # Delegate raw client PCM chunks to conversation coordinator
            await self.conversation_manager.handle_audio_chunk(bytes_data)
        elif text_data:
            try:
                data = json.loads(text_data)
                if data.get("type") == "ios_debug":
                    # An iOS client in meter mode (?ios_test=meter) turns on debug logging for this session
                    if self.session.is_ios and not self.session.ios_debug:
                        self.session.ios_debug = True
                        ios_debug_log(self.session, "debug_on")
                    data.pop("type")
                    ios_debug_log(self.session, data.pop("ev", "client"), **data)
                    return
                if data.get("call_id"):
                    self.session.call_id = data.get("call_id")
                if data.get("conversation_type"):
                    self.session.conversation_type = data.get("conversation_type")
                if data.get("type") == "init_session":
                    if data.get("call_id"):
                        self.session.call_id = data.get("call_id")
                    if data.get("conversation_type"):
                        self.session.conversation_type = data.get("conversation_type")
                    return
                if data.get("type") == "restore_slots":
                    slots = data.get("slots", {})
                    if slots:
                        self.session.booking_slots.update(slots)
                        if slots.get("first_name"):
                            self.session.user_name = slots.get("first_name")
                        if slots.get("message"):
                            self.session.user_concern = slots.get("message")
                    return
                if data.get("type") == "submit_feedback":
                    payload = data.get("payload", {}) or data.get("data", {})
                    rating = payload.get("rating", "Call Completed")
                    transcript = payload.get("transcript", "No transcript provided.")
                    audio_b64 = payload.get("audio_base64")
                    audio_filename = payload.get("audio_filename", "voice_recording.webm")
                    audio_bytes = None
                    if audio_b64:
                        if "," in audio_b64:
                            audio_b64 = audio_b64.split(",", 1)[1]
                        try:
                            audio_bytes = base64.b64decode(audio_b64)
                        except Exception as e:
                            print(f"[WARN] Error decoding audio base64 over WS: {e}")
                    call_id = payload.get("call_id") or getattr(self.session, 'call_id', None) or f"call_{uuid.uuid4().hex[:10]}"
                    is_sub = bool(getattr(self.session, 'booking_slots', {}).get("is_submitted"))
                    save_type = "submit_feedback" if is_sub else (payload.get("save_type") or payload.get("tag") or ("submit_feedback" if ("Stars" in rating or "Submit" in rating or "feedback" in rating.lower()) else "without_submit"))
                    conv_type = payload.get("conversation_type", getattr(self.session, 'conversation_type', 'voice_agent'))
                    
                    @sync_to_async
                    def save_ws_feedback():
                        log_record, created = VoiceRecordingLog.objects.get_or_create(
                            call_id=call_id,
                            defaults={
                                'rating': rating,
                                'transcript': transcript,
                                'save_type': save_type,
                                'conversation_type': conv_type
                            }
                        )
                        if not created:
                            if transcript and transcript != "No transcript provided.":
                                curr_len = len((log_record.transcript or "").strip())
                                if len(transcript.strip()) >= curr_len:
                                    log_record.transcript = transcript
                            if save_type == 'submit_feedback' or log_record.save_type != 'submit_feedback':
                                log_record.rating = rating
                                log_record.save_type = save_type
                            if conv_type:
                                log_record.conversation_type = conv_type
                        if audio_bytes and len(audio_bytes) > 0:
                            has_valid_file = False
                            try:
                                has_valid_file = bool(log_record.audio_file and log_record.audio_file.name and os.path.exists(log_record.audio_file.path))
                            except Exception:
                                has_valid_file = False
                            if not has_valid_file:
                                unique_filename = f"rec_{uuid.uuid4().hex[:8]}_{audio_filename}"
                                log_record.audio_file.save(unique_filename, ContentFile(audio_bytes), save=False)
                        log_record.save()
                        print(f"[INFO] Saved VoiceRecordingLog #{log_record.id} via WebSocket (audio={bool(audio_bytes)}, save_type={save_type})")

                    try:
                        await save_ws_feedback()
                    except Exception as save_err:
                        print(f"[WARN] Error saving WS feedback to DB: {save_err}")
                    
                    await self.send_json({"type": "feedback_ack", "status": "success"})
                    return
                # Delegate JSON events to NLU coordinator
                await self.conversation_manager.handle_client_json(data, self.system_prompt)
            except Exception as e:
                print(f"[ERROR] Error routing JSON payload: {e}")

    async def transcribe_bot_audio_via_manager(self, audio_bytes):
        # Helper callback to bridge gemini response handler to transcriber
        await self.conversation_manager.transcribe_and_sync_bot_text(audio_bytes)
