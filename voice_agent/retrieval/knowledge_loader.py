import os
from pathlib import Path

# Module-level cache for the compiled knowledge base
_cached_knowledge = None

def get_compiled_knowledge(force_reload=False):
    global _cached_knowledge
    if _cached_knowledge is not None and not force_reload:
        return _cached_knowledge
        
    try:
        base_dir = Path(__file__).resolve().parent.parent
        knowledge_dir = os.path.join(base_dir, 'knowledge')
        
        if not os.path.exists(knowledge_dir):
            # Fallback if the folder is missing
            return "Ultimate Smile Design is a premium dental network connecting patients with Certified Smile Designers for Veneers and Crowns."
            
        combined_parts = []
        # List all yaml files in sorted order to ensure deterministic structure
        yaml_files = sorted([f for f in os.listdir(knowledge_dir) if f.endswith('.yaml')])
        
        for yaml_file in yaml_files:
            file_path = os.path.join(knowledge_dir, yaml_file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        combined_parts.append(content)
            except Exception as e:
                print(f"Error reading knowledge file {yaml_file}: {e}")
                
        if combined_parts:
            _cached_knowledge = "\n\n".join(combined_parts)
            print(f"[INFO] Knowledge Base loaded from YAML files! Length: {len(_cached_knowledge)} chars.")
        else:
            _cached_knowledge = "Ultimate Smile Design is a premium dental network connecting patients with Certified Smile Designers for Veneers and Crowns."
            
    except Exception as e:
        print(f"[ERROR] Failed to load Knowledge Base: {e}")
        _cached_knowledge = "Ultimate Smile Design is a premium dental network connecting patients with Certified Smile Designers for Veneers and Crowns."
        
    return _cached_knowledge
