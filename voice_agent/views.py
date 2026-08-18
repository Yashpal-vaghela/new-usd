from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

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
    
    api_key = os.getenv('GEMINI_API_KEY_NEW')
    if not api_key:
        return JsonResponse({'error': 'GEMINI_API_KEY_NEW is not set'}, status=500)
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-tts-preview:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": "Leda"
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
        wav_base64 = wrap_pcm_to_wav_base64(audio_data, 24000)
        return JsonResponse({'audioBase64': wav_base64})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

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