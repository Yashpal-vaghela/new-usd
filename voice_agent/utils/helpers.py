import re
from voice_agent.services.appointment_service import transliterate_to_english

MULTILINGUAL_CITY_MAP = {
    # Gujarat
    "અમદાવાદ": "Ahmedabad", "ahmedabad": "Ahmedabad", "amdavad": "Ahmedabad", "अहमदाबाद": "Ahmedabad",
    "સુરત": "Surat", "surat": "Surat", "सूरत": "Surat",
    "વડોદરા": "Vadodara", "vadodara": "Vadodara", "baroda": "Vadodara", "वडोदरा": "Vadodara",
    "રાજકોટ": "Rajkot", "rajkot": "Rajkot", "राजकोट": "Rajkot",
    "જામનગર": "Jamnagar", "jamnagar": "Jamnagar", "जामनगर": "Jamnagar",
    "ભરૂચ": "Bharuch", "bharuch": "Bharuch", "भरूच": "Bharuch",
    "હળવદ": "Halvad", "halvad": "Halvad", "हलवद": "Halvad",
    "ધ્રાંગધ્રા": "Dhrangadhra", "dhrangadhra": "Dhrangadhra", "ध्रांगध्रा": "Dhrangadhra",
    # India Metro & Others
    "મુંબઈ": "Mumbai", "मुंबई": "Mumbai", "mumbai": "Mumbai", "bombay": "Mumbai", "மும்பை": "Mumbai", "ముంబై": "Mumbai", "ಮುಂಬೈ": "Mumbai", "മുംബൈ": "Mumbai", "ਮੁੰਬਈ": "Mumbai", "মুম্বাই": "Mumbai", "ମୁମ୍ବାଇ": "Mumbai",
    "પુણે": "Pune", "पुणे": "Pune", "pune": "Pune",
    "delhi": "New Delhi", "new delhi": "New Delhi", "दिल्ली": "New Delhi", "नई दिल्ली": "New Delhi", "டெல்லி": "New Delhi", "ఢిల్లీ": "New Delhi", "ದೆಹಲಿ": "New Delhi", "ഡൽഹി": "New Delhi", "ਦਿੱਲੀ": "New Delhi", "দিল্লি": "New Delhi", "ଦିଲ୍ଲୀ": "New Delhi",
    "ગુડગાંવ": "Gurugram", "ગુડગાવ": "Gurugram", "ગુડગાંવા": "Gurugram", "ગુરૂગ્રામ": "Gurugram", "ગુરુગ્રામ": "Gurugram",
    "गुड़गाँव": "Gurugram", "गुड़गांव": "Gurugram", "गुरुग्राम": "Gurugram", "gurugram": "Gurugram", "gurgaon": "Gurugram",
    "bangalore": "Bangalore", "bengaluru": "Bangalore", "बैंगलोर": "Bangalore", "बेंगलुरु": "Bangalore", "பெங்களூரு": "Bangalore", "బెంగళూరు": "Bangalore", "ಬೆಂಗಳೂರು": "Bangalore", "ബെംഗളൂരു": "Bangalore",
    "hyderabad": "Hyderabad", "हैदराबाद": "Hyderabad", "ஹைதராபாத்": "Hyderabad", "హైదరాబాద్": "Hyderabad", "ഹൈദരാബാദ്": "Hyderabad",
    "chennai": "Chennai", "चेन्नई": "Chennai", "madras": "Chennai", "சென்னை": "Chennai", "చెన్నై": "Chennai", "ചെന്നൈ": "Chennai",
    "gwalior": "Gwalior", "ग्वालियर": "Gwalior",
    "indore": "Indore", "इंदौर": "Indore",
    "sangli": "Sangli", "सांगली": "Sangli",
    "guwahati": "Guwahati", "ગુવાહાટી": "Guwahati", "गुवाहाटी": "Guwahati", "આસામ": "Guwahati", "અસમ": "Guwahati", "असम": "Guwahati", "গুয়াহাটি": "Guwahati", "ଗୁଆହାଟୀ": "Guwahati",
    "guntur": "Guntur", "गुंटूर": "Guntur", "గుంటూరు": "Guntur",
    "faridkot": "Faridkot", "fareedakot": "Faridkot", "फरीदकोट": "Faridkot", "ਫ਼ਰੀਦਕੋਟ": "Faridkot", "ਫਰੀਦਕੋਟ": "Faridkot",
    "sri ganganagar": "Sri Ganganagar", "ganganagar": "Sri Ganganagar", "श्रीगंगानगर": "Sri Ganganagar", "गंगानगर": "Sri Ganganagar",
    "malda": "Malda", "मालदा": "Malda", "মালদা": "Malda"
}

