import os
from pathlib import Path
from voice_agent.retrieval.knowledge_loader import get_compiled_knowledge

_cached_prompt_templates = None

def load_prompt_templates(force_reload=False):
    global _cached_prompt_templates
    if _cached_prompt_templates is not None and not force_reload:
        return _cached_prompt_templates
        
    base_dir = Path(__file__).resolve().parent.parent
    prompts_dir = os.path.join(base_dir, 'prompts')
    
    prompt_files = ['identity.md', 'safety.md', 'conversation.md', 'language.md', 'output_format.md']
    templates = []
    
    for filename in prompt_files:
        filepath = os.path.join(prompts_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                templates.append(f.read().strip())
        except Exception as e:
            print(f"Error loading prompt file {filename}: {e}")
            
    _cached_prompt_templates = "\n\n".join(templates)
    return _cached_prompt_templates

def get_system_prompt(force_reload=False):
    prompts = load_prompt_templates(force_reload)
    knowledge = get_compiled_knowledge(force_reload)
    
    return f"""=========================================
MASTER DIRECTIVE: ULTIMATE SMILE DESIGN (USD) - GEMINI LIVE VOICE AGENT
=========================================
You are running on Native Gemini Live and generate both TEXT and AUDIO responses.
This is your highest priority instruction. Every rule below overrides any conflicting behavior unless explicitly stated otherwise.
- Only for the very first greeting of a brand new conversation without prior history: warmly say EXACTLY this phrase: "Namaste! I am Riya USD Consultant, How can we assist you today? Let's start with your beautiful name, what is your name?"
- If there is prior conversation history, or the user has already introduced themselves, or the user just reconnected: NEVER re-introduce yourself ("I am Riya..."). Answer the user's queries directly, concisely, and naturally.
Always use the Knowledge Base as the factual source.
Select only the information needed to answer the user's question.
Do not include additional details unless the user asks for them.
=========================================

{prompts}

=========================================
KNOWLEDGE BASE:
Always consult this knowledge base for specific facts, philosophy, treatments, and pricing.
=========================================
{knowledge}

=========================================
37. KNOWLEDGE APPLICATION PRINCIPLE
=========================================
The Knowledge Base contains facts.
It does not contain scripts.
Never invent treatment details.
"""
