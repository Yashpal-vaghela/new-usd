import json
import asyncio
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from voice_agent.ai.session_manager import Session
from voice_agent.ai.conversation_manager import ConversationManager
from voice_agent.gemini.client import GeminiClient
from voice_agent.ai.prompt_builder import get_system_prompt

class VoiceAgentConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.session = Session()
        
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

    async def receive(self, text_data=None, bytes_data=None):
        if bytes_data:
            # Delegate raw client PCM chunks to conversation coordinator
            await self.conversation_manager.handle_audio_chunk(bytes_data)
        elif text_data:
            try:
                data = json.loads(text_data)
                if data.get("type") == "restore_slots":
                    slots = data.get("slots", {})
                    if slots:
                        self.session.booking_slots.update(slots)
                    return
                # Delegate JSON events to NLU coordinator
                await self.conversation_manager.handle_client_json(data, self.system_prompt)
            except Exception as e:
                print(f"[ERROR] Error routing JSON payload: {e}")

    async def transcribe_bot_audio_via_manager(self, audio_bytes):
        # Helper callback to bridge gemini response handler to transcriber
        await self.conversation_manager.transcribe_and_sync_bot_text(audio_bytes)
