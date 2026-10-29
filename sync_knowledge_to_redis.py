"""
Sync Voice Agent Knowledge Base and Prompts into Redis.
Usage:
    python sync_knowledge_to_redis.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure root dir in path
sys.path.insert(0, str(Path(__file__).resolve().parent))
load_dotenv()

from voice_agent.services.redis_service import get_redis_client, store_knowledge_in_redis

def main():
    print("=" * 60)
    print("[SYNC] SYNC VOICE AGENT KNOWLEDGE & PROMPTS TO REDIS")
    print("=" * 60)


    redis_url = os.getenv("REDIS_URL") or os.getenv("UPSTASH_REDIS_URL")
    if not redis_url:
        print("[!] No REDIS_URL found in .env.")
        print("    You can add: REDIS_URL=redis://127.0.0.1:6379/0 (local)")
        print("    Or Cloud:    REDIS_URL=rediss://default:PASSWORD@ENDPOINT.upstash.io:6379")
        print("\nAttempting connection to default localhost:6379...")
    
    client = get_redis_client()
    if not client:
        print("[ERROR] Failed to connect to Redis.")
        print("Please ensure Redis is running or provide a valid REDIS_URL in .env.")
        sys.exit(1)

    success, msg = store_knowledge_in_redis()
    if success:
        print(f"[SUCCESS] {msg}")
        # Print sample keys stored
        keys = client.keys("usd:*")
        print(f"\nKeys currently stored in Redis ({len(keys)} total):")
        for k in sorted(keys):
            size = len(client.get(k) or "")
            print(f"  - {k} ({size:,} characters)")
    else:
        print(f"[ERROR] {msg}")

if __name__ == "__main__":
    main()