ALL_CERTIFIED_DOCTORS_LIST = [
    "Dr. Rakesh Patel", "Dr. Jigar P. Thakkar", "Dr. Ankit Mataliya", "Dr. Neerav Jhaveri", "Dr. Alap D Shah", "Dr. Abbas Noorani", "Dr. Purvesh Chauhan", "Dr. Ravi Shah", "Dr. Janu Shah",
    "Dr. Bharat R. Patel", "Dr. Parita Shah", "Dr. Viren K Savani", "Dr. Purvi Patel", "Dr. Priyanka Kathiriya", "Dr. Jay Patel",
    "Dr. Vinita Tekchandani", "Dr. Deepika Dalal", "Dr. Nikita Motwani", "Dr. Rohan Bandi", "Dr. Moez Khakiani",
    "Dr. Aarti Bhatewara", "Dr. Kaveena Parikh", "Dr. Khushbu Patel",
    "Dr. Margie I Aghera", "Dr. Pagisha Sojitra", "Dr. Vishvaraj Agravat", "Dr. Hetal Buch",
    "Dr. D. J. Chetariya", "Dr. Prasanna Patel", "Dr. Bharat Katarmal",
    "Dr. Hafsha Saiyed", "Dr. Pankaj Patel", "Dr. Dilip J Parejiya",
    "Dr. Sanjit Singh", "Dr. Minu Arora", "Dr. Amit Kr. Agrawal",
    "Dr. Surangana Gupta", "Dr. Jaydev Roy", "Dr. Himanshu Sharma",
    "Dr. Aman Singhal", "Dr. Mohammed Issak", "Dr. Srilakshmi CH", "Dr. M Jaydev",
    "Dr. Reuben Joseph", "Dr. Praneeth Kumar", "Dr. Kalyani Jagdale", "Dr. Digvijay Deshpande",
    "Dr. Adil Lyngdoh", "Dr. Asmita Sodhi", "Dr. Neetu Jindal", "Dr. A K Saha"
]

DOCTOR_HOME_CITIES = {
    "Dr. Rakesh Patel": "Ahmedabad", "Dr. Jigar P. Thakkar": "Ahmedabad", "Dr. Ankit Mataliya": "Ahmedabad",
    "Dr. Neerav Jhaveri": "Ahmedabad", "Dr. Alap D Shah": "Ahmedabad", "Dr. Abbas Noorani": "Ahmedabad",
    "Dr. Purvesh Chauhan": "Ahmedabad", "Dr. Ravi Shah": "Ahmedabad", "Dr. Janu Shah": "Ahmedabad",
    "Dr. Bharat R. Patel": "Surat", "Dr. Parita Shah": "Surat", "Dr. Viren K Savani": "Surat",
    "Dr. Purvi Patel": "Surat", "Dr. Priyanka Kathiriya": "Surat", "Dr. Jay Patel": "Surat",
    "Dr. Vinita Tekchandani": "Mumbai", "Dr. Deepika Dalal": "Mumbai", "Dr. Nikita Motwani": "Mumbai",
    "Dr. Rohan Bandi": "Mumbai", "Dr. Moez Khakiani": "Mumbai",
    "Dr. Aarti Bhatewara": "Pune", "Dr. Kaveena Parikh": "Vadodara", "Dr. Khushbu Patel": "Vadodara",
    "Dr. Margie I Aghera": "Rajkot", "Dr. Pagisha Sojitra": "Rajkot", "Dr. Vishvaraj Agravat": "Rajkot", "Dr. Hetal Buch": "Rajkot",
    "Dr. D. J. Chetariya": "Jamnagar", "Dr. Prasanna Patel": "Jamnagar", "Dr. Bharat Katarmal": "Jamnagar",
    "Dr. Hafsha Saiyed": "Bharuch", "Dr. Pankaj Patel": "Halvad", "Dr. Dilip J Parejiya": "Dhrangadhra",
    "Dr. Sanjit Singh": "New Delhi", "Dr. Minu Arora": "New Delhi", "Dr. Amit Kr. Agrawal": "Gurugram",
    "Dr. Surangana Gupta": "Indore", "Dr. Jaydev Roy": "Indore", "Dr. Himanshu Sharma": "Indore",
    "Dr. Aman Singhal": "Gwalior", "Dr. Mohammed Issak": "Bangalore", "Dr. Srilakshmi CH": "Hyderabad", "Dr. M Jaydev": "Hyderabad",
    "Dr. Reuben Joseph": "Chennai", "Dr. Praneeth Kumar": "Guntur", "Dr. Kalyani Jagdale": "Sangli",
    "Dr. Digvijay Deshpande": "Sangli", "Dr. Adil Lyngdoh": "Guwahati", "Dr. Asmita Sodhi": "Faridkot",
    "Dr. Neetu Jindal": "Sri Ganganagar", "Dr. A K Saha": "Malda"
}

