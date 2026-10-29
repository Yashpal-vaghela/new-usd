import os
import redis
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

_redis_client = None
_redis_checked = False

def get_redis_client():
    """
    Returns a connected Redis client instance.
    Supports local Redis, Redis.com, or Upstash (rediss://... or redis://...).
    Falls back gracefully to None if Redis is unreachable or not configured.
    """
    global _redis_client, _redis_checked
    if _redis_client is not None:
        return _redis_client
        
    if _redis_checked and _redis_client is None:
        return None

    _redis_checked = True
    redis_url = os.getenv("REDIS_URL") or os.getenv("UPSTASH_REDIS_URL")
    
    if not redis_url:
        # Default local attempt
        redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_password = os.getenv("REDIS_PASSWORD", None)
        redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/0" if redis_password else f"redis://{redis_host}:{redis_port}/0"

    if redis_url and "upstash.io" in redis_url and redis_url.startswith("redis://"):
        redis_url = redis_url.replace("redis://", "rediss://", 1)

    try:
        # decode_responses=True returns strings instead of bytes
        client = redis.from_url(redis_url, decode_responses=True, socket_timeout=5, socket_connect_timeout=5)
        client.ping()
        _redis_client = client
        print(f"[INFO] [REDIS] Connected successfully to Redis at {redis_url.split('@')[-1] if '@' in redis_url else redis_url}")
        return _redis_client
    except Exception as e:
        # If standard connection failed, try SSL rediss:// if not already tried
        if redis_url and redis_url.startswith("redis://"):
            try:
                ssl_url = redis_url.replace("redis://", "rediss://", 1)
                client = redis.from_url(ssl_url, decode_responses=True, socket_timeout=5, socket_connect_timeout=5)
                client.ping()
                _redis_client = client
                print(f"[INFO] [REDIS] Connected successfully to Redis via SSL at {ssl_url.split('@')[-1] if '@' in ssl_url else ssl_url}")
                return _redis_client
            except Exception:
                pass
        print(f"[WARN] [REDIS] Could not connect to Redis ({e}). Running with local in-memory fallback.")
        _redis_client = None
        return None

def store_knowledge_in_redis():
    """
    Scans voice_agent/knowledge/ (*.yaml) and voice_agent/prompts/ (*.md),
    and stores them into Redis keys for instant sub-millisecond retrieval.
    """
    client = get_redis_client()
    if not client:
        return False, "Redis connection not available"

    base_dir = Path(__file__).resolve().parent.parent
    knowledge_dir = base_dir / 'knowledge'
    prompts_dir = base_dir / 'prompts'

    total_chars = 0
    stored_keys = []

    # 1. Store individual and compiled knowledge YAML files
    if knowledge_dir.exists():
        combined_knowledge = []
        yaml_files = sorted([f for f in os.listdir(knowledge_dir) if f.endswith('.yaml')])
        
        for yaml_file in yaml_files:
            file_path = knowledge_dir / yaml_file
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        cat_key = f"usd:knowledge:{yaml_file.replace('.yaml', '')}"
                        client.set(cat_key, content)
                        combined_knowledge.append(content)
                        stored_keys.append(cat_key)
            except Exception as e:
                print(f"[ERROR] [REDIS] Error reading {yaml_file}: {e}")

        if combined_knowledge:
            full_knowledge_text = "\n\n".join(combined_knowledge)
            client.set("usd:knowledge:compiled", full_knowledge_text)
            stored_keys.append("usd:knowledge:compiled")
            total_chars += len(full_knowledge_text)

    # 2. Store markdown prompt files
    if prompts_dir.exists():
        prompt_files = ['identity.md', 'safety.md', 'conversation.md', 'language.md', 'output_format.md']
        templates = []
        for filename in prompt_files:
            file_path = prompts_dir / filename
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        prompt_key = f"usd:prompt:{filename.replace('.md', '')}"
                        client.set(prompt_key, content)
                        templates.append(content)
                        stored_keys.append(prompt_key)
            except Exception as e:
                print(f"[ERROR] [REDIS] Error reading {filename}: {e}")

        if templates:
            full_prompts_text = "\n\n".join(templates)
            client.set("usd:prompt:templates", full_prompts_text)
            stored_keys.append("usd:prompt:templates")
            total_chars += len(full_prompts_text)

    # 3. Store knowledge_base.txt (master text knowledge base)
    kb_txt_path = base_dir / 'knowledge_base.txt'
    if kb_txt_path.exists():
        try:
            with open(kb_txt_path, 'r', encoding='utf-8') as f:
                kb_txt_content = f.read().strip()
                if kb_txt_content:
                    client.set("usd:knowledge:master_txt", kb_txt_content)
                    stored_keys.append("usd:knowledge:master_txt")
                    total_chars += len(kb_txt_content)
                    print(f"[INFO] [REDIS] Stored knowledge_base.txt into Redis key 'usd:knowledge:master_txt' ({len(kb_txt_content):,} chars)")
        except Exception as e:
            print(f"[ERROR] [REDIS] Error reading knowledge_base.txt: {e}")

    return True, f"Successfully stored {len(stored_keys)} keys into Redis (~{total_chars:,} characters)."

def get_knowledge_base_txt_from_redis():
    """
    Fetches the master knowledge_base.txt content directly from Redis.
    Returns None if Redis is unavailable or key not found.
    """
    client = get_redis_client()
    if client:
        try:
            return client.get("usd:knowledge:master_txt")
        except Exception as e:
            print(f"[WARN] [REDIS] Failed to fetch master_txt from Redis: {e}")
    return None


def get_cached_knowledge_from_redis():
    """
    Fetches the compiled knowledge base directly from Redis.
    Returns None if Redis is unavailable or key not found.
    """
    client = get_redis_client()
    if client:
        try:
            return client.get("usd:knowledge:compiled")
        except Exception as e:
            print(f"[WARN] [REDIS] Failed to fetch compiled knowledge from Redis: {e}")
    return None

def get_cached_prompts_from_redis():
    """
    Fetches the compiled prompt templates directly from Redis.
    Returns None if Redis is unavailable or key not found.
    """
    client = get_redis_client()
    if client:
        try:
            return client.get("usd:prompt:templates")
        except Exception as e:
            print(f"[WARN] [REDIS] Failed to fetch prompt templates from Redis: {e}")
    return None

def lookup_knowledge_topic_from_redis(topic_name: str):
    """
    Fetches a specific knowledge section (e.g., 'pricing', 'treatments', 'faq', 'dentists')
    directly from Redis in 1-2 milliseconds.
    """
    client = get_redis_client()
    if not client:
        return None
        
    clean_topic = topic_name.strip().lower().replace(".yaml", "")
    key = f"usd:knowledge:{clean_topic}"
    try:
        return client.get(key)
    except Exception as e:
        print(f"[WARN] [REDIS] Failed to lookup topic {topic_name}: {e}")
        return None
