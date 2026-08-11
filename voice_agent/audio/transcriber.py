import os
import httpx
import json
from voice_agent.audio.transcoder import wrap_pcm_to_wav_bytes, wrap_pcm_to_wav_base64
from voice_agent.utils.helpers import clean_hallucinations

async def transcribe_audio_with_gemini(pcm_bytes, sample_rate=16000):
    api_key = os.getenv("GEMINI_API_KEY_NEW")
    if not api_key or not pcm_bytes or len(pcm_bytes) == 0:
        return ""
        
    try:
        b64_wav = wrap_pcm_to_wav_base64(pcm_bytes, sample_rate)
        payload = {
            "contents": [{
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": "audio/wav",
                            "data": b64_wav
                        }
                    },
                    {
                        "text": "Transcribe the audio exactly. Do not add any extra commentary, headers, greetings, or explanations. If the audio is silent or cannot be understood, return nothing."
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 200
            }
        }
        
        models_to_try = [
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-flash-latest",
            "gemini-3.1-flash-lite",
            "gemini-2.0-flash"
        ]
        
        async with httpx.AsyncClient() as client:
            for model in models_to_try:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                    resp = await client.post(url, json=payload, timeout=15.0)
                    if resp.status_code == 200:
                        res_json = resp.json()
                        candidates = res_json.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            text_parts = [p.get("text", "") for p in parts if "text" in p]
                            text = "".join(text_parts).strip()
                            cleaned = clean_hallucinations(text)
                            if cleaned:
                                print(f"[INFO] Successfully transcribed audio using {model}: {cleaned}")
                                return cleaned
                            return text
                    else:
                        print(f"[WARN] Gemini transcription call returned status {resp.status_code} for {model}")
                except Exception as e:
                    print(f"[WARN] Gemini transcription call failed for {model}: {e}")
                    continue
    except Exception as e:
        print(f"[ERROR] Gemini transcription error: {e}")
        
    return ""

async def transcribe_voice_data(pcm_bytes, sample_rate=16000, language_code='unknown'):
    return await transcribe_audio_with_gemini(pcm_bytes, sample_rate)

async def transcribe_bot_audio_with_groq(pcm_bytes, sample_rate=24000):
    return await transcribe_audio_with_gemini(pcm_bytes, sample_rate)