def clean_hallucinations(text):
    if not text:
        return ""
    text_str = str(text).strip()
    text_str = re.sub(r"\d{1,2}:\d{2}(:\d{2})?(\.\d+)?\s*-->\s*\d{1,2}:\d{2}(:\d{2})?", "", text_str)
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
    text = re.sub(r"\d{1,2}:\d{2}(:\d{2})?(\.\d+)?\s*-->\s*\d{1,2}:\d{2}(:\d{2})?", "", text)
    text = re.sub(r"\b\d{1,2}:\d{2}(:\d{2})?\b", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

import unicodedata

def strip_diacritics(s):
    if not s:
        return ""
    return "".join(c for c in unicodedata.normalize("NFKD", str(s)) if unicodedata.category(c) != "Mn")

def _norm_phon(s):
    s = strip_diacritics(str(s or "")).lower()
    s = s.replace("w", "v").replace("oo", "u").replace("ee", "i").replace("aa", "a").replace(".", "")
    return re.sub(r"[^a-z0-9]", "", s)

def extract_slots_from_review_summary(text: str) -> dict:
    """Universal Language-Agnostic Review Summary Slot Extractor.
    Parses any structured review summary in any script (Gujarati, Hindi, Punjabi, Tamil, Telugu, English, etc.)
    or Romanized transliteration (Nām, Phōna, Shahar, Samasyā, Ḍākatar)."""
    if not text:
        return {}
    extracted = {}

    # Step 1: Normalize line breaks & extract bullet / key-value items
    # Normalize Gujarati visarga U+0A83, devanagari visarga, and full-width colon to standard colon
    norm_text = re.sub(r"[\u0A83\u0903:：]", ":", text)
    # Split on any known review key onto a fresh line
    key_patterns = r"(?:નામ|नाम|नाव|নাম|பெயர்|పేరు|ಹೆಸರು|പേര്|ਨਾਮ|name|full name|ફોન|फ़ोन|फोन|फोन नंबर|phone|mobile|શહેર|शहर|நகரம்|city|location|સમસ્યા|સમસ્યાં|समस्या|பிரச்சனை|concern|issue|problem|ડૉક્ટર|ડોક્ટર|डॉक्टर|மருத்துவர்|doctor|dentist)\s*:"
    norm_text = re.sub(rf"[,;।.\n\r\t\s]+(?:[-•*]\s*)?({key_patterns})", r"\n- \1", norm_text, flags=re.IGNORECASE)
    norm_text = re.sub(r"[\s•*]+[-•*]\s*", "\n- ", norm_text)
    lines = [l.strip() for l in norm_text.split("\n") if l.strip()]

    # Collect parsed key-value pairs
    kv_pairs = []
    for l in lines:
        m = re.search(r"^[-•*\d.\s]*([^\s:\-][^:\-]{0,25})\s*[:\-]\s*(.+)$", l)
        if m:
            raw_k = m.group(1).strip()
            raw_v = m.group(2).strip()
            # Clean trailing call-to-actions from value (e.g. 'Please type submit...')
            raw_v = re.split(r"(?i)\s*(?:Please|Kripa|Krupa|Kripā|Krupā|કૃપા|कृपया|దయచేసి|దయವಿಟ್ಟು|தயவுசெய்து|Submit|સબમિટ|सबमिट|yā\s+radd|યા\s+રદ)\s+", raw_v)[0].strip()
            raw_v = re.sub(r"[*_`]", "", raw_v).strip()
            raw_v = re.sub(r"[,;।.]+$", "", raw_v).strip()
            if raw_v:
                kv_pairs.append((raw_k, raw_v))

    # Step 2: Categorize each key-value pair
    for raw_k, raw_v in kv_pairs:
        k_clean = strip_diacritics(raw_k).lower()
        if any(ord(c) > 127 for c in raw_k):
            k_trans = strip_diacritics(transliterate_to_english(raw_k)).lower()
        else:
            k_trans = k_clean

        # A. PHONE (Digits or Phone key)
        if re.search(r"\b[0-9]{10}\b", raw_v) or any(w in k_clean or w in k_trans for w in ["phone", "phon", "phona", "fone", "fon", "mobile", "mobail", "duravani", "tolaipesi", "sampark"]):
            digits = "".join(filter(str.isdigit, raw_v))
            if len(digits) >= 10:
                extracted["phone"] = digits[-10:]
                continue

        # B. DOCTOR (Doctor key or Doctor name match)
        if any(w in raw_k.lower() or w in k_clean or w in k_trans for w in ["doctor", "doc", "doktar", "doktor", "daktar", "dakatar", "dakatara", "dakator", "ડૉ", "ડો", "डॉ", "da", "do", "vaid", "vaidya", "vaidyaru", "maruthuvar", "maruththuvar", "மருத்துவர்", "chikitsak", "వైద్యు", "డాక్టర్", "ವೈದ್ಯ", "ಡಾಕ್ಟರ್", "ഡോക്ടർ", "ਡਾਕਟਰ", "ଡାକ୍ତର", "ডাক্তার"]) or raw_v.lower().startswith("dr"):
            # Check if doctor can be found via find_doctor_in_text
            try:
                from voice_agent.ai.conversation_manager import find_doctor_in_text
                doc_found = find_doctor_in_text(raw_v, city=extracted.get("city"))
            except Exception:
                doc_found = None

            raw_v_eng = transliterate_to_english(raw_v) if any(ord(c) > 127 for c in raw_v) else raw_v
            if not doc_found and raw_v_eng:
                try:
                    from voice_agent.ai.conversation_manager import find_doctor_in_text
                    doc_found = find_doctor_in_text(raw_v_eng, city=extracted.get("city"))
                except Exception:
                    doc_found = None

            if not doc_found:
                v_norm = _norm_phon(raw_v_eng).replace("y", "i").replace("ee", "i").replace("oo", "u")
                for doc in ALL_CERTIFIED_DOCTORS_LIST:
                    doc_norm = _norm_phon(doc).replace("y", "i").replace("ee", "i").replace("oo", "u")
                    doc_parts = doc.replace("Dr.", "").strip().split()
                    if len(doc_parts) >= 2:
                        f_p = _norm_phon(doc_parts[0]).replace("y", "i").replace("ee", "i")
                        l_p = _norm_phon(doc_parts[-1]).replace("y", "i").replace("ee", "i")
                        if (f_p in v_norm and l_p in v_norm) or (len(f_p) >= 4 and f_p in v_norm) or doc_norm in v_norm or v_norm in doc_norm:
                            doc_found = doc
                            break
                    elif doc_norm in v_norm or v_norm in doc_norm:
                        doc_found = doc
                        break
            if not doc_found:
                try:
                    from voice_agent.services.appointment_service import is_matched_doctor
                    doc_found = is_matched_doctor(raw_v, city=extracted.get("city"))
                except Exception:
                    pass
            if doc_found:
                extracted["doctor_name"] = doc_found
            elif len(raw_v) >= 3 and raw_v.lower() not in ["none", "null", "-", "--"]:
                extracted["doctor_name"] = raw_v if raw_v.lower().startswith("dr") else f"Dr. {raw_v}"
            continue

        # C. CITY (City key or City match)
        if any(w in k_clean or w in k_trans for w in ["city", "shahar", "shaher", "sahar", "nagar", "nagaram", "ooru", "place", "location", "gam", "gaav", "સહર", "ਸ਼ਹਿਰ", "ಪಟ್ಟಣ", "പട്ടണം"]):
            city_found = None
            tl = raw_v.lower()
            for ck, standard_name in MULTILINGUAL_CITY_MAP.items():
                if ck in raw_v or (ck.isascii() and re.search(r"\b" + re.escape(ck) + r"\b", tl)):
                    city_found = standard_name
                    break
            if not city_found and any(ord(c) > 127 for c in raw_v):
                raw_v_eng = transliterate_to_english(raw_v).lower()
                for ck, standard_name in MULTILINGUAL_CITY_MAP.items():
                    if ck.lower() in raw_v_eng or (ck.isascii() and re.search(r"\b" + re.escape(ck.lower()) + r"\b", raw_v_eng)):
                        city_found = standard_name
                        break
            if city_found:
                extracted["city"] = city_found
            elif len(raw_v) >= 3 and raw_v.lower() not in ["none", "null", "-", "--"]:
                extracted["city"] = transliterate_to_english(raw_v).title() if any(ord(c) > 127 for c in raw_v) else raw_v.title()
            continue

        # D. NAME (Name key)
        if any(w in k_clean or w in k_trans for w in ["name", "nam", "naam", "naav", "nav", "nom", "peru", "peyar", "hesaru", "per", "patient", "user", "noma", "maru naam", "mera naam"]):
            cand_name = re.sub(r"[\s।.,!?:;\-–—/\\(){}\[\]\"'|`~]+", " ", raw_v).strip()
            cand_name = re.sub(r"\s+(?:ભાઈ|જી|bhai|ji|sahab|saheb|ji)$", "", cand_name, flags=re.IGNORECASE).strip()
            # Reject if cand_name is a known doctor
            cand_norm = _norm_phon(cand_name)
            is_doc = False
            for doc in ALL_CERTIFIED_DOCTORS_LIST:
                d_norm = _norm_phon(doc)
                if d_norm and len(cand_norm) >= 4 and (d_norm in cand_norm or cand_norm in d_norm):
                    is_doc = True
                    break
            if is_doc:
                continue
            
            # Reject conversational junk phrases
            junk_words = {"pan", "janai", "di", "tune", "main", "tumne", "kidhu", "didhu", "aapyo", "aapi", "aapya", "bata", "diya", "thi", "thiye", "submit", "cancel", "kripa", "krupa", "samasya", "problem", "doctor"}
            if any(w in cand_name.lower().split() for w in junk_words):
                continue

            if any(ord(c) > 127 for c in cand_name):
                trans_n = transliterate_to_english(cand_name)
                if trans_n:
                    cand_name = trans_n
            parts = cand_name.split()
            if parts and len(parts) <= 4:
                f_cand = parts[0].strip().capitalize()
                l_cand = " ".join(parts[1:]).strip().capitalize() if len(parts) > 1 else "-"
                if len(f_cand) >= 2 and f_cand.lower() not in ["none", "null", "user", "patient", "not", "dr"]:
                    extracted["first_name"] = f_cand
                    extracted["last_name"] = l_cand
                    extracted["user_name"] = f"{f_cand} {l_cand}".strip() if l_cand != "-" else f_cand
            continue

        # E. CONCERN / PROBLEM / ISSUE / MESSAGE
        if any(w in k_clean or w in k_trans for w in ["concern", "problem", "issue", "samasya", "samasy", "takleef", "dard", "prashna", "preshani", "dukha", "karana", "bhavin", "note", "message", "treatment", "service", "varnan"]):
            if len(raw_v) >= 2 and raw_v.lower() not in ["none", "null", "not provided", "-", "--"]:
                extracted["message"] = raw_v
                extracted["user_concern"] = raw_v
            continue

    # Step 3: Fill any remaining missing slot using direct text search fallback
    if not extracted.get("phone"):
        m_p = re.search(r"\b([0-9]{10})\b", text)
        if m_p:
            extracted["phone"] = m_p.group(1)

    if not extracted.get("doctor_name"):
        for doc in ALL_CERTIFIED_DOCTORS_LIST:
            doc_norm = _norm_phon(doc)
            if doc_norm in _norm_phon(text):
                extracted["doctor_name"] = doc
                break

    if not extracted.get("city"):
        if extracted.get("doctor_name") and extracted["doctor_name"] in DOCTOR_HOME_CITIES:
            extracted["city"] = DOCTOR_HOME_CITIES[extracted["doctor_name"]]
        else:
            tl = text.lower()
            for ck, standard_name in MULTILINGUAL_CITY_MAP.items():
                if ck in text or (ck.isascii() and re.search(r"\b" + re.escape(ck) + r"\b", tl)):
                    extracted["city"] = standard_name
                    break

    return extracted
