import os
import httpx
from dotenv import load_dotenv
import asyncio

async def main():
    load_dotenv("d:/repo/new-usd/.env")
    api_key = os.getenv("GEMINI_API_KEY_NEW")

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    if response.status_code == 200:
        models = response.json().get("models", [])
        for m in models:
            print(f"{m.get('name')} - {m.get('displayName')}")
    else:
        print(f"Failed: {response.status_code} - {response.text}")

asyncio.run(main())
