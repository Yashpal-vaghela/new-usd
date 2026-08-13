import os
import httpx
import asyncio
from dotenv import load_dotenv
from voice_agent.utils.constants import GEMINI_TEXT_MODEL

async def main():
    load_dotenv("d:/repo/new-usd/.env")
    api_key = os.getenv("GEMINI_API_KEY_NEW")
    
    # Try gemini-2.5-flash
    model = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse&key={api_key}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": "Hello"}]}]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        print(f"[{model}] Status: {response.status_code}")
        print(response.text[:200])

    # Try gemini-3.5-flash
    model = "gemini-3.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse&key={api_key}"
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        print(f"\n[{model}] Status: {response.status_code}")
        print(response.text[:200])

asyncio.run(main())
