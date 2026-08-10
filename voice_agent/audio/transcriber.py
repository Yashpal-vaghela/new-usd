import os
import httpx
from voice_agent.audio.transcoder import wrap_pcm_to_wav_bytes
from voice_agent.utils.helpers import clean_hallucinations

async def transcribe_voice_data(pcm_bytes, sample_rate=16000, language_code='unknown'):
    sarvam_key = os.getenv("SARVAM_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    if not sarvam_key and not groq_key:
        return ""
    if not pcm_bytes or len(pcm_bytes) == 0:
        return ""
        
    try:
        wav_bytes = wrap_pcm_to_wav_bytes(pcm_bytes, sample_rate)
        
        # 1. Try Groq Whisper
        if groq_key:
            try:
                files = {'file': ('voice.wav', wav_bytes, 'audio/wav')}
                data = {'model': 'whisper-large-v3', 'response_format': 'json'}
                headers = {'Authorization': f'Bearer {groq_key}'}
                
                async with httpx.AsyncClient() as client:
                    resp = await client.post('https://api.groq.com/openai/v1/audio/transcriptions', headers=headers, files=files, data=data, timeout=10.0)
                    if resp.status_code == 200:
                        res_json = resp.json()
                        if res_json.get("text"):
                            return clean_hallucinations(res_json["text"].strip())
            except Exception as e:
                print("Groq failed, falling back to Sarvam...")
                
        # 2. Try Sarvam AI
        if sarvam_key:
            files = {'file': ('voice.wav', wav_bytes, 'audio/wav')}
            data = {'language_code': language_code}
            headers = {'api-subscription-key': sarvam_key}
            
            async with httpx.AsyncClient() as client:
                resp = await client.post('https://api.sarvam.ai/speech-to-text', headers=headers, files=files, data=data, timeout=10.0)
                if resp.status_code == 200:
                    res_json = resp.json()
                    raw_text = res_json.get("transcript", res_json.get("text", ""))
                    return clean_hallucinations(raw_text.strip())
    except Exception as e:
        print(f"Transcription failure: {e}")
        
    return ""

async def transcribe_bot_audio_with_groq(pcm_bytes, sample_rate=24000):
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key or not pcm_bytes or len(pcm_bytes) == 0:
        return ""
    try:
        wav_bytes = wrap_pcm_to_wav_bytes(pcm_bytes, sample_rate)
        files = {'file': ('bot_voice.wav', wav_bytes, 'audio/wav')}
        data = {'model': 'whisper-large-v3', 'response_format': 'json'}
        headers = {'Authorization': f'Bearer {groq_key}'}
        
        async with httpx.AsyncClient() as client:
            resp = await client.post('https://api.groq.com/openai/v1/audio/transcriptions', headers=headers, files=files, data=data, timeout=10.0)
            if resp.status_code == 200:
                res_json = resp.json()
                return clean_hallucinations(res_json.get("text", ""))
    except Exception as e:
        print(f"Groq Bot STT Error: {e}")
    return ""
