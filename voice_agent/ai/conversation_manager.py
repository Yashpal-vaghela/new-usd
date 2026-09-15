def log_live_conversation(mode, user_text, bot_text, slots):
    import sys
    fn = slots.get('first_name') or '-'
    ln = slots.get('last_name') or '-'
    name_str = f"{fn} {ln}".strip() if ln != '-' else fn
    city_str = slots.get('city') or '-'
    doc_str = slots.get('doctor_name') or '-'
    msg_str = slots.get('message') or '-'
    phone_str = slots.get('phone') or '-'
    sub_str = "YES (Submitted to CRM)" if slots.get('is_submitted') else "No"

    sep = "=" * 70
    log_msg = (
        f"\n{sep}\n"
        f"⚡ [{mode.upper()}]\n"
        f"👤 USER : {user_text}\n"
        f"🤖 RIYA : {bot_text}\n"
        f"📋 SLOTS: Name: {name_str} | City: {city_str} | Doctor: {doc_str} | Concern: {msg_str} | Phone: {phone_str} | Submitted: {sub_str}\n"
        f"{sep}\n"
    )
    try:
        print(log_msg, flush=True)
    except Exception:
        try:
            sys.stdout.buffer.write(log_msg.encode('utf-8', errors='replace') + b'\n')
            sys.stdout.buffer.flush()
        except Exception:
            pass    

import os
import re
import json
import base64
import asyncio
import httpx
from voice_agent.utils.constants import INACTIVITY_TIMEOUT
from voice_agent.utils.helpers import clean_assistant_text, clean_hallucinations, extract_slots_from_review_summary, is_submit_review_summary, transliterate_to_english, strip_diacritics, ALL_CERTIFIED_DOCTORS_LIST
from voice_agent.navigation.commands import detect_best_tag, detect_best_tag_with_fallback
from voice_agent.audio.transcriber import transcribe_voice_data
from voice_agent.services.appointment_service import submit_consultation_appointment
from voice_agent.gemini.client import APPOINTMENT_TOOL_DECLARATION

_CHAT_HTTP_CLIENT = httpx.AsyncClient(
    timeout=12.0,
    limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)
)

_KEY_COOLDOWNS = {}

def get_prioritized_api_keys():
    import time
    now = time.time()
    candidates = []
    for var_name in ["GEMINI_API_KEY_NEW", "GEMINI_API_KEY"]:
        val = os.getenv(var_name, "").strip()
        if val and val not in candidates:
            candidates.append(val)
    available = [k for k in candidates if _KEY_COOLDOWNS.get(k, 0) < now]
    return available if available else candidates

def mark_key_rate_limited(key):
    import time
    _KEY_COOLDOWNS[key] = time.time() + 60.0

