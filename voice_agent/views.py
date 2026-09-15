import os
import json
import base64
import uuid
import datetime
import threading
import httpx
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from voice_agent.audio.transcoder import wrap_pcm_to_wav_base64

def chat_bot(request):
    return render(request, 'chat_bot.html')

@csrf_exempt
def api_tts(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)
    
    try:
        data = json.loads(request.body.decode('utf-8'))
        text = data.get('text', 'Okay.')
    except Exception as e:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)
    
    api_key = os.getenv('GEMINI_API_KEY_NEW') or os.getenv('GEMINI_API_KEY')
    if not api_key:
        return JsonResponse({'error': 'GEMINI_API_KEY is not set'}, status=500)
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-tts-preview:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": "Despina"
                    }
                }
            }
        }
    }
    
    try:
        response = httpx.post(url, json=payload, timeout=20.0)
        if response.status_code != 200:
            return JsonResponse({'error': f'Gemini TTS Failed: {response.text}'}, status=500)
        
        result = response.json()
        candidates = result.get('candidates', [])
        if not candidates:
            return JsonResponse({'error': 'No content candidates returned'}, status=500)
        
        inline_data = candidates[0].get('content', {}).get('parts', [{}])[0].get('inlineData', {})
        audio_data = inline_data.get('data')
        
        if not audio_data:
            return JsonResponse({'error': 'No audio returned from Gemini TTS'}, status=500)
        
        # Convert raw PCM base64 payload to WAV base64
        pcm_bytes = base64.b64decode(audio_data)
        wav_base64 = wrap_pcm_to_wav_base64(pcm_bytes, 24000)
        return JsonResponse({'audioBase64': wav_base64})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ==============================================================================
# Voice Agent Independent Email Configuration (ONLY Voice Agent - not other mails)
# FROM (Sender)   : vaghela9632@gmail.com
# TO (Destination): marketing@advancedentalexport.com
# ==============================================================================
SENDER_GMAIL = os.getenv('SENDER_GMAIL', 'vaghela9632@gmail.com')
SENDER_GMAIL_APP_PASSWORD = os.getenv('SENDER_GMAIL_APP_PASSWORD', 'ooby stkw cvkn wzwy')
FEEDBACK_RECIPIENT_EMAILS = [
    os.getenv('MARKETING_EMAIL', 'marketing@advancedentalexport.com'),
]

def dispatch_feedback_email(rating_label='Call Completed', transcript='No transcript provided.', audio_bytes=None, audio_filename='voice_recording.webm'):
    """Sends independent Gmail SMTP email with transcript and attached in-memory audio recording."""
    try:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        email_body = (
            f"=========================================\n"
            f"🌟 ULTIMATE SMILE DESIGN VOICE AGENT LOG\n"
            f"=========================================\n\n"
            f"• Event / Status: {rating_label}\n"
            f"• Timestamp: {now_str}\n\n"
            f"=========================================\n"
            f"CONVERSATION TRANSCRIPT:\n"
            f"=========================================\n\n"
            f"{transcript.strip()}\n\n"
            f"=========================================\n"
        )
        
        if SENDER_GMAIL and SENDER_GMAIL_APP_PASSWORD:
            connection = get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host='smtp.gmail.com',
                port=587,
                username=SENDER_GMAIL,
                password=SENDER_GMAIL_APP_PASSWORD,
                use_tls=True,
            )
            from_email_str = f"USD Voice Agent <{SENDER_GMAIL}>"
        else:
            connection = None
            from_email_str = f"USD Voice Agent <{SENDER_GMAIL}>"
        
        email_msg = EmailMessage(
            subject=f"🌟 USD Voice Agent: {rating_label}",
            body=email_body,
            from_email=from_email_str,
            to=FEEDBACK_RECIPIENT_EMAILS,
            reply_to=[SENDER_GMAIL],
            connection=connection
        )
        
        if audio_bytes and len(audio_bytes) > 0:
            try:
                mime_type = 'audio/webm'
                if audio_filename.endswith('.mp4'):
                    mime_type = 'audio/mp4'
                elif audio_filename.endswith('.wav'):
                    mime_type = 'audio/wav'
                elif audio_filename.endswith('.opus'):
                    mime_type = 'audio/ogg'
                email_msg.attach(audio_filename, audio_bytes, mime_type)
                size_kb = round(len(audio_bytes) / 1024, 1)
                email_msg.body += f"\n🎙️ AUDIO RECORDING ATTACHED:\n• File: {audio_filename} (~{size_kb} KB, Opus compressed)\n"
            except Exception as att_err:
                print(f"[WARNING] Failed to attach in-memory audio: {att_err}")
                
        email_msg.send(fail_silently=False)
        print(f"[INFO] Direct Gmail SMTP delivery successful from {from_email_str} to {FEEDBACK_RECIPIENT_EMAILS} (Audio attached: {bool(audio_bytes)})")
        return True
    except Exception as e:
        import traceback
        print(f"[ERROR] Direct Gmail SMTP delivery error: {e}")
        traceback.print_exc()
        return False

