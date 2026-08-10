import re

def clean_hallucinations(text):
    lower = str(text or "").lower().strip()
    bad_phrases = [
        "thank you.", "thank you", "thanks.", "thanks",
        "okay.", "okay", "ok.", "ok",
        "thank you for watching.", "thank you for watching",
        "thanks for watching.", "thanks for watching"
    ]
    if lower in bad_phrases:
        return ""
    return text

def clean_assistant_text(input_text=""):
    text = str(input_text or "")
    text = re.sub(r"\[(hi|bn|ta|te|mr|gu|kn|ml|pa|or|en)-IN\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<!--[\s\S]*?-->", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