ALL_CERTIFIED_DOCTORS = [
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

CERTIFIED_CITIES = [
    "Ahmedabad", "Surat", "Mumbai", "Pune", "Vadodara", "Rajkot", "Jamnagar",
    "Bharuch", "Halvad", "Dhrangadhra", "New Delhi", "Delhi", "Gurugram", "Gurgaon",
    "Indore", "Gwalior", "Bangalore", "Bengaluru", "Hyderabad", "Chennai", "Guntur",
    "Sangli", "Guwahati", "Faridkot", "Sri Ganganagar", "Malda"
]

UNSUPPORTED_CITIES = [
    "Amreli", "Bhavnagar", "Mehsana", "Mehasana", "Gandhinagar", "Anand", "Nadiad", "Morbi", "Navsari", "Valsad", "Vapi",
    "Nashik", "Thane", "Noida", "Ghaziabad", "Faridabad", "Chandigarh", "Bhopal", "Ujjain", "Jabalpur", "Agra", "Kanpur",
    "Lucknow", "Kolhapur", "Satara", "Solapur", "Mysore", "Mangalore", "Ludhiana", "Amritsar", "Jalandhar", "Bathinda",
    "Jaipur", "Udaipur", "Kolkata", "Vijayawada", "Visakhapatnam", "Nellore", "Hubli", "Aurangabad", "Jhansi", "Mathura"
]

CITY_DOCTORS = {
    "Ahmedabad": ["Dr. Rakesh Patel", "Dr. Jigar P. Thakkar", "Dr. Ankit Mataliya", "Dr. Neerav Jhaveri", "Dr. Alap D Shah", "Dr. Abbas Noorani", "Dr. Purvesh Chauhan", "Dr. Ravi Shah", "Dr. Janu Shah"],
    "Surat": ["Dr. Bharat R. Patel", "Dr. Parita Shah", "Dr. Viren K Savani", "Dr. Purvi Patel", "Dr. Priyanka Kathiriya", "Dr. Jay Patel"],
    "Mumbai": ["Dr. Vinita Tekchandani", "Dr. Deepika Dalal", "Dr. Nikita Motwani", "Dr. Rohan Bandi", "Dr. Moez Khakiani"],
    "Pune": ["Dr. Aarti Bhatewara"],
    "Vadodara": ["Dr. Kaveena Parikh", "Dr. Khushbu Patel"],
    "Rajkot": ["Dr. Margie I Aghera", "Dr. Pagisha Sojitra", "Dr. Vishvaraj Agravat", "Dr. Hetal Buch"],
    "Jamnagar": ["Dr. D. J. Chetariya", "Dr. Prasanna Patel", "Dr. Bharat Katarmal"],
    "Bharuch": ["Dr. Hafsha Saiyed"],
    "Halvad": ["Dr. Pankaj Patel"],
    "Dhrangadhra": ["Dr. Dilip J Parejiya"],
    "New Delhi": ["Dr. Sanjit Singh", "Dr. Minu Arora"],
    "Delhi": ["Dr. Sanjit Singh", "Dr. Minu Arora"],
    "Gurugram": ["Dr. Amit Kr. Agrawal"],
    "Gurgaon": ["Dr. Amit Kr. Agrawal"],
    "Indore": ["Dr. Surangana Gupta", "Dr. Jaydev Roy", "Dr. Himanshu Sharma"],
    "Gwalior": ["Dr. Aman Singhal"],
    "Bangalore": ["Dr. Mohammed Issak"],
    "Bengaluru": ["Dr. Mohammed Issak"],
    "Hyderabad": ["Dr. Srilakshmi CH", "Dr. M Jaydev"],
    "Chennai": ["Dr. Reuben Joseph"],
    "Guntur": ["Dr. Praneeth Kumar"],
    "Sangli": ["Dr. Kalyani Jagdale", "Dr. Digvijay Deshpande"],
    "Guwahati": ["Dr. Adil Lyngdoh"],
    "Faridkot": ["Dr. Asmita Sodhi"],
    "Sri Ganganagar": ["Dr. Neetu Jindal"],
    "Malda": ["Dr. A K Saha"]
}

DOCTOR_TO_CITY = {}
for _c, _docs in CITY_DOCTORS.items():
    for _d in _docs:
        DOCTOR_TO_CITY[_d.lower()] = _c

from voice_agent.utils.helpers import MULTILINGUAL_CITY_MAP

INVALID_CITY_WORDS = {
    # Auxiliary verbs & function words
    "is", "am", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "shall", "should", "can", "could", "may", "might", "must",
    "the", "a", "an", "and", "or", "but", "if", "so", "as", "to", "for", "with", "from", "at", "by", "on", "in", "about",
    "who", "what", "where", "when", "why", "how", "which",
    "i", "you", "he", "she", "it", "we", "they", "my", "your", "his", "her", "our", "their", "me", "him", "them", "us",
    "this", "that", "these", "those",
    # Dental & consultation terms
    "yes", "no", "ok", "okay", "yeah", "yep", "sure", "submit", "cancel", "update", "edit", "change", "correct",
    "doctor", "dentist", "dr", "name", "phone", "number", "appointment", "booking", "teeth", "tooth",
    "veneer", "veneers", "crown", "crowns", "smile", "design", "consultation", "clinic", "care", "philosophy",
    "card", "warranty", "team", "guide", "specialist", "case", "cost", "price",
    # Common professions & nouns
    "lawyer", "advocate", "vakeel", "vakil", "engineer", "teacher", "patient", "user",
    "apple", "today", "tomorrow", "now", "later", "please", "thanks", "thank",
    # Gujarati transliterated
    "chhe", "che", "chu", "chhu", "chiye", "nathi", "maru", "tamaru", "mari", "tamari", "maro", "tamaro",
    "mare", "tamare", "tame", "hu", "pan", "se", "ma", "maa", "me", "mein", "thi", "na", "no", "ne",
    "kaya", "kayo", "kayi", "su", "shu", "kem", "barabar", "sachu", "khotu", "aaje", "kaale", "bhai",
    "saher", "shahar", "gaam", "nagar",
    # Hindi transliterated
    "hai", "hain", "hoon", "hun", "ho", "nahi", "nahin", "mera", "meri", "mere", "aapka", "aapki", "aapke",
    "mujhe", "kripya", "theek", "batao", "kardo", "karna", "chahiye", "sakte", "sakta", "kya", "kyu",
    "kaise", "kahan", "hoga", "hogi", "accha", "sahi", "aaj", "kal", "ka", "ki", "ke", "ko",
    # Indic script
    "ઇસ", "છે", "છુ", "છીએ", "હું", "તમે", "મારે", "તમારે", "મારું", "તમારું", "નથી", "હા", "ના", "પણ", "તો",
    "દાંત", "સ્માઇલ", "ડૉક્ટર", "ડેન્ટિસ્ટ", "લોયર", "વકીલ", "આજે", "કાલે", "શહેર", "નામ", "ફોન", "નંબર",
    "સબમિટ", "કેન્સલ", "અપડેટ",
    "है", "हैं", "हूँ", "हो", "इज", "नहीं", "हाँ", "ना", "कौन", "क्या", "कैसे", "कहाँ", "दाँत", "दांत",
    "स्माइल", "डॉक्टर", "डेंटिस्ट", "वकील", "आज", "कल", "नाम", "शहर", "फोन", "नंबर", "सबमिट", "कैंसिल", "अपडेट"
}

def extract_city_from_text(text_to_search, asking_for_city=False):
    if not text_to_search:
        return None
    import re
    tl = text_to_search.lower().strip()
    
    # 1. Exact or word-boundary match in multilingual map
    for k, standard_name in MULTILINGUAL_CITY_MAP.items():
        if k in text_to_search or (k.isascii() and re.search(r"\b" + re.escape(k) + r"\b", tl)):
            return standard_name
            
    # 2. Check CERTIFIED_CITIES list
    for city in CERTIFIED_CITIES:
        if re.search(r"\b" + re.escape(city) + r"\b", tl, re.IGNORECASE):
            return city

    # 3. Check UNSUPPORTED / Regional residence cities list
    for city in UNSUPPORTED_CITIES:
        if re.search(r"\b" + re.escape(city) + r"\b", tl, re.IGNORECASE):
            return city.capitalize()

    # 4. Location explicit phrases ("i live in X", "living in X", "staying in X", "i am from X", "mari city X", "mera shahar X")
    m_loc = re.search(r"\b(?:i live in|i stay in|i am from|living in|staying in|reside in|from)\s+([A-Za-z\u0A80-\u0AFF\u0900-\u097F]{3,30})", text_to_search, re.IGNORECASE)
    if not m_loc:
        m_loc = re.search(r"\b([A-Za-z\u0A80-\u0AFF\u0900-\u097F]{3,30})\s*(?:thi\s+chu|thi\s+chhu|ma\s+rahu\s+chu|me\s+rehta\s+hu|me\s+rehti\s+hu)\b", text_to_search, re.IGNORECASE)
    if not m_loc:
        m_loc = re.search(r"\b(?:my city is|mari city|maru saher|maru shaher|mera shahar|mera sahar)\s*[:=\-]?\s*([A-Za-z\u0A80-\u0AFF\u0900-\u097F]{3,30})", text_to_search, re.IGNORECASE)
    if m_loc:
        cand_c = m_loc.group(1).strip()
        if cand_c.lower() not in INVALID_CITY_WORDS and len(cand_c) >= 3:
            from voice_agent.services.appointment_service import transliterate_to_english
            clean_c = transliterate_to_english(cand_c).title() if any(ord(c) > 127 for c in cand_c) else cand_c.title()
            if clean_c.lower() not in INVALID_CITY_WORDS:
                return clean_c

    # 5. Bare city response if asking_for_city is active
    if asking_for_city:
        cand = text_to_search.strip()
        cand = re.sub(r"[।.,!?:;\-–—/\\(){}\[\]\"'|`~]+", " ", cand).strip()
        parts = cand.split()
        if 1 <= len(parts) <= 4:
            # Filter filler words
            non_fillers = [p for p in parts if p.lower() not in INVALID_CITY_WORDS and p.lower() not in ["order", "in", "a", "city", "place"]]
            if non_fillers:
                target_cand = " ".join(non_fillers).strip()
                if len(target_cand) >= 3:
                    from voice_agent.services.appointment_service import transliterate_to_english
                    clean_c = transliterate_to_english(target_cand).title() if any(ord(c) > 127 for c in target_cand) else target_cand.title()
                    if clean_c.lower() not in INVALID_CITY_WORDS:
                        return clean_c
            
    return None

def extract_certified_city_from_text(text_to_search):
    return extract_city_from_text(text_to_search, asking_for_city=False)

def get_city_for_doctor(doc_name):
    if not doc_name:
        return None
    import re
    clean_d = re.sub(r"^dr\.?\s*", "", doc_name, flags=re.IGNORECASE).strip().lower()
    for full_doc, city in DOCTOR_TO_CITY.items():
        doc_c = re.sub(r"^dr\.?\s*", "", full_doc, flags=re.IGNORECASE).strip().lower()
        if doc_c == clean_d or doc_c in clean_d or clean_d in doc_c:
            return city
    return None

def find_exact_full_doctor(text_to_search, city=None):
    if not text_to_search:
        return None
    import re
    tl = text_to_search.lower()
    if city and city in CITY_DOCTORS:
        doc_list = CITY_DOCTORS[city]
    else:
        doc_list = ALL_CERTIFIED_DOCTORS
    for doc in doc_list:
        doc_clean = re.sub(r"^dr\.?\s*", "", doc, flags=re.IGNORECASE).strip().lower()
        if re.search(r"\b" + re.escape(doc.lower()) + r"\b", tl) or re.search(r"\b" + re.escape(doc_clean) + r"\b", tl):
            return doc
    return None

def find_partial_doctor(text_to_search, city=None):
    if not text_to_search:
        return None
    import re
    tl = text_to_search.lower().strip()
    
    # If the text is an explicit self introduction (e.g. "my name is...", "myself..."), never match doctor
    if re.search(r"\b(?:my name is|i am|i'm|myself|call me)\b", tl):
        return None

    if city and city in CITY_DOCTORS:
        doc_list = CITY_DOCTORS[city]
    else:
        doc_list = ALL_CERTIFIED_DOCTORS

    # Case 1: Explicit prefix "dr." or "doctor" (e.g. "dr srilakshmi", "dr. ravi", "doctor mohammed")
    m_dr = re.search(r"\b(?:dr\.?|doctor)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)", tl, re.IGNORECASE)
    if m_dr:
        cand = m_dr.group(1).strip().lower()
        for doc in doc_list:
            doc_clean = re.sub(r"^dr\.?\s*", "", doc, flags=re.IGNORECASE).strip().lower()
            if cand in doc_clean or doc_clean.startswith(cand):
                return doc

    # Case 2: Match doctor by specific first name or distinctive name parts (e.g. "jaanu", "janu", "alap", "srilakshmi")
    tl_clean = re.sub(r"^(?:dr\.?|doctor)\s*", "", tl, flags=re.IGNORECASE).strip()

    common_surnames = {"shah", "patel", "sharma", "singh", "patil", "kumar", "gupta", "agarwal", "deshpande", "patel."}
    
    # 2a. Priority pass: Match distinct first names (e.g. "janu", "jaanu", "alap", "ravi", "rakesh")
    for doc in doc_list:
        doc_clean = re.sub(r"^dr\.?\s*", "", doc, flags=re.IGNORECASE).strip().lower()
        parts = [p.lower() for p in doc_clean.split() if len(p) >= 3 and p.lower() not in common_surnames]
        for p in parts:
            if re.search(r"\b" + re.escape(p) + r"\b", tl_clean):
                return doc
            # Phonetic double-vowel match (e.g. jaanu -> janu)
            p_simple = re.sub(r"([aeiou])\1+", r"\1", p)
            tl_simple = re.sub(r"([aeiou])\1+", r"\1", tl_clean)
            if re.search(r"\b" + re.escape(p_simple) + r"\b", tl_simple):
                return doc

    # 2b. Secondary pass: Match full distinctive surnames only (never common surnames like patel/shah)
    for doc in doc_list:
        doc_clean = re.sub(r"^dr\.?\s*", "", doc, flags=re.IGNORECASE).strip().lower()
        parts = [p.lower() for p in doc_clean.split() if len(p) >= 4 and p.lower() not in common_surnames]
        for p in parts:
            if re.search(r"\b" + re.escape(p) + r"\b", tl_clean):
                return doc

    return None

MULTILINGUAL_DOCTOR_MAP = {
    # Vadodara
    "ખુશ્બુ": "Dr. Khushbu Patel", "ખુશબુ": "Dr. Khushbu Patel", "ખુશ્બુ પટેલ": "Dr. Khushbu Patel", "खुशबू": "Dr. Khushbu Patel", "khushbu": "Dr. Khushbu Patel", "khushboo": "Dr. Khushbu Patel", "khushbu patel": "Dr. Khushbu Patel",
    "કવિના": "Dr. Kaveena Parikh", "કવીના": "Dr. Kaveena Parikh", "કવિના પરીખ": "Dr. Kaveena Parikh", "कवीना": "Dr. Kaveena Parikh", "kaveena": "Dr. Kaveena Parikh", "kavina": "Dr. Kaveena Parikh", "kaveena parikh": "Dr. Kaveena Parikh", "parikh": "Dr. Kaveena Parikh", "પરીખ": "Dr. Kaveena Parikh",
    # Ahmedabad
    "રાકેશ": "Dr. Rakesh Patel", "રાકેશ પટેલ": "Dr. Rakesh Patel", "राकेश": "Dr. Rakesh Patel", "राकेश पटेल": "Dr. Rakesh Patel", "rakesh": "Dr. Rakesh Patel", "rakesh patel": "Dr. Rakesh Patel",
    "જીગર": "Dr. Jigar P. Thakkar", "જીગર ઠક્કર": "Dr. Jigar P. Thakkar", "जिगर": "Dr. Jigar P. Thakkar", "जिगर ठक्कर": "Dr. Jigar P. Thakkar", "jigar": "Dr. Jigar P. Thakkar", "jigar thakkar": "Dr. Jigar P. Thakkar", "thakkar": "Dr. Jigar P. Thakkar", "ઠક્કર": "Dr. Jigar P. Thakkar", "thakkar bhai": "Dr. Jigar P. Thakkar", "ઠક્કર ભાઈ": "Dr. Jigar P. Thakkar",
    "અંકિત": "Dr. Ankit Mataliya", "અંકિત માતાલિયા": "Dr. Ankit Mataliya", "અંકિત મતાલિયા": "Dr. Ankit Mataliya", "अंकित": "Dr. Ankit Mataliya", "अंकित मतालिया": "Dr. Ankit Mataliya", "ankit": "Dr. Ankit Mataliya", "ankit mataliya": "Dr. Ankit Mataliya", "mataliya": "Dr. Ankit Mataliya", "માતલિયા": "Dr. Ankit Mataliya", "મતાલિયા": "Dr. Ankit Mataliya",
    "નીરવ": "Dr. Neerav Jhaveri", "નીરવ ઝવેરી": "Dr. Neerav Jhaveri", "નિરવ": "Dr. Neerav Jhaveri", "नीरव": "Dr. Neerav Jhaveri", "नीरव झवेरी": "Dr. Neerav Jhaveri", "neerav": "Dr. Neerav Jhaveri", "neerav jhaveri": "Dr. Neerav Jhaveri", "nirav": "Dr. Neerav Jhaveri", "jhaveri": "Dr. Neerav Jhaveri", "ઝવેરી": "Dr. Neerav Jhaveri",
    "આલાપ": "Dr. Alap D Shah", "આલાપ શાહ": "Dr. Alap D Shah", "आलाप": "Dr. Alap D Shah", "आलाप शाह": "Dr. Alap D Shah", "alap": "Dr. Alap D Shah", "alap shah": "Dr. Alap D Shah",
    "અબ્બાસ": "Dr. Abbas Noorani", "અબ્બાસ નૂરાની": "Dr. Abbas Noorani", "अब्बास": "Dr. Abbas Noorani", "अब्बास नूरानी": "Dr. Abbas Noorani", "abbas": "Dr. Abbas Noorani", "abbas noorani": "Dr. Abbas Noorani", "noorani": "Dr. Abbas Noorani", "નૂરાની": "Dr. Abbas Noorani",
    "પૂર્વેશ": "Dr. Purvesh Chauhan", "પૂર્વેશ ચૌહાણ": "Dr. Purvesh Chauhan", "પુર્વેશ": "Dr. Purvesh Chauhan", "पूर्वश": "Dr. Purvesh Chauhan", "पूर्वेश": "Dr. Purvesh Chauhan", "purvesh": "Dr. Purvesh Chauhan", "purvesh chauhan": "Dr. Purvesh Chauhan", "chauhan": "Dr. Purvesh Chauhan", "ચૌહાણ": "Dr. Purvesh Chauhan",
    "રવિ શાહ": "Dr. Ravi Shah", "રવિ": "Dr. Ravi Shah", "रवि": "Dr. Ravi Shah", "रवि शाह": "Dr. Ravi Shah", "ravi shah": "Dr. Ravi Shah", "ravi": "Dr. Ravi Shah", "raavi": "Dr. Ravi Shah",
    "જાનુ": "Dr. Janu Shah", "જાનુ શાહ": "Dr. Janu Shah", "જાનું": "Dr. Janu Shah", "જાનું શાહ": "Dr. Janu Shah", "जानू": "Dr. Janu Shah", "जानू शाह": "Dr. Janu Shah", "जानु": "Dr. Janu Shah", "जानु शाह": "Dr. Janu Shah", "janu": "Dr. Janu Shah", "janu shah": "Dr. Janu Shah", "jaanu": "Dr. Janu Shah", "jaanu shah": "Dr. Janu Shah", "jannu": "Dr. Janu Shah",
    # Surat
    "ભરત પટેલ": "Dr. Bharat R. Patel", "ભરત આર પટેલ": "Dr. Bharat R. Patel", "ભરત": "Dr. Bharat R. Patel", "भरत": "Dr. Bharat R. Patel", "भरत पटेल": "Dr. Bharat R. Patel", "भरत आर पटेल": "Dr. Bharat R. Patel", "bharat": "Dr. Bharat R. Patel", "bharat patel": "Dr. Bharat R. Patel", "bharat r patel": "Dr. Bharat R. Patel",
    "પરીતા": "Dr. Parita Shah", "પરીતા શાહ": "Dr. Parita Shah", "પરિતા": "Dr. Parita Shah", "परीता": "Dr. Parita Shah", "परीता शाह": "Dr. Parita Shah", "परिता": "Dr. Parita Shah", "परिता शाह": "Dr. Parita Shah", "parita": "Dr. Parita Shah", "parita shah": "Dr. Parita Shah",
    "વિરેન": "Dr. Viren K Savani", "વિરેન સાવાની": "Dr. Viren K Savani", "વીરેન": "Dr. Viren K Savani", "विरेन": "Dr. Viren K Savani", "विरेन सावनी": "Dr. Viren K Savani", "वीरेन": "Dr. Viren K Savani", "viren": "Dr. Viren K Savani", "viren savani": "Dr. Viren K Savani", "viren k savani": "Dr. Viren K Savani",
    "પૂર્વી": "Dr. Purvi Patel", "પૂર્વી પટેલ": "Dr. Purvi Patel", "પુર્વી": "Dr. Purvi Patel", "पूर्वी": "Dr. Purvi Patel", "पूर्वी पटेल": "Dr. Purvi Patel", "पुर्वी": "Dr. Purvi Patel", "purvi": "Dr. Purvi Patel", "purvi patel": "Dr. Purvi Patel",
    "પ્રિયંકા": "Dr. Priyanka Kathiriya", "પ્રિયંકા કથીરિયા": "Dr. Priyanka Kathiriya", "પ્રિયંકા કાઠીરીયા": "Dr. Priyanka Kathiriya", "प्रियंका": "Dr. Priyanka Kathiriya", "प्रियंका कथीरिया": "Dr. Priyanka Kathiriya", "priyanka": "Dr. Priyanka Kathiriya", "priyanka kathiriya": "Dr. Priyanka Kathiriya", "kathiriya": "Dr. Priyanka Kathiriya", "કથીરિયા": "Dr. Priyanka Kathiriya", "કાઠીરીયા": "Dr. Priyanka Kathiriya",
    "જય પટેલ": "Dr. Jay Patel", "જય": "Dr. Jay Patel", "जय": "Dr. Jay Patel", "जय पटेल": "Dr. Jay Patel", "jay": "Dr. Jay Patel", "jay patel": "Dr. Jay Patel",
    # Mumbai
    "વિનિતા": "Dr. Vinita Tekchandani", "વિનિતા ટેકચંદાની": "Dr. Vinita Tekchandani", "विनिता": "Dr. Vinita Tekchandani", "विनीता": "Dr. Vinita Tekchandani", "vinita": "Dr. Vinita Tekchandani", "vinita tekchandani": "Dr. Vinita Tekchandani", "tekchandani": "Dr. Vinita Tekchandani", "takechandani": "Dr. Vinita Tekchandani", "ટેકચંદાની": "Dr. Vinita Tekchandani",
    "દીપિકા": "Dr. Deepika Dalal", "દીપિકા દલાલ": "Dr. Deepika Dalal", "દિપિકા": "Dr. Deepika Dalal", "दीपिका": "Dr. Deepika Dalal", "deepika": "Dr. Deepika Dalal", "deepika dalal": "Dr. Deepika Dalal", "dalal": "Dr. Deepika Dalal", "દલાલ": "Dr. Deepika Dalal",
    "નિકિતા": "Dr. Nikita Motwani", "નિકિતા મોટવાની": "Dr. Nikita Motwani", "निकिता": "Dr. Nikita Motwani", "nikita": "Dr. Nikita Motwani", "nikita motwani": "Dr. Nikita Motwani", "motwani": "Dr. Nikita Motwani", "મોટવાની": "Dr. Nikita Motwani",
    "રોહન": "Dr. Rohan Bandi", "રોહન બંડી": "Dr. Rohan Bandi", "रोहन": "Dr. Rohan Bandi", "rohan": "Dr. Rohan Bandi", "rohan bandi": "Dr. Rohan Bandi", "bandi": "Dr. Rohan Bandi", "બંડી": "Dr. Rohan Bandi",
    "મોએઝ": "Dr. Moez Khakiani", "મોઈઝ": "Dr. Moez Khakiani", "मोएज़": "Dr. Moez Khakiani", "moez": "Dr. Moez Khakiani", "moez khakiani": "Dr. Moez Khakiani", "khakiani": "Dr. Moez Khakiani", "ખાકિયાની": "Dr. Moez Khakiani",
    # Pune
    "આરતી": "Dr. Aarti Bhatewara", "આરતી ભાતેવારા": "Dr. Aarti Bhatewara", "आरती": "Dr. Aarti Bhatewara", "आरती भातेवारा": "Dr. Aarti Bhatewara", "aarti": "Dr. Aarti Bhatewara", "aarti bhatewara": "Dr. Aarti Bhatewara", "bhatewara": "Dr. Aarti Bhatewara", "ભાતેવારા": "Dr. Aarti Bhatewara",
    # Rajkot
    "માર્ગી": "Dr. Margie I Aghera", "માર્ગી અઘેરા": "Dr. Margie I Aghera", "માર્ગી આઘેરા": "Dr. Margie I Aghera", "મર્ગી": "Dr. Margie I Aghera", "મર્ગી પરમાર": "Dr. Margie I Aghera", "મર ગઈ": "Dr. Margie I Aghera", "ડોક્ટર મર ગઈ": "Dr. Margie I Aghera", "ડોક્ટર મર ગઈ આઈ": "Dr. Margie I Aghera", "मार्गी": "Dr. Margie I Aghera", "margie": "Dr. Margie I Aghera", "margi": "Dr. Margie I Aghera", "dr margi": "Dr. Margie I Aghera", "dr. margi": "Dr. Margie I Aghera", "aghera": "Dr. Margie I Aghera", "અઘેરા": "Dr. Margie I Aghera", "આઘેરા": "Dr. Margie I Aghera",
    "પગીશા": "Dr. Pagisha Sojitra", "પગીશા સોજીત્રા": "Dr. Pagisha Sojitra", "पगीशा": "Dr. Pagisha Sojitra", "pagisha": "Dr. Pagisha Sojitra", "sojitra": "Dr. Pagisha Sojitra", "સોજીત્રા": "Dr. Pagisha Sojitra",
    "વિશ્વરાજ": "Dr. Vishvaraj Agravat", "વિશ્વરાજ અગ્રાવત": "Dr. Vishvaraj Agravat", "विश्वराज": "Dr. Vishvaraj Agravat", "vishvaraj": "Dr. Vishvaraj Agravat", "agravat": "Dr. Vishvaraj Agravat", "અગ્રાવત": "Dr. Vishvaraj Agravat",
    "હેતલ": "Dr. Hetal Buch", "હેતલ બૂચ": "Dr. Hetal Buch", "હેતલ બુચ": "Dr. Hetal Buch", "हेतल": "Dr. Hetal Buch", "hetal": "Dr. Hetal Buch", "hetal buch": "Dr. Hetal Buch", "buch": "Dr. Hetal Buch", "બૂચ": "Dr. Hetal Buch", "બુચ": "Dr. Hetal Buch",
    # Jamnagar
    "ચેતરિયા": "Dr. D. J. Chetariya", "ચેતરીયા": "Dr. D. J. Chetariya", "chetariya": "Dr. D. J. Chetariya", "चेतरिया": "Dr. D. J. Chetariya", "चेतरीया": "Dr. D. J. Chetariya",
    "પ્રસન્ન": "Dr. Prasanna Patel", "પ્રસન્ના": "Dr. Prasanna Patel", "prasanna": "Dr. Prasanna Patel", "प्रसन्न": "Dr. Prasanna Patel", "प्रसन्ना": "Dr. Prasanna Patel",
    "કાતરમલ": "Dr. Bharat Katarmal", "katarmal": "Dr. Bharat Katarmal", "કાતરમલ": "Dr. Bharat Katarmal", "कातरमल": "Dr. Bharat Katarmal",
    # Bharuch, Halvad, Dhrangadhra
    "હફશા": "Dr. Hafsha Saiyed", "hafsha": "Dr. Hafsha Saiyed", "hafsha saiyed": "Dr. Hafsha Saiyed", "saiyed": "Dr. Hafsha Saiyed", "સૈયદ": "Dr. Hafsha Saiyed", "हफशा": "Dr. Hafsha Saiyed", "हफ़शा": "Dr. Hafsha Saiyed",
    "પંકજ": "Dr. Pankaj Patel", "pankaj": "Dr. Pankaj Patel", "pankaj patel": "Dr. Pankaj Patel", "पंकज": "Dr. Pankaj Patel", "पंकज पटेल": "Dr. Pankaj Patel",
    "દિલીપ": "Dr. Dilip J Parejiya", "dilip": "Dr. Dilip J Parejiya", "parejiya": "Dr. Dilip J Parejiya", "પરેજીયા": "Dr. Dilip J Parejiya", "दिलीप": "Dr. Dilip J Parejiya",
    # Other Hubs (Tamil, Telugu, Kannada, Bengali, Malayalam, Punjabi, Odia, etc.)
    "રૂબેન": "Dr. Reuben Joseph", "ரூபன்": "Dr. Reuben Joseph", "ரூபன் ஜோசப்": "Dr. Reuben Joseph", "reuben": "Dr. Reuben Joseph", "reuben joseph": "Dr. Reuben Joseph",
    "પ્રણીથ": "Dr. Praneeth Kumar", "ప్రణీత్": "Dr. Praneeth Kumar", "ప్రణీత్ కుమార్": "Dr. Praneeth Kumar", "ପ୍ରଣୀତ": "Dr. Praneeth Kumar", "প্রণীত": "Dr. Praneeth Kumar", "praneeth": "Dr. Praneeth Kumar", "praneeth kumar": "Dr. Praneeth Kumar",
    "ઇસ્સાક": "Dr. Mohammed Issak", "મોહમ્મદ ઇસ્સાક": "Dr. Mohammed Issak", "ಮೊಹಮ್ಮದ್": "Dr. Mohammed Issak", "ಮೊಹಮ್ಮದ್ ಇಸ್ಸಾಕ್": "Dr. Mohammed Issak", "മൊഹമ്മദ്": "Dr. Mohammed Issak", "മൊഹമ്മദ് ഇസ്സാക്": "Dr. Mohammed Issak", "issak": "Dr. Mohammed Issak", "mohammed issak": "Dr. Mohammed Issak",
    "શ્રીલક્ષ્મી": "Dr. Srilakshmi CH", "શ્રી લક્ષ્મી": "Dr. Srilakshmi CH", "શ્રી લક્ષ્મીને": "Dr. Srilakshmi CH", "શ્રીલક્ષ્મીને": "Dr. Srilakshmi CH", "ડો. શ્રી લક્ષ્મી": "Dr. Srilakshmi CH", "ડો. શ્રીલક્ષ્મી": "Dr. Srilakshmi CH", "ડોક્ટર શ્રી લક્ષ્મી": "Dr. Srilakshmi CH", "શ્રી લક્ષ્મી સી એચ": "Dr. Srilakshmi CH",
    "श्रीलक्ष्मी": "Dr. Srilakshmi CH", "श्री लक्ष्मी": "Dr. Srilakshmi CH", "श्री लक्ष्मी जी": "Dr. Srilakshmi CH", "डॉ. श्री लक्ष्मी": "Dr. Srilakshmi CH",
    "శ్రీలక్ష్మి": "Dr. Srilakshmi CH", "శ్రీ లక్ష్మి": "Dr. Srilakshmi CH", "డాక్టర్ శ్రీలక్ష్మి": "Dr. Srilakshmi CH", "ஸ்ரீலக்ஷ்மி": "Dr. Srilakshmi CH", "ஸ்ரீ லக்ஷ்மி": "Dr. Srilakshmi CH", "டாக்டர் ஸ்ரீலக்ஷ்மி": "Dr. Srilakshmi CH",
    "srilakshmi": "Dr. Srilakshmi CH", "sri lakshmi": "Dr. Srilakshmi CH", "srilakshmi ch": "Dr. Srilakshmi CH", "sri laxmi": "Dr. Srilakshmi CH", "srilaxmi": "Dr. Srilakshmi CH", "dr srilakshmi": "Dr. Srilakshmi CH", "dr sri lakshmi": "Dr. Srilakshmi CH",
    "સંજિત": "Dr. Sanjit Singh", "sanjit": "Dr. Sanjit Singh", "sanjit singh": "Dr. Sanjit Singh",
    "મીનુ": "Dr. Minu Arora", "minu": "Dr. Minu Arora", "minu arora": "Dr. Minu Arora",
    "સુરંગના": "Dr. Surangana Gupta", "surangana": "Dr. Surangana Gupta",
    "હિમાંશુ": "Dr. Himanshu Sharma", "himanshu": "Dr. Himanshu Sharma", "himanshu sharma": "Dr. Himanshu Sharma",
    "અમન": "Dr. Aman Singhal", "અમન": "Dr. Aman Singhal", "ਅਮਨ": "Dr. Aman Singhal", "ਅਮਨ ਸਿੰਘਲ": "Dr. Aman Singhal", "ଅମନ": "Dr. Aman Singhal", "ଅମନ ସିଂଘଲ": "Dr. Aman Singhal", "അമൻ": "Dr. Aman Singhal", "അമൻ സിംഗാൾ": "Dr. Aman Singhal", "aman": "Dr. Aman Singhal", "aman singhal": "Dr. Aman Singhal",
    "કલ્યાણી": "Dr. Kalyani Jagdale", "ਕਲਿਆਣੀ": "Dr. Kalyani Jagdale", "kalyani": "Dr. Kalyani Jagdale", "jagdale": "Dr. Kalyani Jagdale",
    "દિગ્વિજય": "Dr. Digvijay Deshpande", "digvijay": "Dr. Digvijay Deshpande",
    "આદિલ": "Dr. Adil Lyngdoh", "আদিল": "Dr. Adil Lyngdoh", "লিংদোহ": "Dr. Adil Lyngdoh", "lyngdoh": "Dr. Adil Lyngdoh", "adil": "Dr. Adil Lyngdoh",
    "અસ્મિતા": "Dr. Asmita Sodhi", "ਅਸਮਿਤਾ": "Dr. Asmita Sodhi", "ਸੋਢੀ": "Dr. Asmita Sodhi", "अस्मिता": "Dr. Asmita Sodhi", "asmita": "Dr. Asmita Sodhi", "sodhi": "Dr. Asmita Sodhi", "asmita sodhi": "Dr. Asmita Sodhi", "સોઢી": "Dr. Asmita Sodhi",
    "નીતુ": "Dr. Neetu Jindal", "neetu": "Dr. Neetu Jindal", "neetu jindal": "Dr. Neetu Jindal", "jindal": "Dr. Neetu Jindal", "જિંદાલ": "Dr. Neetu Jindal",
    "સાહા": "Dr. A K Saha", "saha": "Dr. A K Saha",
    "જયદેવ": "Dr. M Jaydev", "జయదేవ్": "Dr. M Jaydev", "jaydev": "Dr. M Jaydev", "jayadev": "Dr. M Jaydev"
}

def find_doctor_in_text(text_to_search, city=None):
    if not text_to_search:
        return None
    import re
    tl = text_to_search.lower()

    # Check for Master Ceramist references - Ceramists work in lab and are NOT clinical doctors
    ceramist_terms = ["ceramist", "सिरामिस्ट", "સેરેમિસ્ટ", "haresh savani", "हरेश सवाणी", "હરેશ સવાણી", "master ceramist"]
    if any(ct in tl for ct in ceramist_terms):
        # Do not treat ceramist query as a doctor selection unless a certified doctor is explicitly named
        has_explicit_doc = any(d.lower() in tl for d in ALL_CERTIFIED_DOCTORS)
        if not has_explicit_doc:
            return None

    # 1. Check multilingual exact keywords
    for k, doc_name in MULTILINGUAL_DOCTOR_MAP.items():
        if city and CITY_DOCTORS.get(city) and doc_name not in CITY_DOCTORS[city]:
            continue
        if k.isascii():
            if re.search(r"\b" + re.escape(k) + r"\b", tl):
                return doc_name
        else:
            if k in text_to_search:
                return doc_name
    return find_exact_full_doctor(text_to_search, city) or find_partial_doctor(text_to_search, city)

def detect_uncertified_doctor(text_to_search):
    if not text_to_search:
        return None
    import re
    # Match any "Dr. Name" or "Doctor Name"
    m = re.search(r"\b(?:dr\.?|doctor)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)", text_to_search, re.IGNORECASE)
    if m:
        cand = m.group(0).strip()
        # If it matches an official USD certified doctor, it's certified (not uncertified)
        if find_doctor_in_text(cand):
            return None
        return cand
    return None

def extract_valid_phone(text_str):
    if not text_str:
        return None
    import re
    s = str(text_str)
    
    # 1. Match standard 10-digit mobile number starting with 6, 7, 8, or 9
    m = re.search(r"(?:(?:\+?91|0)[\s\-]?)?([6-9]\d{4}[\s\-]?\d{5})\b", s)
    if m:
        clean = "".join(filter(str.isdigit, m.group(1)))
        if len(clean) == 10:
            return clean

    m10 = re.search(r"\b([6-9]\d{9})\b", s)
    if m10:
        return m10.group(1)

    # 2. Check total digits in text
    digits = "".join(filter(str.isdigit, s))
    if len(digits) == 10:
        return digits
    if len(digits) == 11 and digits.startswith("0"):
        return digits[1:]
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    return None

def detect_user_language(user_text="", history=None):
    def _detect_lang_from_string(text):
        if not text:
            return None
        t_raw = str(text).strip()
        tl = t_raw.lower()
        
        # 0. Check explicit language commands in text
        if re.search(r"\b(?:english|eng|in english|english please|speak english|talk in english)\b", tl):
            return "en"
        if re.search(r"\b(?:hindi|in hindi|hindi please|hindi me|hindi mein|हिंदी)\b", tl):
            return "hi"
        if re.search(r"\b(?:gujarati|in gujarati|gujarati please|gujarati ma|ગુજરાતી)\b", tl):
            return "gu"
        if re.search(r"\b(?:marathi|in marathi|marathi please|marathi madhe|मराठी)\b", tl):
            return "mr"
        if re.search(r"\b(?:tamil|in tamil|tamil please|தமிழ்)\b", tl):
            return "ta"
        if re.search(r"\b(?:telugu|in telugu|telugu please|తెలుగు)\b", tl):
            return "te"
        if re.search(r"\b(?:bengali|bangla|in bengali|bengali please|বাংলা)\b", tl):
            return "bn"
        if re.search(r"\b(?:kannada|in kannada|kannada please|ಕನ್ನಡ)\b", tl):
            return "kn"
        if re.search(r"\b(?:malayalam|in malayalam|malayalam please|മലയാളം)\b", tl):
            return "ml"
        if re.search(r"\b(?:punjabi|in punjabi|punjabi please|ਪੰਜਾਬੀ)\b", tl):
            return "pa"
        if re.search(r"\b(?:odia|oriya|in odia|odia please|ଓଡ଼ିଆ)\b", tl):
            return "or"

        # 1. Unicode script detection
        script_counts = {
            "gu": sum(1 for c in t_raw if 0x0A80 <= ord(c) <= 0x0AFF),
            "bn": sum(1 for c in t_raw if 0x0980 <= ord(c) <= 0x09FF),
            "ta": sum(1 for c in t_raw if 0x0B80 <= ord(c) <= 0x0BFF),
            "te": sum(1 for c in t_raw if 0x0C00 <= ord(c) <= 0x0C7F),
            "kn": sum(1 for c in t_raw if 0x0C80 <= ord(c) <= 0x0CFF),
            "ml": sum(1 for c in t_raw if 0x0D00 <= ord(c) <= 0x0D7F),
            "pa": sum(1 for c in t_raw if 0x0A00 <= ord(c) <= 0x0A7F),
            "or": sum(1 for c in t_raw if 0x0B00 <= ord(c) <= 0x0B7F),
            "devanagari": sum(1 for c in t_raw if 0x0900 <= ord(c) <= 0x097F),
        }
        max_script = max(script_counts, key=script_counts.get)
        if script_counts[max_script] > 0:
            if max_script == "devanagari":
                mr_words = re.findall(r"(?:\b|[\s।.,!?:;\-_])(आहे|आहेत|नाही|नाहीत|माझे|माझा|माझी|माझ्या|तुमचे|तुमचा|तुमची|तुमच्या|आपले|आपला|आपली|आपल्या|मला|तुम्हाला|आम्हाला|त्यांना|त्याला|तिला|सांगा|सांगतो|सांगते|सांग|करावे|करायचे|करायची|करायचा|करावी|झाले|झाला|झाली|झालेत|कसे|कसा|कशी|कशा|नमस्कार|चालेल|नक्की|पाहिजे|हवे|हवी|हवा|होय|राहतो|राहते|राहतात|पुण्यात|मुंबईत|शहरात|दातांचे|दातांची|दातांना|दात|माहित|माहीत|मी|हे|या|ह्या|काय|कधी|कुठे)(?:\b|[\s।.,!?:;\-_])", tl)
                hi_words = re.findall(r"(?:\b|[\s।.,!?:;\-_])(है|हैं|हूँ|हूं|हो|था|थी|थे|गा|गी|गे|का|की|के|को|में|से|पर|ने|लिए|मेरा|मेरी|मेरे|मुझे|मुझको|हम|हमारा|हमारी|हमारे|आपका|आपकी|आपके|तुम्हारा|तुम्हारी|तुम्हारे|क्या|क्यों|कहाँ|कहां|कैसे|कैसा|कैसी|कब|कितना|कितनी|कितने|नहीं|नही|हाँ|हां|बताइए|बताओ|करना|करवाना|कराओगी|कराओगे|चाहिए|सकता|सकती|सकते|दांत|दाँत|दांतों|दाँतों|रहता|रहती|रहते|शुरू|शुरु|दीजिए|दीजिये|लीजिए|लीजिये)(?:\b|[\s।.,!?:;\-_])", tl)
                mr_score = len(mr_words) * 2
                hi_score = len(hi_words) * 2
                if mr_score > hi_score:
                    return "mr"
                return "hi"
            return max_script

        # 2. Latin-script Token-based Language Detection with Word Boundary Regex
        scores = {"en": 0, "gu": 0, "hi": 0, "mr": 0, "bn": 0, "ta": 0, "te": 0, "kn": 0, "ml": 0, "pa": 0, "or": 0}

        # Gujarati tokens
        gu_tokens = re.findall(r"\b(tamaru|tamaro|tamari|tame|maaru|maru|maro|mari|mare|maare|kem|chho|cho|chhe|che|chu|chhu|nathi|thik|theek|kari|dyo|do|karvu|karvi|karyu|naakho|nakho|thai|sake|etle|saher|shahar|bhaley|chokkas|aavse|mane|haji|su|shu|pan|saathe|sathe|kaya|kyare|mast|akdum|joie|joye|barabar|sachu|khotu|aaje|kaale|daant|dant)\b", tl)
        scores["gu"] = len(gu_tokens) * 2

        # Hindi tokens
        hi_tokens = re.findall(r"\b(mera|meri|mere|aapka|aapki|aapke|mujhe|humko|kripya|kripa|theek|bataiye|batao|kardo|karna|chahiye|sakte|sakta|sakti|kya|kyu|kyun|kaise|kahan|kaha|hoga|hogi|hoge|hai|hain|hoon|hun|accha|achha|sahi|zaroor|zarur|aaj|kal|daant|dant)\b", tl)
        scores["hi"] = len(hi_tokens) * 2

        # Marathi tokens
        mr_tokens = re.findall(r"\b(maze|tumche|mazya|tumchya|mala|aahe|aahet|nahit|nahi|sangto|sangte|sang|karaycha|karaychi|havi|hava|kasa|kashi|kashe|kay|chaaleel|chalel|nakki|pahije|dant|dantanche)\b", tl)
        scores["mr"] = len(mr_tokens) * 2

        # Bengali tokens
        bn_tokens = re.findall(r"\b(amar|apnar|naam|nam|achhe|ache|korun|korbo|bhalo|hobe|dante|kemon|ki|shob|ekhon|aajke)\b", tl)
        scores["bn"] = len(bn_tokens) * 2

        # Tamil tokens
        ta_tokens = re.findall(r"\b(ennudaiya|ungaludaiya|en|ungal|peyar|peru|pallu|pal|irukku|pannunga|pannu|solunga|solli|eppadi|enna|aamam|seri)\b", tl)
        scores["ta"] = len(ta_tokens) * 2

        # Telugu tokens
        te_tokens = re.findall(r"\b(naa|mee|peru|pallu|panti|undi|undhi|cheyandi|cheppandi|ela|enti|avunu|sare)\b", tl)
        scores["te"] = len(te_tokens) * 2

        # Kannada tokens
        kn_tokens = re.findall(r"\b(nanna|nimma|hesaru|hallu|halla|ide|madi|heli|hege|yenu|haudu|sari)\b", tl)
        scores["kn"] = len(kn_tokens) * 2

        # Malayalam tokens
        ml_tokens = re.findall(r"\b(ente|ningalude|peru|pallu|palla|undu|cheyyuka|parayu|engane|enthanu|athe|sari)\b", tl)
        scores["ml"] = len(ml_tokens) * 2

        # Punjabi tokens
        pa_tokens = re.findall(r"\b(tuhada|tuhadi|mera|meri|naa|naam|dasso|dass|sat|sri|akal|hovega|hovegi|ki|kive|haanji|theek)\b", tl)
        scores["pa"] = len(pa_tokens) * 2

        # Odia tokens
        or_tokens = re.findall(r"\b(mora|moro|apanka|nama|danta|achhi|karantu|kahantu|kipari|kana|han|thik)\b", tl)
        scores["or"] = len(or_tokens) * 2

        # English grammatical and functional tokens
        en_tokens = re.findall(r"\b(what|how|why|who|when|where|which|is|are|am|was|were|be|been|being|have|has|had|do|does|did|can|could|will|would|shall|should|may|might|must|i|you|he|she|it|we|they|my|your|his|her|our|their|me|him|them|us|this|that|these|those|the|a|an|in|on|at|to|for|from|with|about|by|into|over|after|before|between|through|under|above|below|and|or|but|if|because|as|until|while|so|not|no|yes|please|thank|thanks|hello|hi|hey|good|morning|evening|afternoon|name|doctor|dentist|appointment|consultation|smile|teeth|tooth|design|veneers|crowns|philosophy|difference|clinic|cost|price|warranty|card|team|guide|submit|cancel|update|change|correct|edit|reside|live|stay|city|phone|number|mobile)\b", tl)
        scores["en"] = len(en_tokens)

        max_lang = max(scores, key=scores.get)
        if scores[max_lang] > 0:
            return max_lang

        return None

    # Step 1: Dynamic Matching on current utterance
    last_lang = _detect_lang_from_string(user_text)
    if last_lang:
        return last_lang

    # Step 2: Fallback to USER turns ONLY in history in reverse order
    if history and isinstance(history, list):
        for turn in reversed(history):
            if turn.get("role") in ["model", "assistant"]:
                continue
            parts = turn.get("parts", [])
            p = ""
            if parts and isinstance(parts, list):
                if isinstance(parts[0], dict):
                    p = parts[0].get("text", "")
                elif isinstance(parts[0], str):
                    p = parts[0]
            elif isinstance(turn.get("text"), str):
                p = turn.get("text")
            hist_lang = _detect_lang_from_string(p)
            if hist_lang:
                return hist_lang

    return "en"

CONFIRMATION_MESSAGES_11 = {
    "gu": "તમારી અપૉઇન્ટમેન્ટ રિક્વેસ્ટ સફળતાપૂર્વક સબમિટ થઈ ગઈ છે! અમારી ટીમ ટૂંક સમયમાં તમારો સંપર્ક કરશે.",
    "hi": "आपकी अपॉइंटमेंट अनुरोध सफलतापूर्वक सबमिट हो गया है! हमारी टीम जल्द ही आपसे संपर्क करेगी।",
    "mr": "तुमची अपॉइंटमेंट विनंती यशस्वीरीत्या सबमिट झाली आहे! आमची टीम लवकरच तुमच्याशी संपर्क साधेल.",
    "bn": "আপনার অ্যাপয়েন্টমেন্ট অনুরোধ সফলভাবে জমা দেওয়া হয়েছে! আমাদের টিম শীঘ্রই আপনার সাথে যোগাযোগ করবে।",
    "ta": "உங்கள் அப்பாயின்ட்மென்ட் கோரிக்கை வெற்றிகரமாக சமர்ப்பிக்கப்பட்டது! எங்கள் குழு விரைவில் உங்களைத் தொடர்பு கொள்ளும்.",
    "te": "మీ అపాయింట్‌మెంట్ అభ్యర్థన విజయవంతంగా సమర్పించబడింది! మా బృందం త్వరలోనే మిమ్మల్ని సంప్రదిస్తుంది.",
    "kn": "ನಿಮ್ಮ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ವಿನಂತಿಯನ್ನು ಯಶಸ್ವಿಯಾಗಿ ಸಲ್ಲಿಸಲಾಗಿದೆ! ನಮ್ಮ ತಂಡವು ಶೀಘ್ರದಲ್ಲೇ ನಿಮ್ಮನ್ನು ಸಂಪರ್ಕಿಸುತ್ತದೆ.",
    "ml": "നിങ്ങളുടെ അപ്പോയിന്റ്മെന്റ് അഭ്യർത്ഥന വിജയകരമായി സമർപ്പിച്ചു! ഞങ്ങളുടെ ടീം ഉടൻ നിങ്ങളെ ബന്ധപ്പെടും.",
    "pa": "ਤੁਹਾਡੀ ਮੁਲਾਕਾਤ ਦੀ ਬੇਨਤੀ ਸਫਲਤਾਪੂਰਵਕ ਦਰਜ ਕਰ ਲਈ ਗਈ ਹੈ! ਸਾਡੀ ਟੀਮ ਜਲਦੀ ਹੀ ਤੁਹਾਡੇ ਨਾਲ ਸੰਪਰਕ ਕਰੇਗੀ।",
    "or": "ଆପଣଙ୍କ ଆପଏଣ୍ଟମେଣ୍ଟ ଅନୁରୋଧ ସଫଳତାର ସହ ଦାଖଲ ହୋଇଛି! ଆମ ଟିମ୍ ଖୁବ୍ ଶୀଘ୍ର ଆପଣଙ୍କ ସହ ଯୋଗାଯୋଗ କରିବ।",
    "en": "Your appointment request has been successfully submitted! Our team will contact you shortly to confirm your schedule."
}

def get_review_summary_prompt(lang, display_name, ph, ct, cn, dr, is_update=False):
    import random
    if lang in ["gu", "hi", "mr", "bn", "ta", "te", "kn", "ml", "pa", "or", "en"]:
        lang_key = lang
    elif lang and ("-" in lang or len(lang) > 2):
        lang_key = lang.lower()[:2]
        if lang_key not in ["gu", "hi", "mr", "bn", "ta", "te", "kn", "ml", "pa", "or", "en"]:
            lang_key = detect_user_language(lang) or "en"
    else:
        lang_key = detect_user_language(lang) if lang else "en"
    if not lang_key:
        lang_key = "en"

    # Doctor display: if not chosen, inform patient that our team will guide them
    dr_gu = dr if dr else "પસંદ કરેલ નથી (અમારી ટીમ માર્ગદર્શન આપશે)"
    dr_hi = dr if dr else "चयनित नहीं (हमारी टीम मार्गदर्शन करेगी)"
    dr_mr = dr if dr else "निवडले नाही (आमची टीम मार्गदर्शन करेल)"
    dr_bn = dr if dr else "নির্বাচিত হয়নি (আমাদের দল আপনাকে গাইড করবে)"
    dr_ta = dr if dr else "தேர்ந்தெடுக்கப்படவில்லை (எங்கள் குழு வழிகாட்டும்)"
    dr_te = dr if dr else "ఎంపిక చేయలేదు (మా బృందం మార్గదర్శనం చేస్తుంది)"
    dr_kn = dr if dr else "ಆಯ್ಕೆ ಮಾಡಲಾಗಿಲ್ಲ (ನಮ್ಮ ತಂಡ ಮಾರ್ಗದರ್ಶನ ನೀಡುತ್ತದೆ)"
    dr_ml = dr if dr else "തിരഞ്ഞെടുത്തിട്ടില്ല (ഞങ്ങളുടെ ടീം സഹായിക്കും)"
    dr_pa = dr if dr else "ਚੁਣਿਆ ਨਹੀਂ ਗਿਆ (ਸਾਡੀ ਟੀਮ ਮਾਰਗਦਰਸ਼ਨ ਕਰੇਗੀ)"
    dr_or = dr if dr else "ଚୟନ ହୋଇନାହିଁ (ଆମ ଟିମ୍ ମାର୍ଗଦର୍ଶନ କରିବ)"
    dr_en = dr if dr else "Not selected (Our team will guide you)"

    if is_update:
        gu_open = random.choice([
            "કોઈ વાંધો નહીં! મેં વિગત અપડેટ કરી દીધી છે. તમારી અપડેટ કરેલી વિગતો:",
            "ઠીક છે! વિગત અપડેટ કરી દેવામાં આવી છે. નવી વિગતો:",
            "ચોક્કસ! મેં ફેરફાર કરી દીધો છે. તમારી વિગતો:",
            "પરફેક્ટ! વિગત બદલાઈ ગઈ છે. તમારી નવી વિગતો:"
        ])
        hi_open = random.choice([
            "कोई बात नहीं! मैंने विवरण अपडेट कर दिया है। आपके अपडेट किए गए विवरण:",
            "ठीक है! विवरण अपडेट कर दिया गया है। नए विवरण:",
            "अवश्य! मैंने बदलाव कर दिया है। आपके विवरण:",
            "परफेक्ट! विवरण अपडेट हो गया है। आपके नए विवरण:"
        ])
        en_open = random.choice([
            "No problem! I have updated that detail. Here are your complete updated appointment details:",
            "Alright! That detail has been updated. Here is your updated summary:",
            "Sure! I have updated that for you. Here are your details:",
            "Perfect! That detail is updated. Here is your updated summary:"
        ])
        mr_open = random.choice([
            "काही हरकत नाही! मी तपशील अपडेट केला आहे. तुमचे अपडेट केलेले तपशील:",
            "ठीक आहे! तपशील अपडेट झाला आहे. नवे तपशील:",
            "नक्कीच! मी बदल केला आहे. तुमचे तपशील:"
        ])
        bn_open = random.choice([
            "কোন সমস্যা নেই! আমি বিবরণ আপডেট করেছি। আপনার আপডেট করা বিবরণ:",
            "ঠিক আছে! বিবরণ আপডেট করা হয়েছে। আপনার নতুন বিবরণ:",
            "অবশ্যই! আমি পরিবর্তন করে দিয়েছি। আপনার বিবরণ:"
        ])
        ta_open = random.choice([
            "பிரச்சனை இல்லை! நான் விவரத்தை புதுப்பித்துள்ளேன். உங்கள் புதுப்பிக்கப்பட்ட விவரங்கள்:",
            "சரி! விவரம் மாற்றப்பட்டது. உங்கள் புதிய விவரங்கள்:",
            "நிச்சயமாக! உங்கள் விவரங்கள் புதுப்பிக்கப்பட்டன:"
        ])
        te_open = random.choice([
            "పర్వాలేదు! నేను వివరాలను అప్‌డేట్ చేసాను. మీ అప్‌డేట్ చేసిన వివరాలు:",
            "సరే! వివరాలు అప్‌డేట్ చేయబడ్డాయి. మీ కొత్త వివరాలు:",
            "ఖచ్చితంగా! మార్పులు చేయబడ్డాయి. మీ వివరాలు:"
        ])
        kn_open = random.choice([
            "ಪರವಾಗಿಲ್ಲ! ನಾನು ವಿವರವನ್ನು ನವೀಕರಿಸಿದ್ದೇನೆ. ನಿಮ್ಮ ನವೀಕರಿಸಿದ ವಿವರಗಳು:",
            "ಸರಿ! ವಿವರವನ್ನು ನವೀಕರಿಸಲಾಗಿದೆ. ನಿಮ್ಮ ಹೊಸ ವಿವರಗಳು:",
            "ಖಂಡಿತ! ಬದಲಾವಣೆ ಮಾಡಲಾಗಿದೆ. ನಿಮ್ಮ ವಿವರಗಳು:"
        ])
        ml_open = random.choice([
            "പ്രശ്നമില്ല! ഞാൻ വിവരങ്ങൾ അപ്ഡേറ്റ് ചെയ്തിട്ടുണ്ട്. നിങ്ങളുടെ അപ്ഡേറ്റ് ചെയ്ത വിവരങ്ങൾ:",
            "ശരി! വിവരങ്ങൾ മാറ്റിയിട്ടുണ്ട്. നിങ്ങളുടെ പുതിയ വിവരങ്ങൾ:",
            "തീർച്ചയായും! വിവരങ്ങൾ അപ്ഡേറ്റ് ചെയ്തു. നിങ്ങളുടെ വിവരങ്ങൾ:"
        ])
        pa_open = random.choice([
            "ਕੋਈ ਗੱਲ ਨਹੀਂ! ਮੈਂ ਵੇਰਵੇ ਅੱਪਡੇਟ ਕਰ ਦਿੱਤੇ ਹਨ। ਤੁਹਾਡੇ ਅੱਪਡੇਟ ਕੀਤੇ ਵੇਰਵੇ:",
            "ਠੀਕ ਹੈ! ਵੇਰਵਾ ਅੱਪਡੇਟ ਹੋ ਗਿਆ ਹੈ। ਤੁਹਾਡੇ ਨਵੇਂ ਵੇਰਵੇ:",
            "ਜ਼ਰੂਰ! ਮੈਂ ਬਦਲਾਅ ਕਰ ਦਿੱਤਾ ਹੈ। ਤੁਹਾਡੇ ਵੇਰਵੇ:"
        ])
        or_open = random.choice([
            "କୌଣସି ଅସୁବିଧା ନାହିଁ! ମୁଁ ବିବରଣୀ ଅପଡେଟ୍ କରିଛି। ଆପଣଙ୍କ ଅପଡେଟ୍ ହୋଇଥିବା ବିବରଣୀ:",
            "ଠିକ୍ ଅଛି! ବିବରଣୀ ଅପଡେଟ୍ ହୋଇଛି। ଆପଣଙ୍କ ନୂତନ ବିବରଣୀ:",
            "ନିଶ୍ଚୟ! ପରିବର୍ତ୍ତନ କରାଯାଇଛି। ଆପଣଙ୍କ ବିବରଣୀ:"
        ])
        prompts = {
            "gu": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Warmly acknowledge the update in ONE short phrase, and THEN YOU ARE STRICTLY REQUIRED TO RE-RECITE THE FULL 5-FIELD REVIEW SUMMARY in Gujarati without omitting any line:\n'{gu_open}\n- નામ: {display_name}\n- ફોન: {ph}\n- શહેર: {ct}\n- સમસ્યા: {cn}\n- ડૉક્ટર: {dr_gu}\n\nકૃપા કરીને આ અપડેટ કરેલ અપૉઇન્ટમેન્ટ રિક્વેસ્ટ મોકલવા માટે 'submit' કહો અથવા રદ કરવા માટે 'cancel' કહો.'",
            "hi": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Warmly acknowledge the update in ONE short phrase, and THEN YOU ARE STRICTLY REQUIRED TO RE-RECITE THE FULL 5-FIELD REVIEW SUMMARY in Hindi without omitting any line:\n'{hi_open}\n- नाम: {display_name}\n- फ़ोन: {ph}\n- शहर: {ct}\n- समस्या: {cn}\n- डॉक्टर: {dr_hi}\n\nकृपया इस अपडेट किए गए अपॉइंटमेंट अनुरोध को भेजने के लिए 'submit' कहें या रद्द करने के लिए 'cancel' कहें।'",
            "mr": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Marathi:\n'{mr_open}\n- नाव: {display_name}\n- फोन: {ph}\n- शहर: {ct}\n- समस्या: {cn}\n- डॉक्टर: {dr_mr}\n\nकृपया ही अपॉइंटमेंट विनंती पाठवण्यासाठी 'submit' लिहा किंवा म्हणा.'",
            "bn": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Bengali:\n'{bn_open}\n- নাম: {display_name}\n- ফোন: {ph}\n- শহর: {ct}\n- સમસ્યા: {cn}\n- ডাক্তার: {dr_bn}\n\nঅনুগ্রহ করে এই অ্যাপয়েন্টমেন্ট পাঠানোর জন্য 'submit' লিখুন বা বলুন।'",
            "ta": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Tamil:\n'{ta_open}\n- பெயர்: {display_name}\n- தொலைபேசி: {ph}\n- நகரம்: {ct}\n- பிரச்சனை: {cn}\n- மருத்துவர்: {dr_ta}\n\nஇந்த அப்பாயின்ட்மென்ட் கோரிக்கையை அனுப்ப தயவுசெய்து 'submit' என எழுதவும் அல்லது சொல்லவும்.'",
            "te": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Telugu:\n'{te_open}\n- పేరు: {display_name}\n- ఫోన్: {ph}\n- నగరం: {ct}\n- సమస్య: {cn}\n- డాక్టర్: {dr_te}\n\nదయచేసి ఈ అపాయింట్‌మెంట్ అభ్యర్థనను పంపడానికి 'submit' అని రాయండి లేదా చెప్పండి.'",
            "kn": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Kannada:\n'{kn_open}\n- ಹೆಸರು: {display_name}\n- ಫೋನ್: {ph}\n- ನಗರ: {ct}\n- ಸಮಸ್ಯೆ: {cn}\n- ವೈದ್ಯರು: {dr_kn}\n\nದಯವಿಟ್ಟು ಈ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ವಿನಂತಿಯನ್ನು ಕಳುಹಿಸಲು 'submit' ಎಂದು ಬರೆಯಿರಿ ಅಥವಾ ಹೇಳಿ.'",
            "ml": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Malayalam:\n'{ml_open}\n- പേര്: {display_name}\n- ഫോൺ: {ph}\n- നഗരം: {ct}\n- പ്രശ്നം: {cn}\n- ഡോക്ടർ: {dr_ml}\n\nഈ അപ്പോയിന്റ്മെന്റ് അഭ്യർത്ഥന അയയ്ക്കാൻ ദയവായി 'submit' എന്ന് എഴുതുകയോ പറയുകയോ ചെയ്യുക.'",
            "pa": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Punjabi:\n'{pa_open}\n- ਨਾਮ: {display_name}\n- ਫ਼ੋਨ: {ph}\n- ਸ਼ਹਿਰ: {ct}\n- ਸਮੱਸਿਆ: {cn}\n- ਡਾਕਟਰ: {dr_pa}\n\nਕਿਰਪਾ ਕਰਕੇ ਇਸ ਮੁਲਾਕਾਤ ਦੀ ਬੇਨਤੀ ਭੇਜਣ ਲਈ 'submit' ਲਿਖੋ ਜਾਂ ਕਹੋ।'",
            "or": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Odia:\n'{or_open}\n- ନାମ: {display_name}\n- ଫୋନ୍: {ph}\n- ସହର: {ct}\n- ସମସ୍ୟା: {cn}\n- ଡାକ୍ତର: {dr_or}\n\nଦୟାକରି ଏହି ଆପଏଣ୍ଟମେଣ୍ଟ ଅନୁରୋଧ ପଠାଇବା ପାଇଁ 'submit' ଲେଖନ୍ତୁ କିମ୍ବା କୁହନ୍ତୁ।'"
        }
        return prompts.get(lang_key, f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Warmly acknowledge the update in ONE short phrase, and THEN YOU ARE STRICTLY REQUIRED TO RE-RECITE THE FULL 5-FIELD REVIEW SUMMARY in full without omitting any line:\n'{en_open}\n- Name: {display_name}\n- Phone: {ph}\n- City: {ct}\n- Concern: {cn}\n- Doctor: {dr_en}\n\nPlease write or say 'submit' to submit this updated appointment request.'")
    else:
        gu_open = random.choice([
            "બહુ સરસ! તમારી બધી વિગતો નોંધી લીધી છે:",
            "ઠીક છે! તમારી બધી વિગતો નોંધી લીધી છે:",
            "ચોક્કસ! આ રહી તમારી વિગતો:",
            "પરફેક્ટ! તમારી વિગતો:",
            "સરસ! તમારી વિગતો નોંધી લીધી છે:"
        ])
        hi_open = random.choice([
            "बहुत बढ़िया! आपके सभी विवरण दर्ज कर लिए गए हैं:",
            "ठीक है! आपके विवरण नोट कर लिए गए हैं:",
            "परफेक्ट! ये रहे आपके विवरण:",
            "अवश्य! आपके सभी विवरण दर्ज कर लिए गए हैं:",
            "बढ़िया! आपके विवरण नोट हो गए हैं:"
        ])
        en_open = random.choice([
            "Great! Here are your appointment details:",
            "Alright! I have noted all your details:",
            "Perfect! Let's review your details:",
            "Sure! Here is your appointment summary:",
            "Excellent! I have recorded your details:"
        ])
        mr_open = random.choice([
            "छान! तुमचे सर्व तपशील नोंदवले गेले आहेत:",
            "ठीक आहे! तुमचे सर्व तपशील नोंदवले गेले आहेत:",
            "नक्कीच! हे आहेत तुमचे तपशील:",
            "परफेक्ट! तुमचे तपशील नोंदवले गेले आहेत:"
        ])
        bn_open = random.choice([
            "বেশ! আপনার সমস্ত বিবরণ নথিভুক্ত করা হয়েছে:",
            "ঠিক আছে! আপনার সমস্ত বিবরণ লিখে নেওয়া হয়েছে:",
            "দারুণ! এই রইল আপনার বিবরণ:",
            "পারফেক্ট! আপনার সমস্ত তথ্য নথিভুক্ত করা হয়েছে:"
        ])
        ta_open = random.choice([
            "அருமை! உங்கள் அனைத்து விவரங்களும் பதிவு செய்யப்பட்டுள்ளன:",
            "சரி! உங்கள் விவரங்கள் குறிக்கப்பட்டுள்ளன:",
            "நிச்சயமாக! இதோ உங்கள் விவரங்கள்:",
            "சிறப்பு! உங்கள் அனைத்து விவரங்களும் பதிவு செய்யப்பட்டுள்ளன:"
        ])
        te_open = random.choice([
            "చాలా బాగుంది! మీ వివరాలన్నీ నమోదు చేయబడ్డాయి:",
            "సరే! మీ వివరాలు నమోదు చేయబడ్డాయి:",
            "ఖచ్చితంగా! ఇవిగో మీ వివరాలు:",
            "పర్ఫెక్ట్! మీ వివరాలన్నీ నమోదు చేయబడ్డాయి:"
        ])
        kn_open = random.choice([
            "ಉತ್ತಮ! ನಿಮ್ಮ ಎಲ್ಲಾ ವಿವರಗಳನ್ನು ದಾಖಲಿಸಲಾಗಿದೆ:",
            "ಸರಿ! ನಿಮ್ಮ ಎಲ್ಲಾ ವಿವರಗಳನ್ನು ನೋಂದಾಯಿಸಲಾಗಿದೆ:",
            "ಖಂಡಿತ! ಇವು ನಿಮ್ಮ ವಿವರಗಳು:",
            "ಪರ್ಫೆಕ್ಟ್! ನಿಮ್ಮ ವಿವರಗಳನ್ನು ದಾಖಲಿಸಲಾಗಿದೆ:"
        ])
        ml_open = random.choice([
            "വളരെ നല്ലത്! നിങ്ങളുടെ എല്ലാ വിവരങ്ങളും രേഖപ്പെടുത്തിയിട്ടുണ്ട്:",
            "ശരി! നിങ്ങളുടെ എല്ലാ വിവരങ്ങളും രേഖപ്പെടുത്തിയിട്ടുണ്ട്:",
            "തീർച്ചയായും! ഇതാ നിങ്ങളുടെ വിവരങ്ങൾ:",
            "പെർഫെക്റ്റ്! നിങ്ങളുടെ വിവരങ്ങൾ രേഖപ്പെടുത്തിയിട്ടുണ്ട്:"
        ])
        pa_open = random.choice([
            "ਬਹੁਤ ਵਧੀਆ! ਤੁਹਾਡੇ ਸਾਰੇ ਵੇਰਵੇ ਦਰਜ ਕਰ ਲਏ ਗਏ ਹਨ:",
            "ਠੀਕ ਹੈ! ਤੁਹਾਡੇ ਸਾਰੇ ਵੇਰਵੇ ਨੋਟ ਕਰ ਲਏ ਗਏ ਹਨ:",
            "ਜ਼ਰੂਰ! ਇਹ ਰਹੇ ਤੁਹਾਡੇ ਵੇਰਵੇ:",
            "ਬਿਲਕੁਲ! ਤੁਹਾਡੇ ਵੇਰਵੇ ਦਰਜ ਕਰ ਲਏ ਗਏ ਹਨ:"
        ])
        or_open = random.choice([
            "ବହୁତ ଭଲ! ଆପଣଙ୍କର ସମସ୍ତ ବିବରଣୀ ରେକର୍ଡ କରାଯାଇଛି:",
            "ଠିକ୍ ଅଛି! ଆପଣଙ୍କର ସମସ୍ତ ବିବରଣୀ ଲେଖାଯାଇଛି:",
            "ନିଶ୍ଚୟ! ଏହା ହେଉଛି ଆପଣଙ୍କର ବିବରଣୀ:",
            "ପରଫେକ୍ଟ! ଆପଣଙ୍କର ବିବରଣୀ ରେକର୍ଡ କରାଯାଇଛି:"
        ])

        prompts = {
            "gu": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Gujarati with a natural varied opening (such as '{gu_open}') and ask the user to write/say 'submit':\n'{gu_open}\n- નામ: {display_name}\n- ફોન: {ph}\n- શહેર: {ct}\n- સમસ્યા: {cn}\n- ડૉક્ટર: {dr_gu}\n\nકૃપા કરીને આ અપૉઇન્ટમેન્ટ રિક્વેસ્ટ મોકલવા માટે 'submit' લખો અથવા કહો.'",
            "hi": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Hindi with a natural varied opening (such as '{hi_open}') and ask the user to write/say 'submit':\n'{hi_open}\n- नाम: {display_name}\n- फ़ोन: {ph}\n- शहर: {ct}\n- समस्या: {cn}\n- डॉक्टर: {dr_hi}\n\nकृपया इस अपॉइंटमेंट अनुरोध को भेजने के लिए 'submit' लिखें या कहें।'",
            "mr": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Marathi with a natural varied opening (such as '{mr_open}') and ask the user to write/say 'submit':\n'{mr_open}\n- नाव: {display_name}\n- फोन: {ph}\n- शहर: {ct}\n- समस्या: {cn}\n- डॉक्टर: {dr_mr}\n\nकृपया ही अपॉइंटमेंट विनंती पाठवण्यासाठी 'submit' लिहा किंवा म्हणा.'",
            "bn": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Bengali with a natural varied opening (such as '{bn_open}') and ask the user to write/say 'submit':\n'{bn_open}\n- নাম: {display_name}\n- ফোন: {ph}\n- শহর: {ct}\n- समस्या: {cn}\n- ডাক্তার: {dr_bn}\n\nঅনুগ্রহ করে এই অ্যাপয়েন্টমেন্ট পাঠানোর জন্য 'submit' লিখুন বা বলুন।'",
            "ta": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Tamil with a natural varied opening (such as '{ta_open}') and ask the user to write/say 'submit':\n'{ta_open}\n- பெயர்: {display_name}\n- தொலைபேசி: {ph}\n- நகரம்: {ct}\n- பிரச்சனை: {cn}\n- மருத்துவர்: {dr_ta}\n\nஇந்த அப்பாயின்ட்மென்ட் கோரிக்கையை அனுப்ப தயவுசெய்து 'submit' என எழுதவும் அல்லது சொல்லவும்.'",
            "te": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Telugu with a natural varied opening (such as '{te_open}') and ask the user to write/say 'submit':\n'{te_open}\n- పేరు: {display_name}\n- ఫోన్: {ph}\n- నగరం: {ct}\n- సమస్య: {cn}\n- డాక్టర్: {dr_te}\n\nదయచేసి ఈ అపాయింట్‌మెంట్ అభ్యర్థనను పంపడానికి 'submit' అని రాయండి లేదా చెప్పండి.'",
            "kn": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Kannada with a natural varied opening (such as '{kn_open}') and ask the user to write/say 'submit':\n'{kn_open}\n- ಹೆಸರು: {display_name}\n- ಫೋನ್: {ph}\n- ನಗರ: {ct}\n- समस्या: {cn}\n- ವೈದ್ಯರು: {dr_kn}\n\nದಯವಿಟ್ಟು ಈ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ವಿನಂತಿಯನ್ನು ಕಳುಹಿಸಲು 'submit' ಎಂದು ಬರೆಯಿರಿ ಅಥವಾ ಹೇಳಿ.'",
            "ml": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Malayalam with a natural varied opening (such as '{ml_open}') and ask the user to write/say 'submit':\n'{ml_open}\n- പേര്: {display_name}\n- ഫോൺ: {ph}\n- നഗരം: {ct}\n- പ്രശ്നം: {cn}\n- ഡോക്ടർ: {dr_ml}\n\nഈ അപ്പോയിന്റ്മെന്റ് അഭ്യർത്ഥന അയയ്ക്കാൻ ദയവായി 'submit' എന്ന് എഴുതുകയോ പറയുകയോ ചെയ്യുക.'",
            "pa": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Punjabi with a natural varied opening (such as '{pa_open}') and ask the user to write/say 'submit':\n'{pa_open}\n- ਨਾਮ: {display_name}\n- ਫ਼ੋਨ: {ph}\n- ਸ਼ਹਿਰ: {ct}\n- ਸਮੱਸਿਆ: {cn}\n- ਡਾਕਟਰ: {dr_pa}\n\nਕਿਰਪਾ ਕਰਕੇ ਇਸ ਮੁਲਾਕਾਤ ਦੀ ਬੇਨਤੀ ਭੇਜਣ ਲਈ 'submit' ਲਿਖੋ ਜਾਂ ਕਹੋ।'",
            "or": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Odia with a natural varied opening (such as '{or_open}') and ask the user to write/say 'submit':\n'{or_open}\n- ନାମ: {display_name}\n- ଫୋନ୍: {ph}\n- ସହର: {ct}\n- ସମସ୍ୟା: {cn}\n- ଡାକ୍ତର: {dr_or}\n\nଦୟାକରି ଏହି ଆପଏଣ୍ଟମେଣ୍ଟ ଅନୁରୋଧ ପଠାଇବା ପାଇଁ 'submit' ଲେଖନ୍ତୁ କିମ୍ବା କୁହନ୍ତୁ।'"
        }
        return prompts.get(lang_key, f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary with a natural varied opening (such as '{en_open}') and ask the user to write/say 'submit':\n'{en_open}\n- Name: {display_name}\n- Phone: {ph}\n- City: {ct}\n- Concern: {cn}\n- Doctor: {dr_en}\n\nPlease write or say 'submit' to submit this appointment request to our clinic team.'")

def get_missing_field_message(lang, missing_type, city=None):
    messages = {
        "name": {
            "gu": "તમારી અપૉઇન્ટમેન્ટ સબમિટ કરતાં પહેલાં, કૃપા કરીને તમારું પૂરું નામ જણાવશો?",
            "hi": "आपकी अपॉइंटमेंट सबमिट करने से पहले, कृपया अपना पूरा नाम बताएं?",
            "mr": "तुमची अपॉइंटमेंट सबमिट करण्यापूर्वी, कृपया तुमचे पूर्ण नाव सांगा?",
            "bn": "আপনার অ্যাপয়েন্টমেন্ট জমা দেওয়ার আগে, দয়া করে আপনার পুরো নাম বলুন?",
            "ta": "உங்கள் அப்பாயின்ட்மென்ட்டை சமர்ப்பிக்கும் முன், தயவுசெய்து உங்கள் முழு பெயரை கூறவும்?",
            "te": "మీ అపాయింట్‌మెంట్‌ను సమర్పించే ముందు, దయచేసి మీ పూర్తి పేరును చెప్పండి?",
            "kn": "ನಿಮ್ಮ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಸಲ್ಲಿಸುವ ಮೊದಲು, ದಯವಿಟ್ಟು ನಿಮ್ಮ ಪೂರ್ಣ ಹೆಸರನ್ನು ತಿಳಿಸಿ?",
            "ml": "നിങ്ങളുടെ അപ്പോയിന്റ്മെന്റ് സമർപ്പിക്കുന്നതിന് മുമ്പ്, ദയവായി നിങ്ങളുടെ മുഴുവൻ പേര് നൽകുക?",
            "pa": "ਤੁਹਾਡੀ ਮੁਲਾਕਾਤ ਦਰਜ ਕਰਨ ਤੋਂ ਪਹਿਲਾਂ, ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ ਪੂਰਾ ਨਾਮ ਦੱਸੋ?",
            "or": "ଆପଣଙ୍କ ଆପଏଣ୍ଟମେଣ୍ଟ ଦାଖଲ କରିବା ପୂର୍ବରୁ, ଦୟାକରି ଆପଣଙ୍କର ପୂରା ନାମ ଜଣାନ୍ତୁ?",
            "en": "Before I can submit your appointment request, could you please provide your full name?"
        },
        "city": {
            "gu": "તમારી અપૉઇન્ટમેન્ટ સબમિટ કરતાં પહેલાં, તમે કયા શહેરમાં છો જેથી હું નજીકના સ્માઈલ ડિઝાઇનર શોધી શકું?",
            "hi": "आपकी अपॉइंटमेंट सबमिट करने से पहले, आप किस शहर में स्थित हैं?",
            "mr": "तुमची अपॉइंटमेंट सबमिट करण्यापूर्वी, तुम्ही कोणत्या शहरात आहात?",
            "bn": "আপনার অ্যাপয়েন্টমেন্ট জমা দেওয়ার আগে, আপনি কোন শহরে আছেন?",
            "ta": "உங்கள் அப்பாயின்ட்மென்ட்டை சமர்ப்பிக்கும் முன், நீங்கள் எந்த நகரத்தில் உள்ளீர்கள்?",
            "te": "మీ అపాయింట్‌మెంట్‌ను సమర్పించే ముందు, మీరు ఏ నగరంలో ఉన్నారు?",
            "kn": "ನಿಮ್ಮ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಸಲ್ಲಿಸುವ ಮೊದಲು, ನೀವು ಯಾವ ನಗರದಲ್ಲಿದ್ದೀರಿ?",
            "ml": "നിങ്ങളുടെ അപ്പോയിന്റ്മെന്റ് സമർപ്പിക്കുന്നതിന് മുമ്പ്, നിങ്ങൾ ഏത് നഗരത്തിലാണ് ഉള്ളത്?",
            "pa": "ਤੁਹਾਡੀ ਮੁਲਾਕਾਤ ਦਰਜ ਕਰਨ ਤੋਂ ਪਹਿਲਾਂ, ਤੁਸੀਂ ਕਿਸ ਸ਼ਹਿਰ ਵਿੱਚ ਸਥਿਤ ਹੋ?",
            "or": "ଆପଣଙ୍କ ଆପଏଣ୍ଟମେଣ୍ଟ ଦାଖଲ କରିବା ପୂର୍ବରୁ, ଆପଣ କେଉଁ ସହରରେ ଅବସ୍ଥିତ?",
            "en": "Before I can submit your appointment request, which city are you located in so I can check for our closest USD Certified Smile Designer?"
        },
        "concern": {
            "gu": "તમારી અપૉઇન્ટમેન્ટ સબમિટ કરતાં પહેલાં, તમને દાંતની કઈ સમસ્યા માટે કન્સલ્ટેશન કરવું છે?",
            "hi": "आपकी अपॉइंटमेंट सबमिट करने से पहले, आपको दाँतों की क्या समस्या है?",
            "mr": "तुमची अपॉइंटमेंट सबमिट करण्यापूर्वी, तुम्हाला दातांची कोणती समस्या आहे?",
            "bn": "আপনার অ্যাপয়েন্টমেন্ট জমা দেওয়ার আগে, দাঁতের কী সমস্যা নিয়ে পরামর্শ করতে চান?",
            "ta": "உங்கள் அப்பாயின்ட்மென்ட்டை சமர்ப்பிக்கும் முன், பற்களில் என்ன பிரச்சனை உள்ளது?",
            "te": "మీ అపాయింట్‌మెంట్‌ను సమర్పించే ముందు, మీకు దంతాల సమస్య ఏమిటి?",
            "kn": "ನಿಮ್ಮ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಸಲ್ಲಿಸುವ ಮೊದಲು, ನಿಮಗೆ ಹಲ್ಲುಗಳ ಯಾವ ಸಮಸ್ಯೆ ಇದೆ?",
            "ml": "നിങ്ങളുടെ അപ്പോയിന്റ്മെന്റ് സമർപ്പിക്കുന്നതിന് മുമ്പ്, പല്ലിന്റെ എന്തെങ്കിലും പ്രശ്നം ഉണ്ടോ?",
            "pa": "ਤੁਹਾਡੀ ਮੁਲਾਕਾਤ ਦਰਜ ਕਰਨ ਤੋਂ ਪਹਿਲਾਂ, ਦੰਦਾਂ ਦੀ ਕੀ ਸਮੱਸਿਆ ਹੈ?",
            "or": "ଆପଣଙ୍କ ଆପଏଣ୍ଟମେଣ୍ଟ ଦାଖଲ କରିବା ପୂର୍ବରୁ, ଆପଣଙ୍କ ଦାନ୍ତର କି ସମସ୍ୟା ଅଛି?",
            "en": "Before I can submit your appointment request, what dental concern or smile improvement would you like to discuss?"
        },
        "doctor": {
            "gu": f"તમારી અપૉઇન્ટમેન્ટ સબમિટ કરતાં પહેલાં, તમે {city or 'શહેર'}માં કયા USD સર્ટિફાઇડ ડૉક્ટર સાથે કન્સલ્ટ કરવા માંગો છો?",
            "hi": f"आपकी अपॉइंटमेंट सबमिट करने से पहले, आप {city or 'शहर'} में किस USD सर्टिफाइड डॉक्टर से कंसल्टेशन करना चाहते हैं?",
            "mr": f"तुमची अपॉइंटमेंट सबमिट करण्यापूर्वी, तुम्ही {city or 'शहरात'} कोणत्या USD प्रमाणित डॉक्टरांशी सल्लामसलत करू इच्छिता?",
            "bn": f"আপনার অ্যাপয়েন্টমেন্ট জমা দেওয়ার আগে, আপনি {city or 'শহরে'} কোন USD সার্টিফাইড ডাক্তারের সাথে পরামর্শ করতে চান?",
            "ta": f"உங்கள் அப்பாயின்ட்மென்ட்டை சமர்ப்பிக்கும் முன், {city or 'நகரத்தில்'} எந்த USD சான்றளிக்கப்பட்ட மருத்துவரை அணுக விரும்புகிறீர்கள்?",
            "te": f"మీ అపాయింట్‌మెంట్‌ను సమర్పించే ముందు, మీరు {city or 'నగరంలో'} ఏ USD సర్టిఫైడ్ డాక్టర్‌తో సంప్రదించాలనుకుంటున్నారు?",
            "kn": f"ನಿಮ್ಮ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಸಲ್ಲಿಸುವ ಮೊದಲು, ನೀವು {city or 'ನಗರದಲ್ಲಿ'} ಯಾವ USD ಪ್ರಮಾಣೀಕೃತ ವೈದ್ಯರನ್ನು ಸಂಪರ್ಕಿಸಲು ಬಯಸುತ್ತೀರಿ?",
            "ml": f"നിങ്ങളുടെ അപ്പോയിന്റ്മെന്റ് സമർപ്പിക്കുന്നതിന് മുമ്പ്, {city or 'നഗരത്തിൽ'} ഏത് USD സർട്ടിഫൈഡ് ഡോക്ടറുമായി കൺസൾട്ട് ചെയ്യാൻ ആഗ്രഹിക്കുന്നു?",
            "pa": f"ਤੁਹਾਡੀ ਮੁਲਾਕਾਤ ਦਰਜ ਕਰਨ ਤੋਂ ਪਹਿਲਾਂ, ਤੁਸੀਂ {city or 'ਸ਼ਹਿਰ'} ਵਿੱਚ ਕਿਸ USD ਪ੍ਰਮਾਣਿਤ ਡਾਕਟਰ ਨਾਲ ਸਲਾਹ ਕਰਨਾ ਚਾਹੁੰਦੇ ਹੋ?",
            "or": f"ଆପଣଙ୍କ ଆପଏଣ୍ଟମେଣ୍ଟ ଦାଖଲ କରିବା ପୂର୍ବରୁ, ଆପଣ {city or 'ସହରରେ'} କେଉଁ USD ସାର୍ଟିଫାଇଡ୍ ଡାକ୍ତରଙ୍କ ସହ ପରାମର୍ଶ କରିବାକୁ ଚାହାଁନ୍ତି?",
            "en": f"Before I can submit your appointment request, which USD Certified Smile Designer would you like to consult with in {city or 'your city'}?"
        },
        "phone": {
            "gu": "તમારી અપૉઇન્ટમેન્ટ સબમિટ કરતાં પહેલાં, કૃપા કરીને તમારો ૧૦ અંકનો મોબાઈલ નંબર આપશો?",
            "hi": "आपकी अपॉइंटमेंट सबमिट करने से पहले, कृपया अपना १० अंकों का मोबाइल नंबर प्रदान करें।",
            "mr": "तुमची अपॉइंटमेंट सबमिट करण्यापूर्वी, कृपया तुमचा १० अंकी मोबाईल नंबर द्या?",
            "bn": "আপনার অ্যাপয়েন্টমেন্ট জমা দেওয়ার আগে, দয়া করে আপনার ১০ অঙ্কের মোবাইল নম্বর দিন?",
            "ta": "உங்கள் அப்பாயின்ட்மென்ட்டை சமர்ப்பிக்கும் முன், தயவுசெய்து உங்கள் 10 இலக்க மொபைல் எண்ணை வழங்கவும்?",
            "te": "మీ అపాయింట్‌మెంట్‌ను సమర్పించే ముందు, దయచేసి మీ 10 అంకెల మొబైల్ నంబర్‌ను ఇవ్వండి?",
            "kn": "ನಿಮ್ಮ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಸಲ್ಲಿಸುವ ಮೊದಲು, ದಯವಿಟ್ಟು ನಿಮ್ಮ 10 ಅಂಕಿಗಳ ಮೊಬೈಲ್ ಸಂಖ್ಯೆಯನ್ನು ನೀಡಿ?",
            "ml": "നിങ്ങളുടെ അപ്പോയിന്റ്മെന്റ് സമർപ്പിക്കുന്നതിന് മുമ്പ്, ദയവായി നിങ്ങളുടെ 10 അക്ക മൊബൈൽ നമ്പർ നൽകുക?",
            "pa": "ਤੁਹਾਡੀ ਮੁਲਾਕਾਤ ਦਰਜ ਕਰਨ ਤੋਂ ਪਹਿਲਾਂ, ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ 10 ਅੰਕਾਂ ਦਾ ਮੋਬਾਈਲ ਨੰਬਰ ਪ੍ਰਦਾਨ ਕਰੋ?",
            "or": "ଆପଣଙ୍କ ଆପଏଣ୍ଟମେଣ୍ଟ ଦାଖଲ କରିବା ପୂର୍ବରୁ, ଦୟାକରି ଆପଣଙ୍କର 10 ଅଙ୍କ ବିଶିଷ୍ଟ ମୋବାଇଲ୍ ନମ୍ବର ପ୍ରଦାନ କରନ୍ତୁ?",
            "en": "Before I can submit your appointment request, could you please provide your 10-digit mobile phone number?"
        }
    }
    return messages.get(missing_type, {}).get(lang, messages.get(missing_type, {}).get("en", "Please provide the missing details."))

def get_turn_text(turn):
    if not turn or not isinstance(turn, dict):
        return ""
    if turn.get("parts") and isinstance(turn["parts"], list) and len(turn["parts"]) > 0:
        p0 = turn["parts"][0]
        if isinstance(p0, dict):
            return p0.get("text", "").strip()
        elif isinstance(p0, str):
            return p0.strip()
    if turn.get("text"):
        return str(turn["text"]).strip()
    if turn.get("content"):
        c = turn["content"]
        if isinstance(c, str):
            return c.strip()
        elif isinstance(c, list) and len(c) > 0:
            if isinstance(c[0], dict):
                return c[0].get("text", "").strip()
            elif isinstance(c[0], str):
                return c[0].strip()
    return ""

class ConversationManager:
    def __init__(self, session, send_json_callback, gemini_client):
        self.session = session
        self.send_json = send_json_callback
        self.gemini_client = gemini_client

    def _build_transcript_text(self) -> str:
        transcript_lines = []
        for turn in (self.session.latest_client_history or []):
            role = "Assistant (Riya)" if turn.get("role") == "model" else "Patient"
            parts = turn.get("parts", [])
            txt = parts[0].get("text", "") if parts else ""
            if txt and not txt.startswith("SYSTEM INSTRUCTION"):
                transcript_lines.append(f"{role}: {txt.strip()}")
        return "\n\n".join(transcript_lines)

    async def handle_audio_chunk(self, bytes_data):
        self.session.reset_activity_timer()
        self.session.current_user_pcm_chunks.append(bytes_data)

        # ⚡ OFFICIAL GEMINI LIVE DIRECT STREAMING (Automatic Server-Side Neural VAD) ⚡
        if self.session.gemini_ws:
            try:
                b64_data = base64.b64encode(bytes_data).decode('utf-8')
                audio_frame = {
                    "realtimeInput": {
                        "audio": {
                            "mimeType": "audio/pcm;rate=16000",
                            "data": b64_data
                        }
                    }
                }
                await self.session.gemini_ws.send(json.dumps(audio_frame))
            except Exception as e:
                pass

    def update_session_memory(self, user_text="", history=None, data=None):
        """Ultra-robust session memory tracking for patient name, city, doctor, concern, and phone."""
        import re
        if data:
            client_slots = data.get("slots")
            if client_slots and isinstance(client_slots, dict):
                for k, v in client_slots.items():
                    if v and str(v).lower() not in ["none", "null", "-", "--"]:
                        self.session.booking_slots[k] = v
                if client_slots.get("first_name") and not self.session.user_name:
                    fn = client_slots.get("first_name")
                    ln = client_slots.get("last_name", "")
                    self.session.user_name = f"{fn} {ln}".strip() if (ln and ln != "-") else fn
                if client_slots.get("message") and not self.session.user_concern:
                    self.session.user_concern = client_slots.get("message")

            client_name = data.get("userName")
            if client_name and isinstance(client_name, str) and client_name.strip() and not self.session.user_name:
                self.session.user_name = client_name.strip()
                parts = client_name.strip().split()
                self.session.booking_slots["first_name"] = parts[0]
                if len(parts) > 1:
                    self.session.booking_slots["last_name"] = " ".join(parts[1:])
            client_concern = data.get("userConcern")
            if client_concern and isinstance(client_concern, str) and client_concern.strip() and not self.session.user_concern:
                self.session.user_concern = client_concern.strip()
                self.session.booking_slots["message"] = client_concern.strip()
            client_city = data.get("userCity")
            if client_city and isinstance(client_city, str) and client_city.strip() and not self.session.booking_slots.get("city"):
                self.session.booking_slots["city"] = client_city.strip()
            client_doc = data.get("userDoctor")
            if client_doc and isinstance(client_doc, str) and client_doc.strip() and not self.session.booking_slots.get("doctor_name"):
                self.session.booking_slots["doctor_name"] = client_doc.strip()
            client_phone = data.get("userPhone")
            if client_phone and isinstance(client_phone, str) and client_phone.strip() and not self.session.booking_slots.get("phone"):
                self.session.booking_slots["phone"] = client_phone.strip()

        all_cities = CERTIFIED_CITIES + UNSUPPORTED_CITIES

        interjections = [
            "Hi", "Hello", "Hey", "Namaste", "Yes", "No", "Ok", "Okay", "Sure", "Thanks", "Thank", "What", "How", "Why",
            "Can", "Good", "Fine", "Teeth", "Smile", "Veneer", "Veneers", "Crown", "Crowns", "Cost", "Price", "Doctor",
            "System", "Dentist", "Consult", "Appointment", "Help", "Makeover", "Oh", "Ohh", "Ohhh", "Ah", "Ahh", "Umm",
            "Um", "Hmm", "Hmmm", "Accha", "Acha", "Haan", "Ha", "Na", "Nah", "Yep", "Nope", "Alright", "Cool", "Well",
            "Yo", "Bhai", "Bro", "Sir", "Mam", "Madam", "Dear", "Pls", "Please", "Now", "See", "Listen", "Actually",
            "Start", "Unorganise", "Unorganized", "Irregular", "Crooked", "Gap", "Yellow", "White"
        ]
        stop_words = set(interjections + [c.capitalize() for c in all_cities])

        indian_states_and_regions = [
            "punjab", "gujarat", "maharashtra", "karnataka", "tamil", "nadu", "tamilnadu", "andhra", "pradesh",
            "telangana", "kerala", "odisha", "orissa", "bengal", "rajasthan", "haryana", "delhi", "bihar", "up",
            "mp", "uttarakhand", "kashmir", "assam", "goa", "south", "north", "east", "west", "india", "bharat",
            "state", "city", "district", "village", "gam", "gaav"
        ]

        conversational_words = [
            "thi", "chu", "chhu", "chhe", "che", "se", "me", "mein", "hu", "hoon", "mai", "main", "from",
            "located", "living", "staying", "residing", "near", "closest", "here", "there", "available",
            "hello", "namaste", "hi", "hey", "yes", "no", "explain", "tell", "detail", "details", "info",
            "information", "about", "what", "is", "are", "kaise", "kya", "kem", "su", "shu", "kahu", "kaho",
            "bol", "bolo", "batao", "batana", "samjhao", "samjhavo", "janvu", "janna", "puche", "pucho",
            "please", "pls", "submit", "book", "appointment", "consultation", "doctor", "dentist", "smile",
            "design", "veneer", "veneers", "crown", "crowns", "teeth", "tooth", "know", "want", "like",
            "pan", "janai", "di", "tune", "main", "tumne", "kidhu", "didhu", "aapyo", "aapi", "aapya", "bata", "diya", "thi", "thiye",
            "kidho", "kidha", "bolya", "bolyo", "bolvu", "samjhao", "samjho", "kahe", "kahyu", "janavi", "janavo",
            "પણ", "જનાઈ", "દી", "તૂને", "મેં", "તુમને", "કીધું", "દીધું", "આપ્યો", "આપી", "આપ્યા", "બતા", "દિયા", "થી",
            "જનાઈદી", "કહ્યું", "બોલ્યા", "બોલ્યો", "સમજાવો", "સમજો", "કહે", "જણાવી", "જણાવો", "આપીદીધું",
            "batao", "batana", "bataya", "bataye", "de diya", "aapi didhu"
        ]

        invalid_name_words = set([
            "riya", "usd", "consultant", "assistant", "agent", "bot", "ai",
            "concern", "problem", "issue", "samasya", "taklif", "takleef", "teeth", "tooth", "dental",
            "appointment", "booking", "consult", "consultation", "city", "doctor", "dentist",
            "list", "aapo", "nahi", "nathi", "karvu", "karo", "submit", "cancel", "yes", "no", "ok", "okay",
            "hello", "hi", "hey", "namaste", "smile", "makeover", "veneers", "veneer", "crown", "crowns",
            "a", "an", "the", "in", "on", "at", "to", "for", "from", "with", "by", "of", "and", "or", "but", "so",
            "planning", "looking", "interested", "trying", "wondering", "suffering", "having", "scared", "worried",
            "afraid", "visiting", "going", "coming", "thinking", "asking", "seeking", "facing", "feeling", "living",
            "staying", "working", "traveling", "searching", "needing", "inquiring", "booking", "consulting", "checking",
            "here", "there", "just", "only", "also", "now", "already", "currently", "actually", "sure", "unsure",
            "ready", "happy", "excited", "trip", "dubai", "india", "patient", "user", "dentist", "doctor",
            "saathe", "sathe", "saath", "saathej", "mate", "matej", "ke saath", "na saathe",
            "સાથે", "સાથ", "સાથેજ", "માટે", "માટેજ", "કે સાથ", "साथ", "के साथ", "लिए", "के लिए",
            "dalal", "દલાલ", "दलाल", "thakkar", "ઠક્કર", "mataliya", "માતલિયા", "jhaveri", "ઝવેરી", "chauhan", "ચૌહાણ",
            "tekchandani", "ટેકચંદાની", "motwani", "મોટવાની", "bandi", "બંડી", "khakiani", "ખાકિયાની", "bhatewara", "ભાતેવારા",
            "aghera", "અઘેરા", "sojitra", "સોજીત્રા", "agravat", "અગ્રાવત", "buch", "બૂચ", "chetariya", "ચેતરિયા", "katarmal", "કાતરમલ",
            "saiyed", "સૈયદ", "parejiya", "પરેજીયા", "singhal", "સિંઘલ", "jagdale", "deshpande", "lyngdoh", "sodhi", "સોઢી", "jindal", "જિંદાલ",
            "તમે", "અમે", "તેઓ", "આપ", "તું", "મને", "તમને", "પશુ", "ખોટું", "સાચું", "નોંધ્યું", "તબિયત", "વાત", "વિશે",
            "કહો", "કહ્યું", "બોલો", "સાંભળો", "જણાવો", "મારું", "તમારું", "તેમનું", "માણસ", "દોસ્ત",
            "નથી", "નહિ", "નહીં", "નકો", "નકોસ", "નાહી", "ના", "ન", "નહોતો", "નહોતી", "નહોતું", "નહોતા", "છે", "છુ", "છું", "છીએ", "હું", "હતા", "હતી", "હતું", "હતો", "છો",
            "नहीं", "नही", "नथी", "ना", "नाही", "नको", "नकोस", "नहीँ", "नहींजी", "न", "है", "हैं", "हूँ", "हुँ", "था", "थी", "थे", "हो", "गा", "गी", "गे", "से", "तो", "भी", "ही",
            "tame", "tamne", "mane", "khotu", "sachu", "nondhyu", "tabiyat", "maru", "tamaru", "tamari", "tamaro", "tamara", "pashu", "mare",
            "tum", "hum", "aap", "mujhe", "tumhe", "galat", "sahi", "naam", "name",
            "certified", "doctor", "designer", "smile", "najik", "najikna", "clinic",
            "not", "no", "never", "none", "neither", "nor", "nathi", "nahi", "nahin", "naa", "nah", "nope",
            "barabar", "yaad", "bhul", "bhuli", "shuru", "karo", "kari", "karvu", "karvo", "karvi",
            "edit", "update", "change", "number", "mobile", "phone", "badlo", "badlu",
            "next", "week", "month", "year", "today", "tomorrow", "yesterday", "aavta", "aavti", "kal", "kale", "kaale",
            "somvar", "mangalvar", "budhvar", "guruvar", "shukravar", "shanivar", "ravivar", "javano", "javani", "java",
            "doctor", "dentist", "lawyer", "advocate", "teacher", "professor", "engineer", "developer", "receptionist",
            "salesperson", "sales", "nurse", "architect", "accountant", "pilot", "founder", "businessman", "student",
            "hindi", "gujarati", "english", "marathi", "bengali", "tamil", "telugu", "kannada", "malayalam", "punjabi", "odia", "urdu",
            "હિન્દી", "ગુજરાતી", "અંગ્રેજી", "મરાઠી", "બંગાળી", "તમિલ", "તેલુગુ", "કન્નડ", "મલયાલમ", "પંજાબી", "ઓડિયા",
            "हिन्दी", "हिंदी", "गुजराती", "अंग्रेजी", "अंग्रेज़ी", "मराठी", "बंगाली", "तमिल", "तेलुगु", "कन्नड़", "मलयालम", "पंजाबी", "ओड़िया"
        ] + [s.lower() for s in indian_states_and_regions] + [w.lower() for w in conversational_words])

        honorific_words = {
            "bhai", "ji", "sahab", "saheb", "ben", "bahen", "sir", "madam",
            "ભાઈ", "બહેન", "સાહબ", "જી", "સાહેબ"
        }

        def is_valid_name(fn, ln):
            if not fn or len(fn) < 2 or len(fn) > 35:
                return False
            fn_l = fn.lower()
            if fn_l in invalid_name_words or fn_l in honorific_words or fn.capitalize() in stop_words or fn_l.endswith("ing") or "riya" in fn_l or "usd" in fn_l or "dr" in fn_l:
                return False
            if ln and ln != "-":
                ln_parts = ln.strip().split()
                non_honorific_parts = [lp for lp in ln_parts if lp.lower() not in honorific_words]
                if not non_honorific_parts and len(ln_parts) > 0:
                    return True
                for lp in non_honorific_parts:
                    lp_l = lp.lower()
                    if lp_l in invalid_name_words or lp.capitalize() in stop_words or "riya" in lp_l or "usd" in lp_l or "dr" in lp_l:
                        return False
            full_n = f"{fn} {ln}".strip() if (ln and ln != "-") else fn
            full_n_clean = strip_diacritics(full_n).lower()
            for doc in ALL_CERTIFIED_DOCTORS_LIST:
                d_clean = strip_diacritics(doc).lower()
                d_parts = d_clean.replace("dr.", "").replace("dr", "").strip().split()
                if len(d_parts) >= 2:
                    if (d_parts[0] in full_n_clean and d_parts[-1] in full_n_clean) or d_clean in full_n_clean or full_n_clean in d_clean:
                        return False
                elif d_clean in full_n_clean or full_n_clean in d_clean:
                    return False
            return True

        def extract_dental_concern(t):
            if not t:
                return ""
            tl = t.lower().strip()
            if is_valid_name(t.split()[0], t.split()[1] if len(t.split()) > 1 else '') and len(t.split()) <= 3:
                if not any(dw in tl for dw in ["teeth", "tooth", "smile", "dant", "daant", "દાંત", "દાંતમાં", "दांत", "मसूड़े", "पेढा"]):
                    return ""   

            if any(q in tl for q in [
                "explain", "what is", "what's", "whats", "how does", "how do", "tell me about", "can you tell", "cost of", "price of",
                "su che", "shu chhe", "su chhe", "shu che", "etle su", "etle shu", "matlab", "meaning", "mean", "kya hai", "kaise hota", "samjhao", "samjhavo", "batao", "batana", "detail", "information",
                "janvu", "janna"
            ]):
                return ""

            has_dental_context = any(dw in tl for dw in [
                "teeth", "tooth", "smile", "dant", "daant", "molar", "dadh", "enamel", "veneer", "veneers", "crown", "crowns", "gum", "gums",
                "દાંત", "દાંતમાં", "દાંતો", "દાઢ", "પેઢા", "પેઢાં", "સ્માઇલ", "વિનિયર",
                "दांत", "दांतों", "दाँत", "दाढ़", "मसूड़े", "मसूड़ों", "स्माइल", "विनियर"
            ])

            non_dental_parts = [
                "naak", "nak", "nose", "aankh", "aankho", "ankh", "eye", "eyes", "kaan", "ear", "ears",
                "gala", "gale", "throat", "mathu", "matho", "head", "headache", "sir dard", "pet", "stomach",
                "haath", "hand", "hands", "pag", "leg", "legs", "kambar", "back", "backache", "chhati", "chest",
                "skin", "chamdi", "fat burner", "weight loss", "belly",
                "नाक", "आँख", "आँखों", "आंख", "आंखों", "कान", "गला", "गले", "माथा", "सिर", "पेट", "हाथ", "पैर", "कमर", "छाती", "त्वचा",
                "નાક", "આંખ", "આંખો", "કાન", "ગળું", "ગળા", "માથું", "માથા", "પેટ", "હાથ", "પગ", "કમર", "છાતી", "ચામડી"
            ]
            for nd in non_dental_parts:
                if any(ord(c) > 127 for c in nd):
                    if nd in tl and not has_dental_context:
                        return ""
                else:
                    if re.search(r"\b" + re.escape(nd) + r"\b", tl, re.IGNORECASE) and not has_dental_context:
                        return ""

            def _has_word(pattern_list):
                for p in pattern_list:
                    if any(ord(c) > 127 for c in p):
                        if p in tl:
                            return True
                    else:
                        if re.search(r"\b" + re.escape(p) + r"\b", tl, re.IGNORECASE):
                            return True
                return False                 

            symptoms = []
            pain_compound_words = [
                "teeth pain", "tooth pain", "dant dard", "daant dard", "daant ma dukhaavo", "dant ma dukhavo", "dant dukhe", "dant dukhe chhe",
                "dant ma dard", "daant ma dard", "દાંતમાં દુખાવો", "દાંત નો દુખાવો", "દાંતમાં દર્દ", "દાંત દુખે છે", "દાંત દુખે", "દાઢમાં દુખાવો", "દાઢ દુખે છે",
                "दांत में दर्द", "दांत का दर्द", "दांत दर्द", "दांतों में दर्द", "दाढ़ में दर्द", "दांत दुख रहा है", "दांत में पीड़ा", "दांत दुखत आहे",
                "dante byatha", "pal vali", "panti noppi", "hallu novu", "pallu vedana", "dand peerh", "danta bindha"
            ]
            if _has_word(pain_compound_words) or (has_dental_context and _has_word([
                "dukhavo", "dukhaavo", "dukhado", "dukhavu", "dukhe", "dukh", "dard", "pain", "pida", "peeda",
                "દુખાવો", "દુઃખાવો", "પીડા", "દુખે છે", "દર્દ", "दर्द", "दर्द होता है", "पीड़ा"
            ])):
                symptoms.append("pain in teeth")

            if _has_word(["black spot", "black spots", "black teeth", "કાળા ડાઘ", "કાળા દાંત", "काले दांत", "दांत में काला"]) or (has_dental_context and _has_word(["kala", "kaala", "black", "dhabba", "કાળા", "કાળા ડાઘ", "काला"])):
                symptoms.append("black spots / dark discoloration")

            if _has_word(["yellow teeth", "stains on teeth", "yellow stains", "પીળા દાંત", "पीले दांत", "दांत पीले"]) or (has_dental_context and _has_word(["yellow", "stain", "stains", "discolor", "bleach", "pila", "peela", "daag", "dhabba", "પીળા", "ડાઘ"])):
                symptoms.append("yellow stains / discoloration")

            if _has_word(["cavity", "decay", "sado", "kido", "keeda", "khado", "khadho", "સડો", "કીડો", "ખાડો", "કેવિટી", "सड़न", "कीड़ा", "कैविटी", "दांत में कीड़ा"]):
                symptoms.append("dental cavity and decay")

            if _has_word(["crooked teeth", "misaligned teeth", "crowded teeth", "straighten teeth", "વાંકા દાંત", "ટેढ़े दांत", "दांत सीधे"]) or (has_dental_context and _has_word(["crooked", "misaligned", "crowded", "overlap", "straighten", "unorganise", "unorganized", "irregular", "uneven", "tedhe", "terhe", "alignment", "વાંકા"])):
                symptoms.append("irregular and misaligned teeth")

            if _has_word(["broken tooth", "chipped tooth", "cracked tooth", "તૂટેલા દાંત", "દાંત તૂટી", "टूटा दांत", "टूटे दांत", "दांत टूट गया"]) or (has_dental_context and _has_word(["chip", "broken", "crack", "punch", "toot", "bhangi", "તૂટેલા", "તૂટી ગયા", "ટુકડો", "ટૂટી ગયા", "टूट गया"])):
                symptoms.append("chipped or broken teeth")

            if _has_word(["missing teeth", "lost teeth", "lost tooth", "daant nathi", "dant nathi", "teeth missing", "દાંત નથી", "दांत नहीं हैं", "दांत निकल गया"]):
                symptoms.append("missing teeth")

            if _has_word([
                "masudo", "masuda", "gum swelling", "gum inflammation",
                "દાંતમાં મસા", "પેઢામાં સોજો", "મસો થયો",
                "मसूड़ों में सूजन", "मसूड़े सूज गए", "दांत में सूजन"
            ]) or (has_dental_context and _has_word(["masa", "masaa", "sujan", "soojan", "sooj", "suj", "swelling", "swollen", "inflammation", "સૂજન", "મસા", "સોજો", "मसूड़े", "मसूड़ों", "सूजन", "मसा"])):
                symptoms.append("gum swelling and inflammation")

            if _has_word(["gum bleeding", "bleeding gums", "દાંતમાંથી લોહી", "પેઢામાંથી લોહી", "दांत से खून", "मसूड़ों से खून"]) or (has_dental_context and _has_word(["lohi", "khoon", "bleeding", "blood", "લોહી", "खून"])):
                symptoms.append("bleeding gums and sensitivity")

            if _has_word(["gap between teeth", "spacing between teeth", "daant ma gap", "dant ma gap", "દાંતમાં ગેપ", "દાંત વચ્ચે ગેપ", "દાંતોમાં ગેપ", "दांतों में गैप", "दांतों के बीच गैप"]) or (has_dental_context and _has_word(["gap", "gaps", "spacing", "space", "vachhe gap", "bich me gap", "jagya", "khali jagya", "ગૅપ", "ગેપ", "જગ્યા", "गैップ", "जगह"])):
                symptoms.append("gap between teeth")

            if _has_word(["loose tooth", "loose teeth", "shaking tooth", "દાંત હલે છે", "દાંત હલે", "दांत हिल रहे हैं", "दांत हिलना"]) or (has_dental_context and _has_word(["hale", "hale chhe", "hil", "hil raha", "shaking", "હલે છે", "हिलना"])):
                symptoms.append("loose or mobile teeth")

            if _has_word(["wedding smile", "marriage smile", "wedding makeover", "લગ્ન માટે સ્માઇલ", "शादी के लिए स्माइल"]) or (has_dental_context and _has_word(["wedding", "marriage", "lagan", "lagna", "shaadi", "લગ્ન", "शादी", "विवाह"])):
                symptoms.append("upcoming wedding preparation")

            if _has_word(["smile makeover", "smile design", "smile designer", "smile correction", "smile improve", "mari smile sudharvi", "smile badalvi", "smile banavi", "want smile design", "need smile design", "સ્માઇલ સુધારવી", "સ્માઇલ ડિઝાઇન", "સ્માઇલ ડિઝાઇનિંગ", "स्माइल सुधारना", "स्माइल मेकओवर", "स्माइल डिजाइन", "स्माइल डिज़ाइन", "स्माइल डिजाइनिंग", "smile transformation"]):
                symptoms.append("smile makeover and design")    

            if _has_word(["teeth whitening", "white teeth", "teeth shine", "teeth shining", "દાંત ચમકાવવા", "દાંત સફેદ", "दांत चमकाना", "सफेद दांत"]) or (has_dental_context and _has_word(["chamkav", "chamkavva", "chamkavu", "chamkavvu", "chamkana", "whitening", "shining", "shine", "sparkle", "brighten", "bright", "ચમકાવવા", "ચમકાવવું", "ચમકાવ", "ચમકતા", "चमकाना"])):
                symptoms.append("teeth whitening and smile makeover")

            if _has_word(["rct", "root canal", "teeth sensitivity", "tooth sensitivity", "દાંતમાં સેન્સિટિવિટી", "પાયોરિયા", "પાયોરીયા", "pyorrhea", "gingivitis", "दांतों में ठंडा गरम", "दांत में झनझनाहट", "सेंसिटिविटी"]) or (has_dental_context and _has_word(["rog", "rog se", "bimari", "infection", "sensitivity", "thandu garam", "thanda garam", "ઠંડુ ગરમ", "સેન્સિટિવિટી", "ठंडा गरम", "झनझनाहट"])):
                symptoms.append("dental sensitivity and infection")

            gen_compound_words = [
                "teeth problem", "tooth problem", "dental problem", "teeth issue", "tooth issue", "dental issue",
                "daant problem", "dant problem", "problem with teeth", "issue with teeth", "concern with teeth",
                "દાંતની સમસ્યા", "દાંત ની સમસ્યા", "દાંતમાં સમસ્યા", "દાંતમાં તકલીફ",
                "દાંતની તકલીફ", "દાંત દર્દ", "दांतों की समस्या", "दांत की समस्या", "दांत में दिक्कत"
            ]
            if _has_word(gen_compound_words) or (has_dental_context and _has_word([
                "problem", "issue", "samashya", "samasya", "taklif", "takleef", "સમસ્યા", "તકલીફ", "સમસ્યા", "तकलीफ", "दिक्कत"
            ])):
                symptoms.append("dental issue/ teeth problem ")

            if symptoms:
                uniq_sym = []
                for s in symptoms:
                    if s not in uniq_sym:
                        uniq_sym.append(s)
                return ", ".join(uniq_sym)
            return ""

        def is_affirmative_submit(text):
            if not text or text.startswith("SYSTEM INSTRUCTION:") or text.startswith("["):
                return False
            tl = text.lower().strip()
            tl = re.sub(r"[\s.,!?\\/]+$", "", tl)
            
            edit_words = [
                "change", "update", "edit", "instead", "no my", "no, my", "spelling", "mistake",
                "ferfaar", "ફેરફાર", "badlo", "badlu", "badlavvu", "badlavu", "બદલો", "બદલવી", "बदलो",
                "pan", "પણ", "પરંતુ", "lekin", "but"
            ]
            if any(ew in tl for ew in edit_words):
                return False

            if tl in [
                "submit", "summit", "submitt", "samit", "sabmit", "yes", "yea", "yep", "yeah", "ok", "okay", "sure", "done", "please do", "confirm", "proceed",
                "હા", "હા કરી દો", "હા કરી દ્યો", "ચોક્કસ", "ભલે", "ઠીક છે", "હાજી", "કરી દ્યો", "કરી દો", "સબમિટ", "હા સબમિટ", "સબમિટ કરો", "સબમિટ કરી દો", "સબમિટ કરી દ્યો",
                "हाँ", "हाँ कर दो", "कर दो", "अवश्य", "ज़रूर", "सबमिट", "हाँ सबमिट", "सबमिट करो", "सबमिट कर दीजिए", "सबमिट कर दो", "हाँजी",
                "हो", "हो करा", "करा", "नक्की", "ચાલેલ", "सबमिट", "सबमिट करा", "हो सबमिट करा",
                "হ্যাঁ", "হ্যাঁ করুন", "করুন", "অবশ্যই", "সাবমিট", "সাবমিট করুন", "হ্যাঁ সাবমিট করুন",
                "ஆம்", "சரி", "கண்டிப்பாக", "சமர்ப்பிக்கவும்", "சப்மிட்", "சப்மிட் பண்ணுங்க", "ஆம் சப்மிட் பண்ணுங்க",
                "అవును", "సరే", "తప్పకుండా", "సమర్పించండి", "సబ్మిట్", "సబ్మిట్ చేయండి", "అవును సబ్మిట్ చేయండి",
                "ಹೌದು", "ಸರಿ", "ಖಂಡಿತ", "ಸಲ್ಲಿಸಿ", "ಸಬ್ಮಿಟ್", "ಸಬ್ಮಿಟ್ ಮಾಡಿ", "ಹೌದು ಸಬ್ಮಿಟ್ ಮಾಡಿ",
                "അതെ", "ശരി", "തീർച്ചയായും", "സമർപ്പിക്കുക", "സബ്മിറ്റ്", "സബ്മിറ്റ് ചെയ്യുക", "അതെ സബ്മിറ്റ് ചെയ്യുക",
                "ਹਾਂ", "ਹਾਂਜੀ", "ਜ਼ਰੂਰ", "ਦਰਜ ਕਰੋ", "ਸਬਮਿਟ", "ਸਬਮਿਟ ਕਰੋ", "ਹਾਂ ਸਬਮਿਟ ਕਰੋ",
                "ହଁ", "ହଁ କରନ୍ତୁ", "ନିଶ୍ଚୟ", "ଦାଖଲ କରନ୍ତୁ", "ସବମିଟ୍", "ସବମିଟ୍ କରନ୍ତୁ", "ହଁ ସବମିଟ୍ କରନ୍ତୁ",
                "haan", "ha", "haa", "ha ji", "haan ji", "kar do", "kardo", "kari do", "kari dyo", "kar dyo", "haa kari dyo",
                "yes submit", "chalega", "thik chhe", "theek hai", "bhaley", "chokkas", "zarur", "zaroor", "submit karo", "submit kar do", "submit kari dyo", "submit madi", "submit pannunga", "submit cheyandi", "submit koro", "submit karantu"
            ]:
                return True

            for phrase in [
                "submit", "summit", "submitt", "confirm appointment", "સબમિટ", "सबमिट", "சமர்ப்பிக்கவும்", "సమర్పించండి", "ಸಲ್ಲಿಸಿ", "സമർപ്പിക്കുക", "ਦਰਜ ਕਰੋ", "ଦାਖଲ କରନ୍ତୁ"
            ]:
                if re.search(r"\b" + re.escape(phrase) + r"\b", tl) or phrase in tl:
                    return True
            return False

        if self.session.user_name and ("riya" in self.session.user_name.lower() or "usd" in self.session.user_name.lower() or "[" in self.session.user_name or ":" in self.session.user_name or len(self.session.user_name) > 30):
            self.session.user_name = ""
            self.session.booking_slots["first_name"] = ""
            self.session.booking_slots["last_name"] = ""

        # Scan history for review summary if present - ALWAYS UNCONDITIONALLY OVERWRITE WITH REVIEW SUMMARY
        if history and isinstance(history, list):
            user_mentioned_doctors = set()
            for h_t in history:
                if h_t.get("role") in ["user", "client"]:
                    u_t_text = get_turn_text(h_t)
                    d_m = find_doctor_in_text(u_t_text)
                    if d_m:
                        user_mentioned_doctors.add(d_m.lower())

            for turn in reversed(history):
                if turn.get("role") in ["model", "assistant"]:
                    p_txt = get_turn_text(turn)
                    if p_txt and is_submit_review_summary(p_txt):
                        sum_slots_last = extract_slots_from_review_summary(p_txt)
                        if sum_slots_last:
                            if sum_slots_last.get("doctor_name"):
                                d_check = sum_slots_last["doctor_name"].lower()
                                if not any(d_check in umd or umd in d_check for umd in user_mentioned_doctors):
                                    sum_slots_last.pop("doctor_name", None)
                            for k, v in sum_slots_last.items():
                                if v and str(v).lower() not in ["none", "null", "-", "--"]:
                                    self.session.booking_slots[k] = v
                            if sum_slots_last.get("user_name"):
                                self.session.user_name = sum_slots_last["user_name"]
                                p_n = sum_slots_last["user_name"].split()
                                self.session.booking_slots["first_name"] = p_n[0]
                                self.session.booking_slots["last_name"] = " ".join(p_n[1:]) if len(p_n) > 1 else "-"
                            if sum_slots_last.get("user_concern") or sum_slots_last.get("message"):
                                self.session.user_concern = sum_slots_last.get("user_concern") or sum_slots_last.get("message")
                                self.session.booking_slots["message"] = self.session.user_concern
                            self.session.last_review_summary_slots = dict(sum_slots_last)
                            self.session.last_review_summary_text = p_txt
                            break

        # Reconstruct session memory from history turns
        if history and isinstance(history, list):
            user_turns_count = 0
            for turn in history:
                role = turn.get("role")
                p = get_turn_text(turn)
                if not p:
                    continue
                if role in ["user", "client"]:
                    user_turns_count += 1
                    # Check city in history (accepts all certified and regional residence cities)
                    c_found = extract_city_from_text(p)
                    if c_found and not self.session.booking_slots.get("city"):
                        self.session.booking_slots["city"] = c_found
                        self.session.unsupported_city = None

                    # Check phone in history
                    valid_phone_h = extract_valid_phone(p)
                    if valid_phone_h and not self.session.booking_slots.get("phone"):
                        self.session.booking_slots["phone"] = valid_phone_h

                    # Check doctor name in history
                    doc_h = find_doctor_in_text(p, self.session.booking_slots.get("city"))
                    if doc_h and not self.session.booking_slots.get("doctor_name"):
                        self.session.booking_slots["doctor_name"] = doc_h

                    # Check concern in history
                    c_found_c = extract_dental_concern(p)
                    if c_found_c and not self.session.user_concern:
                        self.session.user_concern = c_found_c
                        self.session.booking_slots["message"] = c_found_c

                    # Check explicit name in history only if name is missing
                    if not self.session.user_name:
                        m_exp = re.search(r"(?:my name is|my full name is|myself|call me|i am|i'm|this is|મારું નામ|મારુ નામ|મારો નામ|મારી નામ|(?:maru|maro|maaru|mari|mera|meri|apna|majhe|amar)\s+(?:naam|nam|name|naav|nav|नाव|નામ|नाम)|maru naam|maro naam|maru nam|maro nam|नाम|मेरा नाम|mera naam|mera nam|नाव|माझे नाव|majhe nav|নাম|আমার নাম|amar naam|பெயர்|என் பெயர்|en peyar|పేరు|నా పేరు|naa peru|ಹೆಸರು|ನನ್ನ ಹೆಸರು|nanna hesaru|പേര്|എന്റെ പേര്|ente peru|ਨਾਮ|ਮੇਰਾ ਨਾਮ|mera naa|ਨਾਮ|ਮੋਰਾ ନਾਮ|mora nama)\s*[:：\-]?\s*([A-Za-z\u0A80-\u0AFF\u0900-\u097F\u0980-\u09FF\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F\u0A00-\u0A7F\u0B00-\u0B7F\s]{2,60})", p, re.IGNORECASE)
                        if m_exp:
                            cand_full = m_exp.group(1).strip()
                            cand_splits = re.split(r"(?:my name is|maru naam|maro naam|mera naam|mera nam|મારું નામ|મારુ નામ|મારો નામ|मेरा नाम|नाव|नाम|name)", cand_full, flags=re.IGNORECASE)
                            if len(cand_splits) > 1:
                                cand_full = cand_splits[-1].strip()
                            cand_full = re.split(r"[\-\–\—\n,|!?।.;:\(\)\[\]]", cand_full)[0].strip()
                            cand_full = re.sub(r"\s+(?:chhe|che|hai|hain|hoon|hu|is|am|are|hूँ|છે|છુ|છીએ|હું|હે|તો|પણ|and|yes|no|है|हूँ|हैं|हो|था|थी|थे|હતો|હતી|હતા)\b.*$", "", cand_full, flags=re.IGNORECASE).strip()
                            cand_full = re.sub(r"\s+(?:છે|છુ|છીએ|હું|હે|તો|પણ|है|हूँ|हैं|हो|था|थी|थे|હતો|હતી|હતા).*$", "", cand_full).strip()
                            cand_full = re.sub(r"[\s।.,!?:;\-–—/\\(){}\[\]\"'|`~]+", " ", cand_full).strip()
                            parts = cand_full.split()
                            if parts:
                                stop_verbs = ["se", "to", "bhi", "hai", "hain", "hoon", "hu", "chhe", "che", "is", "am", "are", "છે", "છુ", "છીએ", "હું", "હે", "તો", "પણ", "है", "हूँ", "हैं", "हो", "था", "थी", "थे", "સે", "તે"]
                                parts = [p_w for p_w in parts if p_w.lower() not in stop_verbs]
                                if parts:
                                    raw_fn = parts[0].strip()
                                    raw_ln = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
                                    fn = transliterate_to_english(raw_fn).strip().capitalize() if any(ord(c) > 127 for c in raw_fn) else raw_fn.capitalize()
                                    ln = transliterate_to_english(raw_ln).strip().capitalize() if (raw_ln and any(ord(c) > 127 for c in raw_ln)) else (raw_ln.capitalize() if raw_ln else "-")
                                    if is_valid_name(fn, ln):
                                        self.session.user_name = f"{fn} {ln}".strip() if (ln and ln != "-") else fn
                                        self.session.booking_slots["first_name"] = fn
                                        self.session.booking_slots["last_name"] = ln if (ln and is_valid_name(fn, ln)) else "-"

        if user_text:
            text = user_text.strip()
            
            # Detect general update / change intent
            is_update_intent = any(w in text.lower() for w in [
                "change", "update", "correct", "modify", "instead", "edit", "wrong", "mistake",
                "badlo", "badlu", "badlavu", "badlavvu", "sudharo", "sudharvu", "ferfar", "badal",
                "ખોટું", "બદલ", "બદલો", "બદલવો", "બદલવી", "બદલવા", "બદલવું", "અપડેટ", "સુધાર", "સુધારો", "સુધારવું", "ફેરફાર", "નંબર બદલો", "નામ બદલો", "શહેર બદલો", "ડૉક્ટર બદલો", "સમસ્યા બદલો",
                "गलत", "बदल", "बदलो", "बदलना", "अपडेट", "सुधार", "सुधारो", "सुधारना", "नंबर बदलो", "नाम बदलो", "शहर बदलो", "डॉक्टर बदलो", "समस्या बदलो"
            ])
            if is_update_intent:
                self.session.booking_slots["is_submitted"] = False
                self.session.slot_just_updated = True

            # Detect specific field edit intent where user has NOT provided the new value yet
            has_city_kw = bool(re.search(r"\b(city|shahar|shaher|sahar|શહેર|शहर)\b", text.lower()))
            has_doc_kw = bool(re.search(r"\b(doctor|dr|dentist|daktar|dakatar|ડૉક્ટર|ડોક્ટર|डॉक्टर)\b", text.lower()))
            
            is_phone_edit_req = is_update_intent and bool(re.search(r"\b(phone|number|mobile|fon|fone|ફોન|નંબર|મોબાઇલ|फोन|नंबर|मोबाइल)\b", text.lower()))
            is_city_edit_req = is_update_intent and has_city_kw
            is_doc_edit_req = is_update_intent and has_doc_kw
            is_name_edit_req = is_update_intent and not has_city_kw and not has_doc_kw and bool(re.search(r"\b(name|naam|નામ|नाम|नाव)\b", text.lower()))
            is_concern_edit_req = is_update_intent and bool(re.search(r"\b(concern|problem|issue|samasya|samasy|takleef|dard|સમસ્યા|તકલીફ|દર્દ|समस्या|तकलीफ|दर्द)\b", text.lower()))
            
            # Detect explicit name rejection from user
            if any(w in text.lower() for w in ["ખોટું નામ", "ખોટું નોંધ્યું", "નામ ખોટું", "naam galat", "galat naam", "wrong name", "incorrect name", "not my name", "haven't given my name"]):
                self.session.user_name = ""
                self.session.booking_slots["first_name"] = ""
                self.session.booking_slots["last_name"] = ""
            
            # Detect email pattern
            email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)
            if email_match:
                self.session.booking_slots["email"] = email_match.group(0).strip()
            
            # Detect strict valid 10-digit Indian phone pattern
            valid_phone = extract_valid_phone(text)
            digits_in_text = "".join(filter(str.isdigit, text))
            if valid_phone:
                if self.session.booking_slots.get("phone") != valid_phone:
                    self.session.booking_slots["phone"] = valid_phone
                    self.session.booking_slots["is_submitted"] = False
                    self.session.slot_just_updated = True
                self.session.last_invalid_phone_input = None
                self.session.asking_for_field = None
            elif is_update_intent and is_phone_edit_req:
                # User specifically asked to change phone number, but hasn't given the 10 digits yet
                self.session.booking_slots["phone"] = ""
                self.session.booking_slots["is_submitted"] = False
                self.session.slot_just_updated = False
                self.session.asking_for_field = "phone"
            elif len(digits_in_text) >= 4 and not self.session.booking_slots.get("phone"):
                self.session.last_invalid_phone_input = digits_in_text

            # ⚡ Step 1: City extraction from user text (Always extract BEFORE Doctor to support simultaneous updates) ⚡
            asking_c = (getattr(self.session, 'asking_for_field', None) == "city")
            c_user = extract_city_from_text(text, asking_for_city=asking_c)
            if c_user:
                old_c = self.session.booking_slots.get("city")
                has_explicit_residence = bool(re.search(r"\b(?:i live in|i stay in|i am from|living in|staying in|reside in|my city is|mari city|maru saher|mera shahar|maru shaher|mera sahar)\b", text, re.IGNORECASE))
                # Only set or overwrite city if:
                # 1. No city was set yet, OR
                # 2. We were actively asking for city, OR
                # 3. User explicitly requested a city update / edit, OR
                # 4. User explicitly stated their residence phrase
                if not old_c or asking_c or is_city_edit_req or has_explicit_residence:
                    if old_c != c_user:
                        self.session.booking_slots["city"] = c_user
                        self.session.unsupported_city = None
                        self.session.city_doctor_mismatch = None
                        self.session.booking_slots["is_submitted"] = False
                        self.session.slot_just_updated = True
                        self.session.city_just_changed = True
                        if asking_c:
                            self.session.asking_for_field = None
                        # Check if user also named a doctor in this same turn
                        doc_with_new_city = find_doctor_in_text(text, c_user)
                        if not doc_with_new_city:
                            doc_with_new_city = find_doctor_in_text(text, city=None)
                        if doc_with_new_city:
                            self.session.booking_slots["doctor_name"] = doc_with_new_city
                            self.session.pending_doctor_candidate = None
                            self.session.asking_for_field = None
            elif is_update_intent and is_city_edit_req:
                self.session.booking_slots["city"] = ""
                self.session.city_doctor_mismatch = None
                self.session.booking_slots["is_submitted"] = False
                self.session.slot_just_updated = False
                self.session.asking_for_field = "city"

            # ⚡ Step 2: Doctor detection in user text (evaluated using active/updated city) ⚡
            active_city = self.session.booking_slots.get("city")
            doc_found = find_doctor_in_text(text, active_city)
            if not doc_found:
                doc_found = find_doctor_in_text(text, city=None)
            if doc_found:
                if self.session.booking_slots.get("doctor_name") != doc_found:
                    self.session.booking_slots["doctor_name"] = doc_found
                    self.session.booking_slots["is_submitted"] = False
                    self.session.slot_just_updated = True
                self.session.pending_doctor_candidate = None
                self.session.last_uncertified_doctor = None
                self.session.city_doctor_mismatch = None
                self.session.asking_for_field = None

                # If appointment was already submitted, sync the new doctor directly to database
                if self.session.booking_slots.get("submission_id") or self.session.booking_slots.get("phone"):
                    try:
                        from voice_agent.services.appointment_service import save_lead_to_local_db, sync_lead_to_godaddy_sqlite, sync_lead_to_api_endpoint, ENABLE_GODADDY_SYNC
                        sync_args = dict(self.session.booking_slots)
                        sync_args["doctor_name"] = doc_found
                        sync_args["is_cancel"] = False
                        sync_args["is_update"] = True
                        sync_args["submission_id"] = self.session.booking_slots.get("submission_id")
                        if self.session.booking_slots.get("godaddy_id"):
                            sync_args["godaddy_id"] = self.session.booking_slots.get("godaddy_id")
                        if self.session.booking_slots.get("api_id"):
                            sync_args["api_id"] = self.session.booking_slots.get("api_id")
                        transcript_text = self._build_transcript_text()
                        if transcript_text:
                            sync_args["transcript"] = transcript_text
                        asyncio.create_task(save_lead_to_local_db(sync_args))
                        loop = asyncio.get_event_loop()
                        loop.run_in_executor(None, sync_lead_to_api_endpoint, sync_args)
                        if ENABLE_GODADDY_SYNC:
                            loop.run_in_executor(None, sync_lead_to_godaddy_sqlite, sync_args)
                    except Exception as sync_e:
                        print(f"[WARN] Error updating doctor in DB: {sync_e}")
            elif is_update_intent and is_doc_edit_req:
                # User wants to update doctor but hasn't named one yet
                self.session.booking_slots["doctor_name"] = ""
                self.session.booking_slots["is_submitted"] = False
                self.session.slot_just_updated = False
                self.session.asking_for_field = "doctor"

            elif getattr(self.session, 'pending_doctor_candidate', None) and not self.session.booking_slots.get("doctor_name"):
                if is_affirmative_submit(text):
                    self.session.booking_slots["doctor_name"] = self.session.pending_doctor_candidate
                    self.session.pending_doctor_candidate = None
                elif text.lower().strip() in ["no", "na", "nah", "nope", "nathi", "nahi"]:
                    self.session.pending_doctor_candidate = None
            elif not self.session.booking_slots.get("doctor_name"):
                doc_partial = find_partial_doctor(text, active_city)
                if not doc_partial:
                    doc_partial = find_partial_doctor(text, city=None)
                if doc_partial:
                    self.session.pending_doctor_candidate = doc_partial
                    self.session.city_doctor_mismatch = None
                else:
                    # Check if user requested a doctor
                    doc_other_city = find_doctor_in_text(text, city=None)
                    if doc_other_city:
                        self.session.booking_slots["doctor_name"] = doc_other_city
                        self.session.pending_doctor_candidate = None
                        self.session.city_doctor_mismatch = None
                    else:
                        self.session.city_doctor_mismatch = None

                    uncert_user = detect_uncertified_doctor(text)
                    if uncert_user:
                        self.session.last_uncertified_doctor = uncert_user
                    else:
                        self.session.last_uncertified_doctor = None

            # Name extraction: Check explicit name statements first (ALWAYS extracted regardless of prior name)
            m_exp = re.search(r"(?:my name is|my full name is|myself|call me|i am|i'm|this is|મારું નામ|મારુ નામ|મારો નામ|મારી નામ|(?:maru|maro|maaru|mari|mera|meri|apna|majhe|amar)\s+(?:naam|nam|name|naav|nav|नाव|નામ|नाम)|maru naam|maro naam|maru nam|maro nam|नाम|मेरा नाम|mera naam|mera nam|नाव|माझे नाव|majhe nav|নাম|আমার নাম|amar naam|பெயர்|என் பெயர்|en peyar|పేరు|నా పేరు|naa peru|ಹೆಸರು|ನನ್ನ ಹೆಸರು|nanna hesaru|പേര്|എന്റെ പേര്|ente peru|ਨਾਮ|ਮੇਰਾ ਨਾਮ|mera naa|ਨਾਮ|ਮੋਰਾ ਨਾਮ|mora nama)\s*[:：\-]?\s*([A-Za-z\u0A80-\u0AFF\u0900-\u097F\u0980-\u09FF\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F\u0A00-\u0A7F\u0B00-\u0B7F\s]{2,60})", text, re.IGNORECASE)
            if not m_exp:
                m_exp = re.search(r"(?:change|update|badlo|badli|badlavu|correct)\s+(?:my\s+)?(?:name|naam|નામ|नाम)\s+(?:to|se|ma|karine)?\s*([A-Za-z\u0A80-\u0AFF\u0900-\u097F\u0980-\u09FF\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F\u0A00-\u0A7F\u0B00-\u0B7F\s]{2,40})", text, re.IGNORECASE)
            if not m_exp:
                m_exp = re.search(r"(?:maare|mare|maru|maaru|mari|mane|mujhe|mera)\s+(?:naam|name|નામ|नाम)\s+([A-Za-z\u0A80-\u0AFF\u0900-\u097F\u0980-\u09FF\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F\u0A00-\u0A7F\u0B00-\u0B7F\s]{2,40})\s+(?:change|update|badlavvu|badlavu|badli|badlo|karvu|karvo|karo|rakhvu|rakhvo|kardo)", text, re.IGNORECASE)
            if not m_exp:
                m_exp = re.search(r"\b(?:my name is only|it'?s only|my name is actually|actually my name is|correct name is|my full name is)\s+([A-Za-z\u0A80-\u0AFF\u0900-\u097F\u0980-\u09FF\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F\u0A00-\u0A7F\u0B00-\u0B7F\s]{2,40})", text, re.IGNORECASE)

            if not m_exp:
                # Handles: "[Name] maru naam chhe", "[Name] mera naam hai"
                m_pre = re.search(r"([A-Za-z\u0A80-\u0AFF\u0900-\u097F]{2,25}(?:\s+[A-Za-z\u0A80-\u0AFF\u0900-\u097F]{2,25})?)\s+(?:maru|maro|maaru|mari|mera|meri|apna|majhe|amar|મારું|મારુ|મારો|मेरा|माझे|ਮੇરા)\s+(?:naam|nam|name|naav|nav|નામ|नाम|नाव)", text, re.IGNORECASE)
                if m_pre:
                    raw_cand = m_pre.group(1).strip()
                    raw_cand = re.sub(r"^(?:yaar|yar|bhai|are|arre|arrey|oh|oho|hey|hi|hello|na|nahi|nahin)\s+", "", raw_cand, flags=re.IGNORECASE).strip()
                    if raw_cand:
                        cand_full = raw_cand
                        m_exp = True

            if m_exp:
                if not isinstance(m_exp, bool):
                    cand_full = m_exp.group(1).strip()
                cand_splits = re.split(r"(?:my name is|maru naam|maro naam|mera naam|mera nam|મારું નામ|મારુ નામ|મારો નામ|मेरा नाम|नाव|नाम|name)", cand_full, flags=re.IGNORECASE)
                if len(cand_splits) > 1:
                    cand_full = cand_splits[-1].strip()
                cand_full = re.split(r"[\-\–\—\n,|!?।.;:\(\)\[\]]", cand_full)[0].strip()
                cand_full = re.sub(r"\s+(?:chhe|che|hai|hain|hoon|hu|is|am|are|hूँ|છે|છુ|છીએ|હું|હે|તો|પણ|and|yes|no|है|हूँ|हैं|हो|था|थी|थे|હતો|હતી|હતા)\b.*$", "", cand_full, flags=re.IGNORECASE).strip()
                cand_full = re.sub(r"\s+(?:છે|છુ|છીએ|હું|હે|તો|પણ|है|हूँ|हैं|हो|था|थी|थे|હતો|હતી|હતા).*$", "", cand_full).strip()
                cand_full = re.sub(r"[\s।.,!?:;\-–—/\\(){}\[\]\"'|`~]+", " ", cand_full).strip()
                parts = cand_full.split()
                if parts:
                    stop_verbs = ["se", "to", "bhi", "hai", "hain", "hoon", "hu", "chhe", "che", "is", "am", "are", "છે|છુ|છીએ|હું|હે|તો|પણ", "है", "हूँ", "हैं", "हो", "था", "थी", "थे", "સે", "તે"]
                    parts = [p_w for p_w in parts if p_w.lower() not in stop_verbs]
                    if parts:
                        raw_fn = parts[0].strip()
                        raw_ln = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
                        f_name = transliterate_to_english(raw_fn).strip().capitalize() if any(ord(c) > 127 for c in raw_fn) else raw_fn.capitalize()
                        l_name = transliterate_to_english(raw_ln).strip().capitalize() if (raw_ln and any(ord(c) > 127 for c in raw_ln)) else (raw_ln.capitalize() if raw_ln else "-")
                        if is_valid_name(f_name, l_name):
                            self.session.user_name = f"{f_name} {l_name}".strip() if (l_name and l_name != "-") else f_name
                            self.session.booking_slots["first_name"] = f_name
                            self.session.booking_slots["last_name"] = l_name if (l_name and is_valid_name(f_name, l_name)) else "-"
                            self.session.booking_slots["is_submitted"] = False
                            self.session.slot_just_updated = True
                            self.session.asking_for_field = None
            elif is_update_intent and is_name_edit_req:
                # User wants to update name but hasn't given the name yet
                self.session.user_name = ""
                self.session.booking_slots["first_name"] = ""
                self.session.booking_slots["last_name"] = ""
                self.session.booking_slots["is_submitted"] = False
                self.session.slot_just_updated = False
                self.session.asking_for_field = "name"
            else:
                # Bare name detection: ONLY allowed if patient's name is NOT already known, OR if patient is in explicit name edit mode!
                user_name_already_known = bool(self.session.user_name and self.session.booking_slots.get("first_name"))
                asking_f = getattr(self.session, 'asking_for_field', None)
                is_name_edit_active = (asking_f == "name" or is_name_edit_req)

                if not user_name_already_known or is_name_edit_active:
                    bare_name_pat = r"^([A-Za-z\u0A80-\u0AFF\u0900-\u097F\u0980-\u09FF\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F\u0A00-\u0A7F\u0B00-\u0B7F]{2,20})(?:\s+([A-Za-z\u0A80-\u0AFF\u0900-\u097F\u0980-\u09FF\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F\u0A00-\u0A7F\u0B00-\u0B7F]{2,20}))?$"
                    m_bare = re.search(bare_name_pat, text.strip(), re.IGNORECASE)
                    if m_bare:
                        raw_fn = m_bare.group(1).strip()
                        raw_ln = m_bare.group(2).strip() if m_bare.group(2) else ""
                        f_name = transliterate_to_english(raw_fn).strip().capitalize() if any(ord(c) > 127 for c in raw_fn) else raw_fn.capitalize()
                        l_name = transliterate_to_english(raw_ln).strip().capitalize() if (raw_ln and any(ord(c) > 127 for c in raw_ln)) else (raw_ln.capitalize() if raw_ln else "")

                        # If user gave only surname (e.g. "Parmar") while first name is already known (e.g. "Bhavin")
                        cur_ln = self.session.booking_slots.get("last_name")
                        cur_fn = self.session.booking_slots.get("first_name")
                        
                        if f_name and not l_name:
                            if cur_fn and cur_fn.lower() != f_name.lower():
                                # Only treat as surname if current last name is empty or "-" and not a conversational/concern word
                                if (not cur_ln or cur_ln == "-") and is_valid_name(cur_fn, f_name):
                                    l_name = f_name
                                    f_name = cur_fn
                                else:
                                    # Do not replace existing valid name/surname with random words
                                    f_name = ""

                        if f_name and is_valid_name(f_name, l_name or "-"):
                            self.session.user_name = f"{f_name} {l_name}".strip() if (l_name and l_name != "-") else f_name
                            self.session.booking_slots["first_name"] = f_name
                            self.session.booking_slots["last_name"] = l_name if l_name else "-"
                            self.session.booking_slots["is_submitted"] = False
                            self.session.asking_for_field = None

            # Affirmative name confirmation check for Step 1
            if self.session.user_name and not getattr(self.session, 'name_confirmed', False):
                affirmative_confirm_words = [
                    "yes", "yeah", "yep", "sure", "correct", "right", "sahi", "sahi hai", "barabar", "barabar chhe", "chokkas", "ha", "haan", "ha ji", "haan ji", "bilkul", "thik", "theek", "satya", "kharekhar", "avunu", "aamam", "haudu", "athe", "haanji"
                ]
                tl_words = text.lower().strip()
                if any(re.search(r"\b" + re.escape(w) + r"\b", tl_words) for w in affirmative_confirm_words) or any(w in tl_words for w in ["हाँ", "हां", "सही", "બરાબર", "હા", "સાચું", "નક્કી", "होय"]):
                    self.session.name_confirmed = True

            concern = extract_dental_concern(text)
            if concern:
                if self.session.user_concern != concern or self.session.booking_slots.get("message") != concern:
                    self.session.user_concern = concern
                    self.session.booking_slots["message"] = concern
                    self.session.booking_slots["is_submitted"] = False
                    self.session.slot_just_updated = True
                    self.session.asking_for_field = None
            elif is_update_intent and is_concern_edit_req:
                self.session.booking_slots["message"] = ""
                self.session.user_concern = ""
                self.session.booking_slots["is_submitted"] = False
                self.session.slot_just_updated = False
                self.session.asking_for_field = "concern"
            
            # Check if user agreed to consultation or initiated booking
            booking_words = ["book", "appointment", "consultation", "अपॉइंटमेंट", "અપૉઇન્ટમેન્ટ", "મુલાકાત", "बुक", "करा दो", "कर दो", "બુક કરો", "બુકિંગ"]
            if any(w in text.lower() for w in booking_words):
                self.session.consultation_agreed = True
            elif self.session.user_concern and not self.session.booking_slots.get("city"):
                from voice_agent.gemini.client import is_affirmative_submit
                if is_affirmative_submit(text):
                    # Check if the previous assistant turn was a non-booking question (philosophy, profession, photo reflection)
                    last_bot_text = ""
                    if history and isinstance(history, list):
                        for h_turn in reversed(history):
                            if h_turn.get("role") in ["model", "assistant"]:
                                parts = h_turn.get("parts", [])
                                if parts and isinstance(parts[0], dict) and "text" in parts[0]:
                                    last_bot_text = parts[0]["text"].lower()
                                elif isinstance(h_turn.get("text"), str):
                                    last_bot_text = h_turn.get("text", "").lower()
                                break
                    non_booking_questions = [
                        "philosophy works", "bring this to life", "photo of your smile", "more natural",
                        "what do you do for work", "aap kya kaam karte", "tame su kaam karo", "tame shu kaam karo",
                        "profession", "व्यवसाय", "पेशा", "પ્રોફેશન", "કામ કરો", "काम करते"
                    ]
                    if not (last_bot_text and any(nbq in last_bot_text for nbq in non_booking_questions)):
                        self.session.consultation_agreed = True
            if self.session.booking_slots.get("city"):
                self.session.consultation_agreed = True


    async def stream_chat_text_response(self, user_text, history, system_prompt):
        """⚡ Blazing fast sub-second Gemini 3.5 Flash Lite streaming specifically for Chat Mode ⚡"""
        self.update_session_memory(user_text, history)
        
        raw_contents = []
        if history:
            for turn in history:
                role = "model" if turn.get("role") in ["model", "assistant"] else "user"
                parts = turn.get("parts", [])
                if parts and isinstance(parts, list) and "text" in parts[0] and parts[0]["text"]:
                    raw_contents.append({"role": role, "text": parts[0]["text"]})
        raw_contents.append({"role": "user", "text": user_text})
        
        # Strictly sanitize to alternating user / model turns for Gemini API compatibility
        contents = []
        curr_role = None
        curr_text_parts = []
        for c in raw_contents:
            r = c["role"]
            t = c["text"]
            if r == curr_role:
                curr_text_parts.append(t)
            else:
                if curr_role is not None:
                    contents.append({"role": curr_role, "parts": [{"text": "\n".join(curr_text_parts)}]})
                curr_role = r
                curr_text_parts = [t]
        if curr_role is not None:
            contents.append({"role": curr_role, "parts": [{"text": "\n".join(curr_text_parts)}]})
        
        # If history starts with model greeting, prepend a user starter
        if contents and contents[0]["role"] == "model":
            contents.insert(0, {"role": "user", "parts": [{"text": "Hello"}]})
        
        # Detect user's current/recent active language from the 11 supported Indian languages
        user_lang = detect_user_language(user_text, history)
        lang_full_names = {
            "en": "English [en-IN]",
            "hi": "Hindi [hi-IN]",
            "gu": "Gujarati [gu-IN]",
            "mr": "Marathi [mr-IN]",
            "bn": "Bengali [bn-IN]",
            "ta": "Tamil [ta-IN]",
            "te": "Telugu [te-IN]",
            "kn": "Kannada [kn-IN]",
            "ml": "Malayalam [ml-IN]",
            "pa": "Punjabi [pa-IN]",
            "or": "Odia [or-IN]"
        }
        lang_display = lang_full_names.get(user_lang, f"{user_lang} [en-IN]")

        active_memory = (
            f"🚨 MANDATORY ACTIVE RESPONSE LANGUAGE: {lang_display} (100% STRICT LOYALTY)\n"
            f"You MUST generate your response ONLY and ENTIRELY in {lang_display}. "
            f"DO NOT switch, mix, or drift into Hindi, Gujarati, or English unless the patient explicitly spoke in that language in this turn.\n"
        )

        assistant_turns_count = sum(1 for turn in history if turn.get("role") in ["model", "assistant"]) if history else 0
        if assistant_turns_count == 2:
            profession_questions = {
                "en": "By the way, what is your profession?",
                "gu": "તેમ છતાં, જો હું પૂછી શકું, તમારો વ્યવસાય (પ્રોફેશન) શું છે?",
                "hi": "वैसे, अगर मैं पूछ सकती हूँ, आपका पेशा या प्रोफेशन क्या है?",
                "mr": "तसे, तुमचा व्यवसाय किंवा प्रोफेशन काय आहे?",
                "bn": "যাইহোক, আপনার পেশা কি?",
                "ta": "வழியில், உங்கள் தொழில் என்ன?",
                "te": "అన్నట్లు, మీ వృత్తి ఏమిటి?",
                "kn": "ಅಂದಹಾಗೆ, ನಿಮ್ಮ ವೃತ್ತಿ ಏನು?",
                "ml": "വഴിയിൽ, നിങ്ങളുടെ തൊഴിൽ എന്താണ്?",
                "pa": "ਵੈਸੇ, ਤੁਹਾਡਾ ਕਿੱਤਾ ਕੀ ਹੈ?",
                "or": "ସେମିତି, ଆପଣଙ୍କ ପେଶା କ'ଣ?"
            }
            prof_q = profession_questions.get(user_lang, profession_questions["en"])
            active_memory += (
                f"\n- 🚨 ABSOLUTE COMPULSORY RULE — RIYA'S 3RD MESSAGE FOLLOW-UP QUESTION:\n"
                f"This is Riya's THIRD (3rd) message in this conversation! "
                f"No matter what topic was discussed or what question the user asked, your follow-up question at the end of this response MUST COMPULSORILY BE to ask what their profession is in {lang_display}: '{prof_q}'.\n"
            )

        if self.session.user_name:
            ln_disp = self.session.booking_slots.get('last_name') or '-'
            active_memory += f"\n- CURRENT PATIENT NAME: {self.session.user_name} (First Name: {self.session.booking_slots.get('first_name')}, Last Name: {ln_disp}, Confirmed: {getattr(self.session, 'name_confirmed', False)})"
        else:
            active_memory += "\n- CURRENT PATIENT NAME: Unknown (User has not provided their name yet. Never guess or hallucinate a name. Ask for their name if needed)."

        patient_city = self.session.booking_slots.get("city")
        if patient_city:
            active_memory += f"\n- CURRENT CONFIRMED PATIENT CITY: {patient_city}"
        else:
            active_memory += "\n- CURRENT PATIENT CITY: Unknown (User has not provided their city yet. Never assume Surat, Mumbai, or any city. Ask for their city if needed)."

        patient_phone = self.session.booking_slots.get("phone")
        if patient_phone:
            active_memory += f"\n- CURRENT CONFIRMED 10-DIGIT PHONE: {patient_phone} (Valid 10-digit mobile number confirmed. Do NOT re-ask or question phone; proceed to review summary)."
        elif getattr(self.session, 'last_invalid_phone_input', None):
            active_memory += f"\n- CURRENT PATIENT PHONE: INVALID INPUT ({self.session.last_invalid_phone_input} is NOT a 10-digit mobile number, it has {len(self.session.last_invalid_phone_input)} digits). Politely inform the patient: 'That does not look like a valid 10-digit mobile number. Could you please provide your 10-digit mobile number?'."
        else:
            active_memory += "\n- CURRENT PATIENT PHONE: Unknown (Ask for their 10-digit mobile number)."

        patient_doctor = self.session.booking_slots.get("doctor_name")
        pending_doc = getattr(self.session, 'pending_doctor_candidate', None)
        uncert_doc = getattr(self.session, 'last_uncertified_doctor', None)
        if patient_doctor:
            active_memory += f"\n- CURRENT CONFIRMED DOCTOR: {patient_doctor}"
        elif pending_doc:
            active_memory += f"\n- PENDING DOCTOR CANDIDATE: {pending_doc} (Patient gave partial name '{user_text}'). NEXT IMMEDIATE STEP (MANDATORY): Ask to confirm the full name and city: 'Are you talking about {pending_doc} from {patient_city or 'your city'}?'"
        elif uncert_doc:
            active_memory += f"\n- CRITICAL ALERT: The user mentioned '{uncert_doc}', who is NOT on our official certified list! Politely refuse: '{uncert_doc} is not on our certified list as they are not a USD Certified Smile Designer. Please choose one of our certified smile designers from {patient_city or 'your city'}, and let me know whenever you are ready.' (CRITICAL: Do NOT list doctor names, do NOT accept '{uncert_doc}', and do NOT proceed until a certified doctor is chosen)."
        mismatch_info = getattr(self.session, 'city_doctor_mismatch', None)
        if mismatch_info:
            d_city = mismatch_info['doctor_city']
            u_city = mismatch_info['user_city']
            active_memory += (
                f"\n- 🚨 CRITICAL DOCTOR-CITY MISMATCH:\n"
                f"The patient is in '{u_city}', but asked about/requested a doctor who practices in '{d_city}'.\n"
                f"FACT: That doctor is located in '{d_city}', NOT in '{u_city}'!\n"
                f"MANDATORY ACTION (STRICT NO-NAME-SPOKEN RULE): Inform the patient in {user_lang} WITHOUT speaking the doctor's name out loud:\n"
                f"'That doctor is located in {d_city}, not in {u_city}. Please select our USD doctor in {u_city}, or you can check out our Find Dentist page.'\n"
                f"(Gujarati: 'તે ડૉક્ટર {d_city}માં છે, {u_city}માં નથી. કૃપા કરીને {u_city}માં અમારા USD ડૉક્ટર પસંદ કરો, અથવા તમે અમારા Find Dentist પેજ પર જોઈ શકો છો.')\n"
                f"(Hindi: 'वह डॉक्टर {d_city} में स्थित हैं, {u_city} में नहीं। कृपया {u_city} में हमारे USD डॉक्टर का चयन करें, या आप हमारे Find Dentist पेज पर जाकर देख सकते हैं।')\n"
                f"(CRITICAL: DO NOT accept that doctor for {u_city} and DO NOT speak their name!)."
            )
        else:
            active_memory += f"\n- CURRENT PREFERRED DOCTOR: {'Not selected' if not patient_doctor else patient_doctor}"

        if self.session.user_concern:
            active_memory += f"\n- CURRENT CONFIRMED DENTAL CONCERN: {self.session.user_concern}"
        else:
            active_memory += "\n- CURRENT PATIENT CONCERN: Unknown (User has not provided their concern yet. Never assume gaps in teeth. Ask for their concern if needed)."

        if self.session.booking_slots.get("city"):
            norm_c = extract_certified_city_from_text(self.session.booking_slots["city"])
            if norm_c:
                self.session.booking_slots["city"] = norm_c

        # Add booking slot status into active session memory
        slots = self.session.booking_slots
        filled_slots = [f"{k}: {v}" for k, v in slots.items() if v and k not in ['is_booking_active', 'is_submitted']]
        if filled_slots:
            active_memory += f"\n- CURRENT CONFIRMED APPOINTMENT SLOTS: {', '.join(filled_slots)} (Zero amnesia: Do not re-ask these slots; continue with remaining unconfirmed slots)."

        # Determine the next single missing field in logical conversational order:
        fn = self.session.booking_slots.get("first_name")
        ln = self.session.booking_slots.get("last_name")
        ct = self.session.booking_slots.get("city")
        cn = self.session.booking_slots.get("message")
        dr = self.session.booking_slots.get("doctor_name")
        ph = self.session.booking_slots.get("phone")

        asking_field = getattr(self.session, 'asking_for_field', None)
        display_name = f"{fn} {ln}".strip() if (ln and ln != "-" and ln.lower() != fn.lower()) else (self.session.user_name or fn or "Patient")

        if slots.get("is_submitted") and not asking_field:
            next_step_instruction = (
                f"🚨 MANDATORY POST-SUBMISSION PERMANENT LOCK (CRITICAL OVERRIDE):\n"
                f"The consultation appointment for {display_name} (Phone: {ph}, City: {ct}, Doctor: {dr}, Concern: {cn}) has ALREADY BEEN SUCCESSFULLY SUBMITTED to our clinic team!\n"
                f"RULES:\n"
                f"1. NEVER ask 'Shall I book your appointment?', 'Shall I submit your appointment?', 'Should I book your consultation?', 'તમારી અપૉઇન્ટમેન્ટ બુક કરી નાખું?', 'आपकी अपॉइंटमेंट बुक कर दूं?' or offer booking again.\n"
                f"2. UNLESS the user explicitly requests: 'I want to change my appointment', 'modify details', or 'book another appointment', you must NEVER prompt for booking or confirmation.\n"
                f"3. For all other questions regarding veneers, costs, procedures, warranty, and dental care, answer warmly, helpfully, and authoritatively within our dental scope without mentioning booking an appointment."
            )
        elif not fn and not self.session.user_name:
            next_step_instruction = "STEP 1 (NAME): Ask for the patient's full name in their language: 'Let's start with your beautiful name, what is your name?'"
        elif not getattr(self.session, 'name_confirmed', False):
            next_step_instruction = (
                f"STEP 1 (NAME CONFIRMATION - ABSOLUTELY MANDATORY BEFORE ADVANCING TO OTHER STEPS):\n"
                f"The patient shared their name '{display_name}'. You MUST explicitly confirm their name in {user_lang}:\n"
                f"• Gujarati: 'નમસ્તે {display_name}! તમારું નામ {display_name} છે, બરાબર ને? તમારા દાંત કે સ્માઇલમાં તમને શું સમસ્યા આવી રહી છે જેથી હું મદદ કરી શકું?'\n"
                f"• Hindi: 'नमस्ते {display_name}! आपका नाम {display_name} है, सही है ना? आपके दाँतों या स्माइल में आपको क्या समस्या आ रही है जिससे मैं आपकी मदद कर सकूँ?'\n"
                f"• English: 'Namaste {display_name}! Your name is {display_name}, right? What specific concern or goal do you have regarding your teeth or smile?'\n"
                f"🚨 MANDATORY: Do NOT jump to city, doctor, or review summary until the name is confirmed."
            )
        elif asking_field == "name":
            next_step_instruction = f"STEP 1 (NAME UPDATE): The patient wants to update their name. Do NOT present the review summary yet. Ask for their correct full name in {user_lang}: 'Sure! What is your correct full name?' ('ચોક્કસ! તમારું સાચું પૂરું નામ શું છે?')."
        elif not cn or asking_field == "concern":
            next_step_instruction = (
                f"STEP 2 (CONVERSATIONAL CONSULTATION & CONCERN EXPLORATION): The patient's name is '{display_name}'.\n"
                f"- If the patient is asking about or exploring our Smile Design philosophy, porcelain veneers, Adele craft, or good vs superior smile: Answer their question thoroughly, warmly, and educationally in {user_lang} as an expert AI Smile Consultant!\n"
                f"- If the patient shares their profession (doctor, lawyer, teacher, engineer, etc.): Connect their profession naturally using the appropriate profession analogy from the knowledge base without any cosmetic pressure or forcing booking.\n"
                f"- If the patient has not stated any dental concern or smile goal yet and you need to ask: Ask what specific concern or smile goal they have in {user_lang}: 'What specific concern or issue are you experiencing with your teeth or smile, {display_name}?' ('તમને તમારા દાંત કે સ્માઇલ વિશે કઈ સમસ્યા છે, {display_name}?').\n"
                f"🚨 MANDATORY: DO NOT ask for City or Doctor yet! DO NOT force appointment booking until they express a specific dental concern or request booking!"
            )
        elif not getattr(self.session, 'consultation_agreed', False) and not ct:
            next_step_instruction = (
                f"STEP 2.5 (CONCERN ACKNOWLEDGEMENT & CONSULTATION OFFER - MANDATORY PERMISSION GATE):\n"
                f"The patient '{display_name}' revealed their dental concern: '{cn}'.\n"
                f"Empathetically acknowledge their specific concern in {user_lang}, and ask if they would like you to help book a consultation appointment with our USD Certified Smile Designer to resolve it!\n"
                f"🚨 CRITICAL MANDATORY GATE: DO NOT start booking, DO NOT ask for City, and DO NOT ask for Doctor yet in this turn until the patient explicitly says YES or agrees!\n"
                f"• Gujarati: 'હું સમજી શકું છું કે તમને {cn}ની સમસ્યા છે, {display_name}. શું હું આના ઉકેલ માટે અમારા USD સર્ટિફાઇડ સ્માઇલ ડિઝાઇનર સાથે કન્સલ્ટેશન અપૉઇન્ટમેન્ટ બુક કરવામાં મદદ કરું?'\n"
                f"• Hindi: 'मैं समझ सकती हूँ कि आपको {cn} की समस्या आ रही है, {display_name}। क्या मैं इसके समाधान के लिए हमारे USD सर्टिफाइड स्माइल डिज़ाइनर के साथ अपॉइंटमेंट बुक करने में आपकी मदद करूँ?'\n"
                f"• English: 'I understand you are experiencing {cn}, {display_name}. Would you like me to help book a consultation appointment with our USD Certified Smile Designer for this?'"
            )
        elif not ct or asking_field == "city":
            next_step_instruction = (
                f"STEP 3 (CITY / RESIDENCE): The patient '{display_name}' has agreed to consultation for concern '{cn}'. "
                f"Ask which city they reside in {user_lang}: 'Which city do you reside in so our team can record your location?' ('ચોક્કસ! તમે કયા શહેરમાં રહો છો?')."
            )
        elif asking_field == "doctor":
            next_step_instruction = (
                f"STEP 4 (DOCTOR SELECTION - OPTIONAL): The patient wants to choose or update their doctor. "
                f"Ask which USD Certified Smile Designer they would like to consult with in {user_lang}: "
                f"'Which USD Certified Smile Designer would you like to consult with?' "
                f"('તમે કયા USD સર્ટિફાઇડ ડૉક્ટર સાથે કન્સલ્ટ કરવા માંગો છો?'). "
                f"(CRITICAL: Doctor is strictly optional. If the patient has no preference, they can skip and leave it to our clinic team. Strict Privacy: NEVER proactively list, output, or speak doctor names!)."
            )
        elif not ph or asking_field == "phone":
            from voice_agent.utils.helpers import DOCTOR_HOME_CITIES
            certified_hub_cities = set(DOCTOR_HOME_CITIES.values())
            is_hub = ct in certified_hub_cities or any(c.lower() == str(ct).lower() for c in certified_hub_cities)
            if is_hub:
                next_step_instruction = (
                    f"STEP 4 & 5 (DOCTOR GUIDANCE IN CERTIFIED CITY + MANDATORY 10-DIGIT MOBILE NUMBER):\n"
                    f"The patient resides in '{ct}', where our USD Certified Smile Designers are available!\n"
                    f"Explain warmly in {user_lang} that our certified smile designers are available in {ct}, doctor selection is optional (our clinic team will guide them when contacting), and immediately ask for their 10-digit mobile number so our team can get in touch:\n"
                    f"• Gujarati: '{ct}માં અમારા USD સર્ટિફાઇડ સ્માઇલ ડિઝાઇનર્સ ઉપલબ્ધ છે. તમે ડૉક્ટર પસંદ કરી શકો છો અથવા અમારી ટીમ તમારો સંપર્ક કરીને યોગ્ય માર્ગદર્શન આપશે. કૃપા કરીને તમારો 10 અંકનો મોબાઇલ નંબર જણાવશો જેથી અમારી ટીમ તમારો સંપર્ક કરી શકે?'\n"
                    f"• Hindi: '{ct} में हमारे USD सर्टिफाइड स्माइल डिज़ाइनर्स उपलब्ध हैं। आप डॉक्टर चुन सकते हैं या हमारी टीम आपसे संपर्क करके मार्गदर्शन करेगी। कृपया अपना 10 अंकों का मोबाइल नंबर बताएं ताकि हमारी टीम आपसे संपर्क कर सके?'\n"
                    f"• English: 'Our USD Certified Smile Designers are available in {ct}. You may choose a preferred doctor or our clinic team will guide you when they reach out. Could you please provide your 10-digit mobile phone number so our team can contact you?'\n"
                    f"🚨 CRITICAL MANDATORY: DO NOT show review summary until a valid 10-digit mobile phone number is provided!"
                )
            else:
                next_step_instruction = (
                    f"STEP 4 & 5 (DOCTOR GUIDANCE IN REGIONAL CITY + MANDATORY 10-DIGIT MOBILE NUMBER):\n"
                    f"The patient resides in '{ct}'.\n"
                    f"Explain warmly in {user_lang} that for {ct}, our clinic team will contact them and guide them to our nearest USD Certified specialist, and immediately ask for their 10-digit mobile number so our team can get in touch:\n"
                    f"• Gujarati: '{ct} માટે અમારી ક્લિનિક ટીમ તમારો સંપર્ક કરશે અને તમને અમારા નજીકના USD સર્ટિફાઇડ નિષ્ણાત ડૉક્ટર માટે સંપૂર્ણ માર્ગદર્શન આપશે. કૃપા કરીને તમારો 10 અંકનો મોબાઇલ નંબર જણાવશો જેથી અમારી ટીમ તમારો સંપર્ક કરી શકે?'\n"
                    f"• Hindi: '{ct} के लिए हमारी क्लिनिक टीम आपसे संपर्क करेगी और आपको हमारे नजदीकी USD सर्टिफाइड विशेषज्ञ के लिए पूरा मार्गदर्शन देगी। कृपया अपना 10 अंकों का मोबाइल नंबर बताएं ताकि हमारी टीम आपसे संपर्क कर सके?'\n"
                    f"• English: 'For {ct}, our clinic team will contact you and guide you to our nearest USD Certified specialist. Could you please provide your 10-digit mobile phone number so our team can contact you?'\n"
                    f"🚨 CRITICAL MANDATORY: DO NOT show review summary until a valid 10-digit mobile phone number is provided!"
                )
        else:
            is_asking_why_no_doctor = any(p in user_text.lower() for p in [
                "why didn't you add dentist", "why didn't you add doctor", "why no doctor", "why no dentist",
                "you didn't add dentist", "you didn't add doctor", "doctor name is missing", "doctor name missing",
                "dentist name missing", "doctor ka naam nahi", "doctor ka naam kyu nahi", "doctor name kyu nahi",
                "dentist ka naam nahi", "ડૉક્ટરનું નામ કેમ નથી", "ડોક્ટર નામ નથી લખ્યું", "ડેન્ટિસ્ટનું નામ નથી",
                "ડોક્ટરનું નામ કેમ ના", "ડૉક્ટરનું નામ કેમ ના", "doctor name kem nathi", "doctor name nathi lakhyu",
                "doctor name nathi", "dentist name nathi", "doctor missing", "dentist missing", "where is doctor"
            ])
            if is_asking_why_no_doctor:
                next_step_instruction = (
                    f"PATIENT INQUIRY ABOUT DENTIST NAME (MANDATORY PROFESSIONAL GUIDANCE DIRECTIVE):\n"
                    f"The patient asked why the dentist/doctor name was not added.\n"
                    f"Explain warmly and professionally in {user_lang} that when our team contacts them to confirm the appointment, they will guide them and at that time the patient can choose their preferred USD Certified Smile Designer, or our team will help match them with the right specialist!\n"
                    f"• Gujarati: 'જ્યારે અમારી ટીમ તમારી અપૉઇન્ટમેન્ટ કન્ફર્મ કરવા માટે સંપર્ક કરશે, ત્યારે તેઓ તમને સંપૂર્ણ માર્ગદર્શન આપશે. તે સમયે તમે તમારા મનપસંદ USD સર્ટિફાઇડ સ્માઇલ ડિઝાઇનર પસંદ કરી શકો છો, અથવા અમારી ટીમ તમારા માટે યોગ્ય નિષ્ણાત ડૉક્ટર સાથે કન્સલ્ટેશન નક્કી કરવામાં મદદ કરશે. શું હું આ વિગતો સાથે તમારી અપૉઇન્ટમેન્ટ સબમિટ કરું?'\n"
                    f"• Hindi: 'जब हमारी टीम आपकी अपॉइंटमेंट कन्फर्म करने के लिए आपसे संपर्क करेगी, तो वे आपको पूरा मार्गदर्शन देंगे। उस समय आप अपने पसंदीदा USD सर्टिफाइड स्माइल डिज़ाइनर का चयन कर सकते हैं, या हमारी टीम आपके लिए सही विशेषज्ञ चुनने में आपकी मदद करेगी। क्या मैं यह अपॉइंटमेंट सबमिट कर दूँ?'\n"
                    f"• English: 'When our team contacts you to confirm your appointment, they will guide you through the process. At that time, you can choose your preferred USD Certified Smile Designer, or our team will help match you with the right specialist for your consultation. Would you like to proceed and submit this appointment?'"
                )
            else:
                is_update = getattr(self.session, 'slot_just_updated', False)
                self.session.slot_just_updated = False
                self.session.asking_for_field = None
                next_step_instruction = get_review_summary_prompt(user_lang, display_name, ph, ct, cn, dr, is_update=is_update)

        active_memory += f"\n- STEP-BY-STEP ONE-QUESTION-AT-A-TIME DIRECTIVE:\n{next_step_instruction}\n(CRITICAL: Never re-ask details already confirmed. Ask ONLY the single missing step)."

        await self.send_json({
            "type": "sync_slots",
            "slots": self.session.booking_slots
        })

        # ⚡ Instant Fast-Path Submission when User Confirms Review Summary (Multilingual across all 11 Indian languages) ⚡
        def is_affirmative_submit(text):
            tl = text.lower().strip()
            tl = re.sub(r"[\s.,!?\\/]+$", "", tl)
            # Exact short affirmations
            if tl in [
                "submit", "yes", "yea", "yep", "yeah", "ok", "okay", "sure", "done", "please do", "confirm", "proceed",
                # Gujarati
                "હા", "હા કરી દો", "હા કરી દ્યો", "ચોક્કસ", "ભલે", "ઠીક છે", "હાજી", "કરી દ્યો", "કરી દો", "સબમિટ", "હા સબમિટ", "સબમિટ કરો", "સબમિટ કરી દો", "સબમિટ કરી દ્યો",
                # Hindi
                "हाँ", "हाँ कर दो", "कर दो", "अवश्य", "ज़रूर", "सबमिट", "हाँ सबमिट", "सबमिट करो", "सबमिट कर दीजिए", "सबमिट कर दो", "हाँजी",
                # Marathi
                "हो", "हो करा", "करा", "नक्की", "चालेल", "सबमिट", "सबमिट करा", "हो सबमिट करा",
                # Bengali
                "হ্যাঁ", "হ্যাঁ করুন", "করুন", "অবশ্যই", "সাবমিট", "সাবমিট করুন", "হ্যাঁ সাবমিট করুন",
                # Tamil
                "ஆம்", "சரி", "கண்டிப்பாக", "சமர்ப்பிக்கவும்", "சப்மிட்", "சப்மிட் பண்ணுங்க", "ஆம் சப்மிட் பண்ணுங்க",
                # Telugu
                "అవును", "సరే", "తప్పకుండా", "సమర్పించండి", "సబ్మిట్", "సబ్మిట్ చేయండి", "అవును సబ్మిట్ చేయండి",
                # Kannada
                "ಹೌದು", "ಸರಿ", "ಖಂಡಿತ", "ಸಲ್ಲಿಸಿ", "ಸಬ್ಮಿಟ್", "ಸಬ್ಮಿಟ್ ಮಾಡಿ", "ಹೌದು ಸಬ್ಮಿಟ್ ಮಾಡಿ",
                # Malayalam
                "അതെ", "ശരി", "തീർച്ചയായും", "സമർപ്പിക്കുക", "സബ്മിറ്റ്", "സബ്മിറ്റ് ചെയ്യുക", "അതെ സബ്മിറ്റ് ചെയ്യുക",
                # Punjabi
                "ਹਾਂ", "ਹਾਂਜੀ", "ਜ਼ਰੂਰ", "ਦਰਜ ਕਰੋ", "ਸਬਮਿਟ", "ਸਬਮਿਟ ਕਰੋ", "ਹਾਂ ਸਬਮਿਟ ਕਰੋ",
                # Odia
                "ହଁ", "ହଁ କରନ୍ତୁ", "ନିଶ୍ଚୟ", "ଦାଖଲ କରନ୍ତୁ", "ସବମିଟ୍", "ସବମିଟ୍ କରନ୍ତୁ", "ହଁ ସବମିଟ୍ କରନ୍ତୁ",
                # Transliterated
                "haan", "ha", "haa", "ha ji", "haan ji", "kar do", "kardo", "kari do", "kari dyo", "kar dyo", "haa kari dyo",
                "yes submit", "chalega", "thik chhe", "theek hai", "bhaley", "chokkas", "zarur", "zaroor", "submit karo", "submit kar do", "submit kari dyo", "submit madi", "submit pannunga", "submit cheyandi", "submit koro", "submit karantu"
            ]:
                return True
            # Check for words indicating an edit/change request
            edit_words = ["change", "update", "edit", "instead", "no my", "no, my", "spelling", "mistake"]
            if any(ew in tl for ew in edit_words):
                return False

            # Regex or substring match for phrases
            for phrase in [
                "submit", "confirm", "book", "kari dyo", "kari do", "kar do", "kardo", "submitt",
                "કરી દ્યો", "કરી દો", "સબમિટ", "કર દો", "कर दो", "सबमिट", "करा", "করুন", "சமர்ப்பிக்கவும்", "సమర్పించండి", "ಸಲ್ಲಿಸಿ", "സമർപ്പിക്കുക", "ਦਰਜ ਕਰੋ", "ଦାଖଲ କରନ୍ତୁ",
                "mari booking", "મારી બુકિંગ", "મારી અપૉઇન્ટમેન્ટ", "मेरी बुकिंग"
            ]:
                if phrase in tl:
                    return True
            return False

        def is_cancel_submit(text):
            # If user is asking to update or change something, it is NEVER a cancellation!
            if getattr(self.session, 'slot_just_updated', False) or getattr(self.session, 'asking_for_field', None):
                return False
            tl = text.lower().strip()
            tl = re.sub(r"[\s.,!?\\/]+$", "", tl)
            # If user text contains update/change keywords, never cancel
            if any(w in tl for w in ["change", "update", "badal", "badlo", "sudharo", "ferfar", "બદલો", "સુધારો", "અપડેટ", "ફેરફાર", "बदलो", "अपडेट", "सुधारो"]):
                return False

            # Check if negated (e.g. "don't cancel")
            if any(neg in tl for neg in ["don't cancel", "dont cancel", "not cancel", "cancel nathi", "cancel nahi", "cancel nahin", "કેન્સલ નથી", "કેન્સલ નહીં", "कैंसिल नहीं", "कैंसिल मत"]):
                return False

            # Match any cancellation keyword or phrase in English, Gujarati, Hindi, Hinglish
            cancel_keywords = [
                "cancel", "abort", "stop booking", "stop appointment",
                "કેન્સલ", "રદ", "કેન્સલ કરો", "રદ કરો", "કેન્સલ કરવી", "કેન્સલ કરવું", "રદ કરવી", "રદ કરવું",
                "कैंसिल", "रद्द", "कैंसिल करो", "रद्द करो", "कैंसिल करना", "रद्द करना",
                "cancel karvi", "cancel karvu", "cancel karo", "cancel kar do", "cancel kardo", "cancel karna",
                "cancel kari nakho", "cancel kari dyo", "cancel kari do", "nathi karvu"
            ]
            if any(kw in tl for kw in cancel_keywords):
                return True

            return False

        def is_explicit_submit_command(text):
            if not text:
                return False
            tl = text.lower().strip()
            tl = re.sub(r"[\s.,!?\\/]+$", "", tl)
            explicit_submit_words = [
                "submit", "summit", "submitt", "samit", "sabmit", "confirm", "proceed",
                "સબમિટ", "સબમિટ કરો", "સબમિટ કરી દો", "સબમિટ કરી દ્યો", "કન્ફર્મ", "કન્ફર્મ કરો",
                "सबमिट", "सबमिट करो", "सबमिट कर दीजिए", "सबमिट कर दो", "कन्फर्म", "कन्फर्म करो",
                "सबमिट करा", "हो सबमिट करा", "সাবমিট", "সাবমিট করুন", "சமர்ப்பிக்கவும்", "சப்மிட்",
                "సమర్పించండి", "సబ్మిట్", "ಸಲ್ಲಿಸಿ", "ಸಬ್ಮಿಟ್", "സമർപ്പിക്കുക", "സബ്മിറ്റ്",
                "ਦਰਜ ਕਰੋ", "ਸਬਮਿਟ", "ଦାਖਲ କରନ୍ତੁ", "ସବମିଟ୍",
                "submit karo", "submit kar do", "submit kari dyo", "submit madi", "submit pannunga", "submit cheyandi", "submit koro", "submit karantu",
                "book my appointment", "mari booking submit", "meri booking submit", "submit my appointment"
            ]
            if tl in explicit_submit_words:
                return True
            for phrase in ["submit", "સબમિટ", "सबमिट", "சமர்ப்பிக்கவும்", "సమర్పించండి", "ಸಲ್ಲಿಸಿ", "സമർപ്പിക്കുക", "ਦਰਜ ਕਰੋ", "ଦାਖਲ କରନ୍ତੁ", "mari booking", "મારી બુકિંગ", "મારી અપૉઇન્ટમેન્ટ", "मेरी बुकिंग"]:
                if phrase in tl:
                    return True
            return False

        user_txt_l = user_text.lower().strip()
        is_affirmative = is_affirmative_submit(user_text)
        is_explicit_submit = is_explicit_submit_command(user_text)
        is_cancel = is_cancel_submit(user_text)

        # ⚡ CRITICAL: When user says "submit" or confirms, ALWAYS extract all details directly from the last confirmation message ⚡
        confirmed_review_slots = dict(getattr(self.session, "last_review_summary_slots", {}) or {})
        last_rev_txt = getattr(self.session, "last_review_summary_text", "")
        if last_rev_txt and is_submit_review_summary(last_rev_txt):
            rev_s = extract_slots_from_review_summary(last_rev_txt)
            if rev_s:
                confirmed_review_slots.update(rev_s)

        if history and isinstance(history, list):
            for turn in reversed(history):
                if turn.get("role") in ["model", "assistant"]:
                    p_last = get_turn_text(turn)
                    if p_last and is_submit_review_summary(p_last):
                        sum_slots = extract_slots_from_review_summary(p_last)
                        if sum_slots:
                            confirmed_review_slots.update(sum_slots)
                            break

        if confirmed_review_slots:
            for k, v in confirmed_review_slots.items():
                if v and str(v).lower() not in ["none", "null", "-", "--"]:
                    self.session.booking_slots[k] = v
            if confirmed_review_slots.get("user_name"):
                self.session.user_name = confirmed_review_slots["user_name"]
            if confirmed_review_slots.get("user_concern") or confirmed_review_slots.get("message"):
                self.session.user_concern = confirmed_review_slots.get("user_concern") or confirmed_review_slots.get("message")

        # Resolve doctor to official certified name if needed
        if self.session.booking_slots.get("doctor_name"):
            try:
                from voice_agent.services.appointment_service import is_matched_doctor
                matched = is_matched_doctor(self.session.booking_slots["doctor_name"], city=self.session.booking_slots.get("city"))
                if not matched:
                    matched = is_matched_doctor(self.session.booking_slots["doctor_name"], city=None)
                if matched:
                    self.session.booking_slots["doctor_name"] = matched
                else:
                    self.session.booking_slots["doctor_name"] = ""
            except Exception:
                pass

        slots = self.session.booking_slots
        has_fn = bool(slots.get("first_name") and slots["first_name"].strip() and slots["first_name"].lower() not in ["", "none", "null", "patient", "user"])
        has_city = bool(slots.get("city") and len(str(slots["city"]).strip()) >= 2 and str(slots["city"]).lower() not in ["", "none", "null", "india"])
        has_doc = bool(slots.get("doctor_name") and slots["doctor_name"].strip() and slots["doctor_name"].lower() not in ["", "none", "null", "usd certified smile designer", "doctor", "dentist", "any", "not selected", "pending"])
        has_concern = bool(slots.get("message") and len(slots["message"].strip()) >= 3 and slots["message"].lower() not in ["none", "null", "dental consultation appointment request"])
        has_phone = bool(slots.get("phone") and len("".join(filter(str.isdigit, str(slots["phone"])))) == 10)

        all_slots_complete = has_fn and has_city and has_concern and has_phone
        is_already_submitted = bool(self.session.booking_slots.get("is_submitted") or self.session.booking_slots.get("submission_id"))

        has_rev_fn = bool(confirmed_review_slots.get("first_name") or confirmed_review_slots.get("user_name"))
        has_rev_ph = bool(confirmed_review_slots.get("phone") and len("".join(filter(str.isdigit, str(confirmed_review_slots["phone"])))) == 10)
        has_rev_city = bool(confirmed_review_slots.get("city"))
        has_rev_doc = bool(confirmed_review_slots.get("doctor_name"))
        has_rev_msg = bool(confirmed_review_slots.get("message") or confirmed_review_slots.get("user_concern"))
        is_full_review_ready = has_rev_fn and has_rev_ph and has_rev_city and has_rev_msg

        # If user explicitly requests submit but ANY mandatory field is missing -> NEVER submit, ask for missing field!
        if is_explicit_submit and not (all_slots_complete or is_full_review_ready):
            if not has_fn:
                missing_msg = get_missing_field_message(user_lang, "name")
            elif not has_concern:
                missing_msg = get_missing_field_message(user_lang, "concern")
            elif not has_city:
                missing_msg = get_missing_field_message(user_lang, "city")
            elif not has_phone:
                missing_msg = get_missing_field_message(user_lang, "phone")
            else:
                missing_msg = "Could you please confirm your appointment details before submission?"

            await self.send_json({
                "type": "bot_text_chunk",
                "text": missing_msg,
                "tag": None,
                "turnId": self.session.current_voice_turn_id
            })
            await self.send_json({
                "type": "bot_spoken_text",
                "text": missing_msg,
                "tag": None,
                "turnId": self.session.current_voice_turn_id
            })
            await self.send_json({
                "type": "reply_complete",
                "userText": user_text,
                "botText": missing_msg,
                "tag": None,
                "totalChunks": 1,
                "slots": dict(self.session.booking_slots),
                "userName": self.session.user_name,
                "userConcern": self.session.user_concern,
                "userCity": self.session.booking_slots.get("city"),
                "userDoctor": self.session.booking_slots.get("doctor_name"),
                "userPhone": self.session.booking_slots.get("phone")
            })
            return

        is_user_confirming_submit = False
        if is_cancel and (is_already_submitted or all_slots_complete):
            is_user_confirming_submit = True
        elif is_explicit_submit and (all_slots_complete or is_full_review_ready):
            is_user_confirming_submit = True
        elif is_affirmative and all_slots_complete and is_full_review_ready:
            is_user_confirming_submit = True

        if is_user_confirming_submit:
            action_type = "cancelling" if is_cancel else "submitting"
            
            submit_args = dict(self.session.booking_slots)
            # Ensure every field confirmed in review message is strictly used in payload
            if confirmed_review_slots:
                for k in ["first_name", "last_name", "phone", "city", "doctor_name", "message"]:
                    if confirmed_review_slots.get(k):
                        submit_args[k] = confirmed_review_slots[k]
                        self.session.booking_slots[k] = confirmed_review_slots[k]
            
            print(f"[INFO] Fast-path {action_type} appointment for {submit_args.get('first_name')} {submit_args.get('last_name')} in {submit_args.get('city')} with {submit_args.get('doctor_name')} (Phone: {submit_args.get('phone')})...")
            
            await self.send_json({
                "type": "status_update",
                "status": "submitting",
                "text": f"Riya is {action_type}..."
            })
            
            submit_args["is_cancel"] = is_cancel
            submit_args["is_update"] = bool(self.session.booking_slots.get("submission_id")) or bool(self.session.booking_slots.get("is_submitted"))
            submit_args["submission_id"] = self.session.booking_slots.get("submission_id")
            if self.session.booking_slots.get("godaddy_id"):
                submit_args["godaddy_id"] = self.session.booking_slots.get("godaddy_id")
            if self.session.booking_slots.get("api_id"):
                submit_args["api_id"] = self.session.booking_slots.get("api_id")

            # ⚡ Attach full conversation transcript to appointment lead email ⚡
            transcript_text = self._build_transcript_text()
            if transcript_text:
                submit_args["transcript"] = transcript_text
            
            res = await submit_consultation_appointment(submit_args)
            if res.get("status") == "success":
                self.session.booking_slots["is_submitted"] = True
                if is_cancel:
                    self.session.booking_slots["is_cancel"] = True
                if isinstance(res.get("details"), dict):
                    ret_id = res["details"].get("id") or res["details"].get("submission_id")
                    if ret_id:
                        self.session.booking_slots["submission_id"] = ret_id
                    if res["details"].get("godaddy_id"):
                        self.session.booking_slots["godaddy_id"] = res["details"]["godaddy_id"]
                    if res["details"].get("api_id"):
                        self.session.booking_slots["api_id"] = res["details"]["api_id"]
                
                await self.send_json({
                    "type": "sync_slots",
                    "slots": self.session.booking_slots
                })
            
            if is_cancel:
                cancel_msgs = {
                    "gu": "તમારી અપૉઇન્ટમેન્ટ રિક્વેસ્ટ કેન્સલ કરવામાં આવી છે. જો તમને બીજી કોઈ મદદ જોઈએ તો જણાવશો.",
                    "hi": "आपका अपॉइंटमेंट अनुरोध रद्द कर दिया गया है। अगर आपको किसी और मदद की आवश्यकता हो तो कृपया बताएं।",
                    "en": "Your appointment request has been cancelled. Please let me know if you need anything else."
                }
                confirm_msg = cancel_msgs.get(user_lang, cancel_msgs["en"])
            else:
                confirm_msg = CONFIRMATION_MESSAGES_11.get(user_lang, CONFIRMATION_MESSAGES_11["en"])

            await self.send_json({
                "type": "bot_text_chunk",
                "text": confirm_msg,
                "tag": None,
                "turnId": self.session.current_voice_turn_id
            })
            clean_text = confirm_msg
            full_text = confirm_msg
            await self.send_json({
                "type": "bot_spoken_text",
                "text": confirm_msg,
                "tag": None,
                "turnId": self.session.current_voice_turn_id
            })
            await self.send_json({
                "type": "reply_complete",
                "userText": user_text,
                "botText": confirm_msg,
                "tag": None,
                "totalChunks": 1,
                "slots": dict(self.session.booking_slots),
                "userName": self.session.user_name,
                "userConcern": self.session.user_concern,
                "userCity": self.session.booking_slots.get("city"),
                "userDoctor": self.session.booking_slots.get("doctor_name"),
                "userPhone": self.session.booking_slots.get("phone")
            })
            return

        full_system_prompt = system_prompt

        if active_memory:
            full_system_prompt += f"\n\n=========================================\nACTIVE PATIENT MEMORY (HIGH PRIORITY OVERRIDE):\n{active_memory}\n========================================="

        payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": full_system_prompt}]},
            "generationConfig": {
                "temperature": 0.25,
                "maxOutputTokens": 300
            },
            "tools": [APPOINTMENT_TOOL_DECLARATION]
        }
        
        full_text = ""
        api_keys = get_prioritized_api_keys()
        models = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-latest"]
        for key in api_keys:
            for model in models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse&key={key}"
                try:
                    async with _CHAT_HTTP_CLIENT.stream("POST", url, json=payload) as resp:
                        if resp.status_code == 200:
                            async for line in resp.aiter_lines():
                                if line.startswith("data: "):
                                    try:
                                        chunk_data = json.loads(line[6:])
                                        candidates = chunk_data.get("candidates", [])
                                        if candidates and "content" in candidates[0]:
                                            parts = candidates[0]["content"].get("parts", [])
                                            for p in parts:
                                                func_call = p.get("functionCall")
                                                if func_call and func_call.get("name") == "submit_appointment_booking":
                                                    if (is_user_confirming_submit or is_cancel) and (is_cancel or not self.session.booking_slots.get("is_submitted")):
                                                        submit_args = dict(self.session.booking_slots)
                                                        submit_args["is_cancel"] = is_cancel
                                                        submit_args["is_update"] = bool(self.session.booking_slots.get("submission_id")) or bool(self.session.booking_slots.get("is_submitted"))
                                                        submit_args["submission_id"] = self.session.booking_slots.get("submission_id")
                                                        if self.session.booking_slots.get("godaddy_id"):
                                                            submit_args["godaddy_id"] = self.session.booking_slots.get("godaddy_id")
                                                        if self.session.booking_slots.get("api_id"):
                                                            submit_args["api_id"] = self.session.booking_slots.get("api_id")
                                                        transcript_text = self._build_transcript_text()
                                                        if transcript_text:
                                                            submit_args["transcript"] = transcript_text
                                                        res = await submit_consultation_appointment(submit_args)
                                                        if res.get("status") == "success":
                                                            self.session.booking_slots["is_submitted"] = True
                                                            if is_cancel:
                                                                self.session.booking_slots["is_cancel"] = True
                                                            if isinstance(res.get("details"), dict):
                                                                ret_id = res["details"].get("id") or res["details"].get("submission_id")
                                                                if ret_id:
                                                                    self.session.booking_slots["submission_id"] = ret_id
                                                                if res["details"].get("godaddy_id"):
                                                                    self.session.booking_slots["godaddy_id"] = res["details"]["godaddy_id"]
                                                                if res["details"].get("api_id"):
                                                                    self.session.booking_slots["api_id"] = res["details"]["api_id"]
                                                            await self.send_json({
                                                                "type": "sync_slots",
                                                                "slots": self.session.booking_slots
                                                            })
                                                        print(f"[INFO] Gemini 3.5 SSE invoked submit_appointment_booking, result: {res}")
                                                    else:
                                                        print(f"[INFO] Ignoring premature SSE submit tool call because user did not say submit.")
                                                chunk_txt = p.get("text", "")
                                                if chunk_txt:
                                                    full_text += chunk_txt
                                                    best_tag = detect_best_tag(user_text, full_text)
                                                    await self.send_json({
                                                        "type": "bot_text_chunk",
                                                        "text": chunk_txt,
                                                        "tag": best_tag,
                                                        "turnId": self.session.current_voice_turn_id
                                                    })
                                    except Exception:
                                        pass
                            if full_text:
                                break
                        else:
                            if resp.status_code == 429:
                                mark_key_rate_limited(key)
                            print(f"[WARN] Chat stream API model {model} status {resp.status_code} with key ...{key[-6:]}, trying fallback...")
                except Exception as e:
                    print(f"[WARN] Chat stream error with model {model} and key ...{key[-6:]}: {e}")
            if full_text:
                break
            
        if not full_text:
            if not self.session.booking_slots.get("first_name"):
                full_text = "May I know your full name?"
            elif not self.session.booking_slots.get("city"):
                full_text = "Which city are you located in so I can check for our closest USD Certified Smile Designer?"
            elif not self.session.booking_slots.get("message"):
                full_text = "What dental concern or smile improvement would you like to discuss?"
            elif not self.session.booking_slots.get("doctor_name"):
                full_text = f"Which USD Certified Smile Designer would you like to consult with in {patient_city or 'your city'}?"
            elif not self.session.booking_slots.get("phone"):
                full_text = "Could you please provide your 10-digit mobile phone number?"
            else:
                full_text = "Thank you! Shall I submit this appointment request to our team now?"
            await self.send_json({
                "type": "bot_text_chunk",
                "text": full_text,
                "tag": None,
                "turnId": self.session.current_voice_turn_id
            })

        clean_text = clean_assistant_text(full_text)

        # ⚡ CRITICAL: Extract and synchronize slots directly from Riya's review/confirmation message ⚡
        if is_submit_review_summary(clean_text or full_text):
            summary_slots = extract_slots_from_review_summary(clean_text or full_text)
            if summary_slots:
                # Guard against model hallucinating a doctor in the review summary when user never picked one
                if summary_slots.get("doctor_name"):
                    doc_in_summary = summary_slots["doctor_name"]
                    user_actually_picked_doc = bool(
                        self.session.booking_slots.get("doctor_name") and 
                        self.session.booking_slots.get("doctor_name") != "-"
                    )
                    if not user_actually_picked_doc:
                        user_picked_now = find_doctor_in_text(user_text, self.session.booking_slots.get("city"))
                        if user_picked_now:
                            user_actually_picked_doc = True
                            self.session.booking_slots["doctor_name"] = user_picked_now

                    if not user_actually_picked_doc:
                        print(f"[WARN] Discarding model hallucinated doctor '{doc_in_summary}' from review summary!")
                        summary_slots.pop("doctor_name", None)
                        self.session.booking_slots["doctor_name"] = ""
                        cur_city = self.session.booking_slots.get("city") or "your city"
                        user_lang = detect_user_language(user_text, history)
                        missing_msg = get_missing_field_message(user_lang, "doctor", city=cur_city)
                        clean_text = missing_msg
                        full_text = missing_msg

                if summary_slots:
                    print(f"[INFO] Synchronizing slots from Riya's review summary: {summary_slots}")
                    self.session.last_review_summary_slots = dict(summary_slots)
                    self.session.last_review_summary_text = clean_text or full_text
                    for k, v in summary_slots.items():
                        if v and str(v).lower() not in ["none", "null", "-", "--"]:
                            self.session.booking_slots[k] = v
                    if summary_slots.get("user_name"):
                        self.session.user_name = summary_slots["user_name"]
                        p_n = summary_slots["user_name"].split()
                        self.session.booking_slots["first_name"] = p_n[0]
                        self.session.booking_slots["last_name"] = " ".join(p_n[1:]) if len(p_n) > 1 else "-"
                    if summary_slots.get("user_concern") or summary_slots.get("message"):
                        self.session.user_concern = summary_slots.get("user_concern") or summary_slots.get("message")
                        self.session.booking_slots["message"] = self.session.user_concern
                    await self.send_json({
                        "type": "sync_slots",
                        "slots": self.session.booking_slots
                    })

        final_tag, new_pending = detect_best_tag_with_fallback(
            user_text, clean_text or "...", getattr(self.session, 'pending_action_tag', None)
        )
        self.session.pending_action_tag = new_pending

        await self.send_json({
            "type": "bot_spoken_text",
            "text": clean_text or full_text,
            "tag": final_tag,
            "turnId": self.session.current_voice_turn_id,
            "slots": dict(self.session.booking_slots),
            "userName": self.session.user_name,
            "userConcern": self.session.user_concern,
            "userCity": self.session.booking_slots.get("city"),
            "userDoctor": self.session.booking_slots.get("doctor_name"),
            "userPhone": self.session.booking_slots.get("phone")
        })
        log_live_conversation("Chat Mode", user_text, clean_text or full_text, dict(self.session.booking_slots))
        await self.send_json({
            "type": "reply_complete",
            "userText": user_text,
            "botText": clean_text or full_text,
            "tag": final_tag,
            "totalChunks": 1,
            "slots": dict(self.session.booking_slots),
            "userName": self.session.user_name,
            "userConcern": self.session.user_concern,
            "userCity": self.session.booking_slots.get("city"),
            "userDoctor": self.session.booking_slots.get("doctor_name"),
            "userPhone": self.session.booking_slots.get("phone")
        })

    async def handle_client_json(self, data, system_prompt):
        msg_type = data.get("type")

        if msg_type == 'heartbeat':
            self.session.reset_activity_timer()
            return
        
        self.session.reset_activity_timer()
        
        if msg_type == 'start_of_speech':
            self.session.vad_state.is_speaking = True
            await self.send_json({"type": "user_speaking_status", "is_speaking": True})
            self.session.current_voice_turn_id += 1
            self.session.current_user_pcm_chunks = []
            self.session.last_sent_voice_transcript_turn_id = -1
            self.session.is_interrupted = False
            self.session.chunk_index = 0
            self.session.display_str = ""
            self.session.full_bot_reply = ""
            self.session.live_pcm_buffer = bytearray()
            self.session.assistant_audio_buffer = bytearray()
            self.session.current_user_transcription = ""
            self.session.user_transcription_task = None
            return

        if msg_type == 'text_input':
            self.session.current_voice_turn_id += 1
            self.session.latest_typed_user_text = data.get("text", "")
            self.session.latest_client_history = data.get("history", [])
            self.session.latest_client_is_voice_mode = data.get("isVoiceMode") != False
            
            # If starting a fresh call, reset all previous memory cleanly
            if "SYSTEM INSTRUCTION: Start the conversation" in self.session.latest_typed_user_text:
                self.session.gemini_resumption_handle = None
                self.session.user_name = ""
                self.session.user_concern = ""
                self.session.booking_slots = {
                    "first_name": "", "last_name": "", "email": "--",
                    "phone": "", "city": "", "message": "", "doctor_name": "",
                    "is_booking_active": False, "is_submitted": False
                }
            
            self.update_session_memory(self.session.latest_typed_user_text, self.session.latest_client_history, data)
            
            user_text = self.session.latest_typed_user_text or "Hello"
            self.session.is_interrupted = False
            self.session.chunk_index = 0
            self.session.display_str = ""
            self.session.full_bot_reply = ""
            self.session.live_pcm_buffer = bytearray()
            self.session.assistant_audio_buffer = bytearray()
            
            # In Chat Mode: Stream instantly via Gemini 3.5 Flash Lite for sub-second UI response
            if not self.session.latest_client_is_voice_mode:
                asyncio.create_task(self.stream_chat_text_response(user_text, self.session.latest_client_history, system_prompt))
                return

            # In Voice Mode: Wait for setupComplete before sending turn to persistent Gemini Live WebSocket
            try:
                await asyncio.wait_for(self.session.setup_complete_event.wait(), timeout=4.0)
            except asyncio.TimeoutError:
                pass

            if self.session.gemini_ws:
                try:
                    active_mem_lines = []
                    if self.session.user_name:
                        active_mem_lines.append(f"- Confirmed Patient Name: {self.session.user_name}")
                    if self.session.booking_slots.get("city"):
                        active_mem_lines.append(f"- Confirmed City: {self.session.booking_slots.get('city')}")
                    if self.session.booking_slots.get("phone"):
                        active_mem_lines.append(f"- Confirmed 10-digit Phone: {self.session.booking_slots.get('phone')}")
                    if self.session.booking_slots.get("doctor_name"):
                        active_mem_lines.append(f"- Confirmed Doctor: {self.session.booking_slots.get('doctor_name')}")
                    if self.session.user_concern:
                        active_mem_lines.append(f"- Confirmed Dental Concern: {self.session.user_concern}")
                    if self.session.booking_slots.get("is_submitted"):
                        active_mem_lines.append("- Appointment Status: ALREADY SUBMITTED to clinic team (Do NOT re-ask for booking details)")

                    if active_mem_lines:
                        user_payload_text = "SYSTEM UPDATE [ACTIVE PATIENT MEMORY - HIGH PRIORITY OVERRIDE]:\n" + "\n".join(active_mem_lines) + "\n\n" + user_text
                    else:
                        user_payload_text = user_text

                    await self.session.gemini_ws.send(json.dumps({
                        "realtimeInput": {
                            "text": user_payload_text
                        }
                    }))
                    self.session.initial_greeting_sent = True
                except Exception as e:
                    print(f"Failed to send text turn to Gemini Live: {e}")
        
        elif msg_type == 'process_final':
            self.session.vad_state.is_speaking = False
            self.session.latest_client_history = data.get("history", [])
            self.session.latest_client_is_voice_mode = data.get("isVoiceMode") != False
            
            turn_id_for_this_speech = self.session.current_voice_turn_id
            pcm_buffer = b"".join(self.session.current_user_pcm_chunks) if self.session.current_user_pcm_chunks else b""
            self.session.current_user_pcm_chunks = []
            self.session.is_interrupted = False
            
            # Extract client transcription (strictly for frontend UI chat bubble display)
            native_text = clean_hallucinations(data.get("nativeTranscript", "").strip())
            if not native_text:
                native_text = clean_hallucinations(self.session.current_user_transcription.strip())
                
            # Background transcription for the browser UI chat bubble subtitles only
            if native_text:
                self.session.current_user_transcription = native_text
                self.update_session_memory(native_text, self.session.latest_client_history)
                fut = asyncio.Future()
                fut.set_result(native_text)
                self.session.user_transcription_task = fut
                await self.maybe_send_voice_transcript(turn_id_for_this_speech, native_text)
            elif pcm_buffer:
                self.session.user_transcription_task = asyncio.create_task(
                    self.transcribe_user_audio_async(pcm_buffer, turn_id_for_this_speech)
                )
        
        elif msg_type == 'start_of_speech':
            self.session.vad_state.is_speaking = True
            self.session.current_voice_turn_id += 1
            self.session.current_user_pcm_chunks = []
            self.session.last_sent_voice_transcript_turn_id = -1
            self.session.is_interrupted = False
            self.session.chunk_index = 0
            self.session.display_str = ""
            self.session.full_bot_reply = ""
            self.session.live_pcm_buffer = bytearray()
            self.session.assistant_audio_buffer = bytearray()
            self.session.current_user_transcription = ""
            self.session.user_transcription_task = None

    async def transcribe_user_audio_async(self, pcm_bytes, turn_id):
        try:
            lang = self.session.current_language or 'hi-IN'
            raw_text = await transcribe_voice_data(pcm_bytes, 16000, lang)
            text = clean_hallucinations(raw_text).strip()
            self.session.current_user_transcription = text
            if text:
                self.update_session_memory(text, self.session.latest_client_history)
            await self.maybe_send_voice_transcript(turn_id, text)
            return text
        except Exception as e:
            print(f"User transcription error: {e}")
            return ""

    async def maybe_send_voice_transcript(self, turn_id, text):
        if not text:
            return
        if turn_id == self.session.last_sent_voice_transcript_turn_id:
            return
        self.session.last_sent_voice_transcript_turn_id = turn_id
        await self.send_json({
            "type": "user_spoken_text",
            "text": text,
            "slots": dict(self.session.booking_slots),
            "userName": self.session.user_name,
            "userConcern": self.session.user_concern,
            "userCity": self.session.booking_slots.get("city"),
            "userDoctor": self.session.booking_slots.get("doctor_name"),
            "userPhone": self.session.booking_slots.get("phone")
        })

    async def transcribe_and_sync_bot_text(self, audio_bytes):
        try:
            user_text = ""
            if self.session.user_transcription_task:
                try:
                    user_text = await self.session.user_transcription_task
                except Exception:
                    pass
            if not user_text:
                user_text = self.session.current_user_transcription or "Voice Message"
                
            if user_text and user_text != "Voice Message":
                self.update_session_memory(user_text, self.session.latest_client_history)

            lang = self.session.current_language or 'en-IN'
            bot_text = await transcribe_voice_data(audio_bytes, 24000, language_code=lang)
            if not bot_text:
                bot_text = "(Voice message played)"
            clean_text = clean_assistant_text(bot_text)
            best_tag = detect_best_tag(user_text, clean_text)
            
            # Synchronize any review summary slots spoken by the bot in Voice Mode
            summary_slots = extract_slots_from_review_summary(clean_text or bot_text)
            if summary_slots:
                for k, v in summary_slots.items():
                    if v and str(v).lower() not in ["none", "null", "-", "--"]:
                        self.session.booking_slots[k] = v
                if summary_slots.get("user_name"):
                    self.session.user_name = summary_slots["user_name"]
                if summary_slots.get("user_concern") or summary_slots.get("message"):
                    self.session.user_concern = summary_slots.get("user_concern") or summary_slots.get("message")
            
            await self.send_json({
                "type": "bot_spoken_text",
                "text": clean_text,
                "tag": best_tag,
                "slots": dict(self.session.booking_slots),
                "userName": self.session.user_name,
                "userConcern": self.session.user_concern,
                "userCity": self.session.booking_slots.get("city"),
                "userDoctor": self.session.booking_slots.get("doctor_name"),
                "userPhone": self.session.booking_slots.get("phone")
            })
        except Exception as e:
            await self.send_json({
                "type": "bot_spoken_text",
                "text": "(Voice message played)",
                "slots": dict(self.session.booking_slots),
                "userName": self.session.user_name,
                "userConcern": self.session.user_concern,
                "userCity": self.session.booking_slots.get("city"),
                "userDoctor": self.session.booking_slots.get("doctor_name"),
                "userPhone": self.session.booking_slots.get("phone")
            })

    async def inactivity_monitor_loop(self, close_ws_callback):
        while self.session.is_client_connected:
            try:
                now = asyncio.get_event_loop().time()
                elapsed = now - self.session.last_activity_time
                is_voice = getattr(self.session, 'latest_client_is_voice_mode', True)
                current_timeout = 180 if is_voice else 240
                if elapsed >= current_timeout:
                    print("⏳ Inactivity timeout reached (180s). Disconnecting client...")
                    await self.send_json({"type": "error", "error": "Session timed out due to inactivity."})
                    await close_ws_callback()
                    break
                
                # Sleep for the remaining time or a minimum of 1 second
                sleep_time = max(1.0, current_timeout - elapsed)
                await asyncio.sleep(sleep_time)
            except Exception as e:
                print(f"Error in inactivity monitor: {e}")
                break