@csrf_exempt
def submit_feedback(request):
    """
    Receives transcript, rating, and optional raw recorded audio file.
    Accepts both application/json (with base64 audio) and multipart/form-data.
    Directly sends email to recipients via Django SMTP (Gmail),
    attaching the audio file directly in-memory without saving to local disk.
    """
    if request.method == 'OPTIONS':
        response = JsonResponse({'status': 'ok'})
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken'
        return response
        
    if request.method != 'POST':
        response = JsonResponse({'error': 'Only POST method is allowed'}, status=405)
        response['Access-Control-Allow-Origin'] = '*'
        return response
    
    try:
        rating_label = 'Call Completed'
        transcript = 'No transcript provided.'
        audio_bytes = None
        audio_filename = 'voice_recording.webm'
        
        # Check if request is JSON
        if request.content_type and 'application/json' in request.content_type:
            try:
                body_data = json.loads(request.body.decode('utf-8'))
            except Exception:
                body_data = {}
            rating_label = body_data.get('rating', 'Call Completed')
            transcript = body_data.get('transcript', 'No transcript provided.')
            audio_b64 = body_data.get('audio_base64')
            if audio_b64:
                if ',' in audio_b64:
                    audio_b64 = audio_b64.split(',', 1)[1]
                try:
                    audio_bytes = base64.b64decode(audio_b64)
                    audio_filename = body_data.get('audio_filename', 'voice_recording.webm')
                except Exception as b64_err:
                    print(f"[WARN] Error decoding audio base64: {b64_err}")
        else:
            rating_label = request.POST.get('rating', 'Call Completed')
            transcript = request.POST.get('transcript', 'No transcript provided.')
            audio_file = request.FILES.get('audio') or request.FILES.get('file')
            if audio_file:
                audio_filename = audio_file.name or 'voice_recording.webm'
                audio_bytes = audio_file.read()
        
        # ⚡ Dispatch email asynchronously so web worker finishes immediately without freezing the website ⚡
        t = threading.Thread(
            target=dispatch_feedback_email,
            args=(rating_label, transcript, audio_bytes, audio_filename),
            daemon=False
        )
        t.start()

        response = JsonResponse({
            'status': 'success',
            'rating': rating_label,
            'audio_attached': bool(audio_bytes)
        })
        response['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        print(f"[ERROR] submit_feedback failed: {e}")
        response = JsonResponse({'error': str(e)}, status=500)
        response['Access-Control-Allow-Origin'] = '*'
        return response

def wrap_pcm_to_wav_base64(base64_pcm, sample_rate=24000):
    pcm_data = base64.b64decode(base64_pcm)
    header = bytearray(44)
    
    # RIFF Identifier
    header[0:4] = b'RIFF'
    # File Size (36 + data size)
    file_size = 36 + len(pcm_data)
    header[4:8] = file_size.to_bytes(4, 'little')
    # WAVE Header
    header[8:12] = b'WAVE'
    # fmt Chunk
    header[12:16] = b'fmt '
    header[16:20] = (16).to_bytes(4, 'little')  # Chunk size: 16
    header[20:22] = (1).to_bytes(2, 'little')    # Audio format: PCM (1)
    header[22:24] = (1).to_bytes(2, 'little')    # Channels: Mono (1)
    header[24:28] = sample_rate.to_bytes(4, 'little')  # Sample rate
    header[28:32] = (sample_rate * 2).to_bytes(4, 'little')  # Byte rate (sample_rate * channels * bits_per_sample/8)
    header[32:34] = (2).to_bytes(2, 'little')    # Block align (channels * bits_per_sample/8)
    header[34:36] = (16).to_bytes(2, 'little')   # Bits per sample (16)
    # data Chunk
    header[36:40] = b'data'
    header[40:44] = len(pcm_data).to_bytes(4, 'little')  # Data size
    
    return base64.b64encode(header + pcm_data).decode('utf-8')