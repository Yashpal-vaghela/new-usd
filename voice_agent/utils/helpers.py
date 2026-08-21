import re

def clean_hallucinations(text):
    if not text:
        return ""
    text_str = str(text).strip()
    # Remove SRT / VTT timestamps and timestamp lines like 00:00, 00:00:00.000 --> 00:00:01.000
    text_str = re.sub(r"\d{1,2}:\d{2}(:\d{2})?(\.\d+)?\s*-->\s*\d{1,2}:\d{2}(:\d{2})?(\.\d+)?", "", text_str)
    text_str = re.sub(r"^\s*\d{1,2}:\d{2}(:\d{2})?\s*$", "", text_str)
    text_str = re.sub(r"\b\d{1,2}:\d{2}(:\d{2})?\b", "", text_str)
    lower = text_str.lower().strip()
    bad_phrases = [
        "thank you.", "thank you", "thanks.", "thanks",
        "okay.", "okay", "ok.", "ok",
        "thank you for watching.", "thank you for watching",
        "thanks for watching.", "thanks for watching",
        "00:00", "00:00:00"
    ]
    if lower in bad_phrases or not text_str.strip():
        return ""
    return text_str.strip()

def clean_assistant_text(input_text=""):
    text = str(input_text or "")
    text = re.sub(r"\[(hi|bn|ta|te|mr|gu|kn|ml|pa|or|en)-IN\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<!--[\s\S]*?-->", "", text)
    text = re.sub(r"\d{1,2}:\d{2}(:\d{2})?(\.\d+)?\s*-->\s*\d{1,2}:\d{2}(:\d{2})?(\.\d+)?", "", text)
    text = re.sub(r"\b\d{1,2}:\d{2}(:\d{2})?\b", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
