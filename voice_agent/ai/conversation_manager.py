def log_live_conversation(mode, user_text, bot_text, slots):
    import sys
    fn = slots.get('first_name') or '-'
    ln = slots.get('last_name') or '-'
    name_str = f"{fn} {ln}".strip() if ln != '-' else fn
    city_str = slots.get('city') or '-'
    pin_str = slots.get('pincode') or '-'
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
        f"📋 SLOTS: Name: {name_str} | City: {city_str} | Pincode: {pin_str} | Doctor: {doc_str} | Concern: {msg_str} | Phone: {phone_str} | Submitted: {sub_str}\n"
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
import time
import re
import json
import base64
import asyncio
import httpx
from typing import Optional, List, Dict, Tuple, Any
from voice_agent.utils.constants import INACTIVITY_TIMEOUT
from voice_agent.utils.helpers import clean_assistant_text, clean_hallucinations, extract_slots_from_review_summary, is_submit_review_summary, transliterate_to_english, strip_diacritics, ALL_CERTIFIED_DOCTORS_LIST, DOCTOR_HOME_CITIES, MULTILINGUAL_CITY_MAP, is_cancel_submit, is_explicit_submit_command, is_affirmative_submit, is_cancel_response_text, is_submit_response_text, _norm_phon
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
    "Jaipur", "Udaipur", "Kolkata", "Vijayawada", "Visakhapatnam", "Nellore", "Hubli", "Aurangabad", "Jhansi", "Mathura",
    "Gangtok", "Namchi", "Singtam", "Pakyong", "Siliguri", "Darjeeling", "Kalimpong"
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
    # Question words & typos (never city names)
    "what", "whta", "wat", "wht", "waht", "wot", "wha", "why", "whyy", "wai", "how", "howw", "when", "wen", "where", "wear", "were", "who", "which", "wich",
    "wait", "hold", "stop", "pause", "sorry", "pardon", "repeat", "again", "didnt hear", "cant hear",
    "huh", "hmm", "hmmm", "um", "umm", "uh", "uhh", "er", "ah", "ahh", "oho", "oh",
    # Common professions & nouns & query words
    "lawyer", "advocate", "vakeel", "vakil", "engineer", "teacher", "patient", "user",
    "apple", "today", "tomorrow", "now", "later", "please", "thanks", "thank",
    "give", "list", "options", "option", "show", "tell", "details", "detail", "more", "other", "all", "hear", "listen", "see", "view", "know", "check", "need", "want",
    # Gujarati transliterated
    "chhe", "che", "chu", "chhu", "chiye", "nathi", "maru", "tamaru", "mari", "tamari", "maro", "tamaro",
    "mare", "tamare", "tame", "hu", "pan", "se", "ma", "maa", "me", "mein", "thi", "na", "no", "ne",
    "kaya", "kayo", "kayi", "su", "shu", "kem", "barabar", "sachu", "khotu", "aaje", "kaale", "bhai",
    "saher", "shahar", "gaam", "nagar", "bol", "bolo", "samjhao", "samjhavo", "samjhya",
    # Hindi transliterated
    "hai", "hain", "hoon", "hun", "ho", "nahi", "nahin", "mera", "meri", "mere", "aapka", "aapki", "aapke",
    "mujhe", "kripya", "theek", "batao", "kardo", "karna", "chahiye", "sakte", "sakta", "kya", "kyu", "kyun",
    "kaise", "kahan", "kaha", "hoga", "hogi", "accha", "sahi", "aaj", "kal", "ka", "ki", "ke", "ko",
    "suno", "sun", "samjho", "samjhao",
    # Indic script
    "ઇસ", "છે", "છુ", "છીએ", "હું", "તમે", "મારે", "તમારે", "મારું", "તમારું", "નથી", "હા", "ના", "પણ", "તો",
    "દાંત", "સ્માઇલ", "ડૉક્ટર", "ડેન્ટિસ્ટ", "લોયર", "વકીલ", "આજે", "કાલે", "શહેર", "નામ", "ફોન", "નંબર",
    "સબમિટ", "કેન્સલ", "અપડેટ", "શું", "કેમ", "ક્યાં", "ક્યારે",
    "है", "हैं", "हूँ", "हो", "इज", "नहीं", "हाँ", "ना", "कौन", "क्या", "कैसे", "कहाँ", "क्यों", "कब", "दाँत", "दांत",
    "स्माइल", "डॉक्टर", "डेंटिस्ट", "वकील", "आज", "कल", "नाम", "शहर", "फोन", "नंबर", "सबमिट", "कैंसिल", "अपडेट"
}

def is_city_negated_in_text(city_term, full_text):
    if not city_term or not full_text:
        return False
    import re
    tl = str(full_text).lower()
    ct = str(city_term).lower().strip()
    if not ct:
        return False
    # Pre-negation (English, Hindi, Gujarati): 'not Sangli', 'no Sangli', 'nahi Sangli', 'nathi Sangli'
    pre = rf'\b(?:not|no|never|nahi|nathi|na|na\s+ki|na\s+ke)\s+{re.escape(ct)}\b'
    # Post-negation (Hindi/Gujarati: 'Sangli nahi', 'Sangli nathi', 'Sangli na')
    post = rf'\b{re.escape(ct)}\s+(?:nahi|nathi|nhi|na)\b'
    return bool(re.search(pre, tl) or re.search(post, tl))


def extract_city_from_text(text_to_search, asking_for_city=False):
    if not text_to_search:
        return None
    import re
    tl = text_to_search.lower().strip()
    
    # 1. Location explicit phrases ("i live in X", "living in X", "staying in X", "i am from X", "i m from X", "mari city X", "mera shahar X")
    m_loc = re.search(r"\b(?:i live in|i stay in|i am from|i m from|im from|living in|staying in|reside in|from)\s+([A-Za-z\u0A80-\u0AFF\u0900-\u097F]{3,30})", text_to_search, re.IGNORECASE)
    if not m_loc:
        m_loc = re.search(r"\b([A-Za-z\u0A80-\u0AFF\u0900-\u097F]{3,30})\s*(?:thi\s+chu|thi\s+chhu|ma\s+rahu\s+chu|me\s+rehta\s+hu|me\s+rehti\s+hu)\b", text_to_search, re.IGNORECASE)
    if not m_loc:
        m_loc = re.search(r"\b(?:my city is|mari city|maru saher|maru shaher|mera shahar|mera sahar)\s*[:=\-]?\s*([A-Za-z\u0A80-\u0AFF\u0900-\u097F]{3,30})", text_to_search, re.IGNORECASE)
    if m_loc:
        cand_c = m_loc.group(1).strip()
        if cand_c.lower() not in INVALID_CITY_WORDS and len(cand_c) >= 3 and not is_city_negated_in_text(cand_c, text_to_search):
            cand_l = cand_c.lower()
            if cand_l in MULTILINGUAL_CITY_MAP:
                return MULTILINGUAL_CITY_MAP[cand_l]
            for cert in CERTIFIED_CITIES:
                if cert.lower() == cand_l:
                    return cert
            from voice_agent.services.appointment_service import transliterate_to_english
            clean_c = transliterate_to_english(cand_c).title() if any(ord(c) > 127 for c in cand_c) else cand_c.title()
            if clean_c.lower() not in INVALID_CITY_WORDS:
                return clean_c

    # 2. Exact or word-boundary match in multilingual map (excluding negated mentions)
    for k, standard_name in MULTILINGUAL_CITY_MAP.items():
        if (k in text_to_search or (k.isascii() and re.search(r"\b" + re.escape(k) + r"\b", tl))) and not is_city_negated_in_text(k, text_to_search):
            return standard_name
            
    # 3. Check CERTIFIED_CITIES list (excluding negated mentions)
    for city in CERTIFIED_CITIES:
        if re.search(r"\b" + re.escape(city) + r"\b", tl, re.IGNORECASE) and not is_city_negated_in_text(city, text_to_search):
            return city

    # 4. Check UNSUPPORTED / Regional residence cities list (excluding negated mentions)
    for city in UNSUPPORTED_CITIES:
        if re.search(r"\b" + re.escape(city) + r"\b", tl, re.IGNORECASE) and not is_city_negated_in_text(city, text_to_search):
            return city.capitalize()

    # 4.5. Fuzzy / close spelling match against known cities (e.g. "heydrabad" -> "Hyderabad", "ahemdabad" -> "Ahmedabad")
    import difflib
    raw_words = re.findall(r"[A-Za-z\u0A80-\u0AFF\u0900-\u097F]+", text_to_search)
    clean_words = [w.lower() for w in raw_words if w.lower() not in INVALID_CITY_WORDS and len(w) >= 3 and not is_city_negated_in_text(w, text_to_search)]
    ascii_city_keys = [k for k in MULTILINGUAL_CITY_MAP.keys() if k.isascii() and len(k) >= 4]
    for w in clean_words:
        c_matches = difflib.get_close_matches(w, ascii_city_keys, n=1, cutoff=0.75)
        if c_matches:
            return MULTILINGUAL_CITY_MAP[c_matches[0]]
        c_cert = difflib.get_close_matches(w, [c.lower() for c in CERTIFIED_CITIES if len(c) >= 4], n=1, cutoff=0.75)
        if c_cert:
            return c_cert[0].title()

    # 5. Bare city response if asking_for_city is active
    if asking_for_city:
        # 🚨 Question words, typos, confusion, hesitation or negative phrases are NEVER cities!
        q_confusion_pattern = r"(?:\?|\b(?:what|whta|wat|wht|waht|wot|wha|wut|why|whyy|how|howw|when|wen|where|wear|who|which|wich|kya|kyu|kyun|kaise|kahan|kaha|kab|kaun|konsa|shu|su|kem|kaya|kayo|kayi|kon|kone|sorry|pardon|repeat|again|wait|hold|pause|stop|listen|suno|sambhalo|bolo|bolie|batao|kaho|help|agent|dont\s+know|don't\s+know|nahi\s+pata|nathi\s+khabar|no\s+idea|not\s+sure)\b)"
        if re.search(q_confusion_pattern, tl):
            return None

        cand = text_to_search.strip()
        cand = re.sub(r"[।.,!?:;\-–—/\\(){}\[\]\"'|`~]+", " ", cand).strip()
        parts = cand.split()
        if 1 <= len(parts) <= 4:
            # Filter filler words and purely numeric tokens (pincodes/phone numbers)
            non_fillers = [
                p for p in parts 
                if p.lower() not in INVALID_CITY_WORDS 
                and p.lower() not in ["order", "in", "a", "city", "place"] 
                and not is_city_negated_in_text(p, text_to_search)
                and not re.search(r"^\d+$", p)
            ]
            if non_fillers:
                target_cand = " ".join(non_fillers).strip()
                if (
                    len(target_cand) >= 3 
                    and not is_city_negated_in_text(target_cand, text_to_search)
                    and not re.search(r"\d{3,}", target_cand)
                    and re.search(r"[A-Za-z\u0A80-\u0AFF\u0900-\u097F]", target_cand)
                    and not re.search(q_confusion_pattern, target_cand.lower())
                ):
                    c_matches = difflib.get_close_matches(target_cand.lower(), ascii_city_keys, n=1, cutoff=0.75)
                    if c_matches:
                        return MULTILINGUAL_CITY_MAP[c_matches[0]]
                    from voice_agent.services.appointment_service import transliterate_to_english
                    clean_c = transliterate_to_english(target_cand).title() if any(ord(c) > 127 for c in target_cand) else target_cand.title()
                    if clean_c.lower() not in INVALID_CITY_WORDS:
                        return clean_c
            
    return None

def extract_certified_city_from_text(text_to_search):
    return extract_city_from_text(text_to_search, asking_for_city=False)


def extract_travel_destination_request(text_to_search: str) -> Optional[str]:
    """
    Detects if user expresses intent to book an appointment, visit, or inquire about a doctor/dentist/clinic in another city.
    E.g. 'but i want to book appointment in surat', 'appointment in surat', 'doctor in surat',
    'surat ma appointment levi che', 'surat mein appointment chahiye',
    'Mumbai mein dentist kaun hai?', 'મને મુંબઈના ડેન્ટિસ્ટના નામ જણાવો ને',
    'who is the dentist in mumbai', 'mumbai doctors', 'dentist in mumbai', etc.
    """
    if not text_to_search:
        return None
    import re
    tl = text_to_search.lower().strip()
    patterns = [
        # Explicit English/Hinglish travel booking or inquiry: "appointment in X", "doctor in X", "dentist in X", "who is dentist in X", "names of dentists in X"
        r"(?:want\s+(?:to\s+)?(?:book|take|get|have|consult|consultant|see)\s+(?:an?\s+)?(?:appointment\s+in|consultation\s+in|in)?|appointment\s+(?:in|for|at)|doctor\s+(?:in|for|at)|dentist\s+(?:in|for|at)|clinic\s+(?:in|for|at)|visit\s+(?:to|in|at)|(?:consult|consultant|consultation)\s+in|book\s+(?:appointment\s+)?in|who\s+is\s+(?:the\s+)?(?:dentist|doctor)\s+in|names?\s+of\s+(?:the\s+)?(?:dentist|doctor)s?\s+in|dentists?\s+in)\s+([a-zA-Z\u0A80-\u0AFF\u0900-\u097F]+)",
        # Hindi/Gujarati postfix: "mumbai mein dentist", "mumbai ma doctor", "mumbai mein kaun hai", etc.
        r"\b([a-zA-Z\u0A80-\u0AFF\u0900-\u097F]+?)\s*(?:ma\s+appointment|ma\s+doctor|ma\s+dentist|ma\s+clinic|ma\s+kon|mein\s+appointment|me\s+appointment|mein\s+doctor|me\s+doctor|mein\s+dentist|me\s+dentist|mein\s+kaun|me\s+kaun|mein\s+clinic|me\s+clinic|ma\s+j\s+javu)",
        # Gujarati "મુંબઈના ડેન્ટિસ્ટ", "અમદાવાદના ડૉક્ટર", "મુંબઈના નામ" (city + na/naa/no/ni + dentist/doctor/naam)
        r"\b([a-zA-Z\u0A80-\u0AFF\u0900-\u097F]+?)(?:na|naa|no|ni|ના|નો|ની)\s*(?:dentist|doctor|daant|clinic|naam|દાંત|ડેન્ટિસ્ટ|ડૉક્ટર|દવાખાનું|નામ)",
        # Hindi "मुंबई के डेंटિસ્ટ", "मुंबई के डॉक्टर", "मुंबई के नाम" (city + ke/ki + dentist/doctor/naam)
        r"\b([a-zA-Z\u0A80-\u0AFF\u0900-\u097F]+?)\s*(?:ke|ki|કે|કી|के|की)\s*(?:dentist|doctor|clinic|naam|डेंटિસ્ટ|ડોક્ટર|डॉक्टर|दवाखाना|नाम)",
        # Inverted "dentist in <city>", "doctor in <city>"
        r"(?:dentist|dentists|doctor|doctors|clinic|appointment|consultation|દાંતના ડૉક્ટર|ડેન્ટિસ્ટ|ડૉક્ટર|डेंटિસ્ટ|डॉक्टर)\s+(?:in|at|of|for|નાં?|મેં?)\s+([a-zA-Z\u0A80-\u0AFF\u0900-\u097F]+)",
        # Pure "<city> doctors" or "<city> dentists"
        r"\b([a-zA-Z\u0A80-\u0AFF\u0900-\u097F]+?)\s+(?:doctors?|dentists?|clinics?)\b"
    ]
    for pat in patterns:
        m = re.search(pat, tl, re.IGNORECASE)
        if m:
            cand = m.group(1).strip()
            city = extract_city_from_text(cand, asking_for_city=True)
            if city:
                return city
    return None

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
    "દીપિકા": "Dr. Deepika Dalal", "દીપિકા દલાલ": "Dr. Deepika Dalal", "દિપિકા": "Dr. Deepika Dalal", "दीपिका": "Dr. Deepika Dalal", "deepika": "Dr. Deepika Dalal", "deepika dalal": "Dr. Deepika Dalal", "dalal": "Dr. Deepika Dalal", "દલાલ": "Dr. Deepika Dalal", "deepika lal": "Dr. Deepika Dalal", "દીપિકા લાલ": "Dr. Deepika Dalal", "दीपिका लाल": "Dr. Deepika Dalal", "dipika lal": "Dr. Deepika Dalal", "dipika dalal": "Dr. Deepika Dalal", "dipika": "Dr. Deepika Dalal",
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
    "પ્રસન્ન": "Dr. Prasanna Patel", "પ્રસન્ના": "Dr. Prasanna Patel", "prasanna": "Dr. Prasanna Patel", "prasana": "Dr. Prasanna Patel", "prassana": "Dr. Prasanna Patel", "dr prasana": "Dr. Prasanna Patel", "dr prassana": "Dr. Prasanna Patel", "dr prasanna": "Dr. Prasanna Patel", "प्रसन्न": "Dr. Prasanna Patel", "प्रसन्ना": "Dr. Prasanna Patel",
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

    # 2. Check total digits in text (still must be a real Indian mobile: starts with 6-9)
    from voice_agent.utils.helpers import is_valid_indian_mobile
    digits = "".join(filter(str.isdigit, s))
    candidate = None
    if len(digits) == 10:
        candidate = digits
    elif len(digits) == 11 and digits.startswith("0"):
        candidate = digits[1:]
    elif len(digits) == 12 and digits.startswith("91"):
        candidate = digits[2:]
    return candidate if candidate and is_valid_indian_mobile(candidate) else None

def extract_valid_pincode(text_str, phone=None):
    if not text_str:
        return None
    import re
    s = str(text_str)
    # Match standard 6-digit Indian PIN code starting with 1-9
    matches = re.findall(r"\b([1-9][0-9]{5})\b", s)
    if matches:
        phone_digits = "".join(filter(str.isdigit, str(phone or "")))
        for m in matches:
            if not phone_digits or m not in phone_digits:
                return m
    # Check if total digits in string is exactly 6 and starts with 1-9
    digits = "".join(filter(str.isdigit, s))
    if len(digits) == 6 and digits[0] in "123456789":
        return digits
    return None

def is_asking_for_dentist_names(text: str) -> bool:
    if not text:
        return False
    tl = text.lower().strip()
    patterns = [
        "who is doctor", "who is dentist", "who are the doctors", "tell me dentist name",
        "give me dentist name", "which doctor", "names of dentists", "list of doctors",
        "name of doctor", "dentist name", "doctor name", "doctor names", "dentist names",
        "give me list", "give me name", "give me names", "give list", "give names",
        "show me list", "tell me list", "tell me name", "tell me names", "show list", "show names",
        "doctor list", "smile designer name", "smile designer kaun", "designer name",
        "doctor kon che", "doctor na naam", "doctor nu naam", "tamara doctor", "tamara dentist",
        "doctor kaun", "dentist kaun", "doctor ka naam", "dentist ka naam", "doctor ke naam",
        "doctor batao", "dentist batao", "naam aapo", "naam batao", "list aapo", "list batao",
        "ડોક્ટર કોણ છે", "ડેન્ટિસ્ટ કોણ છે", "ડોક્ટરના નામ", "ડેન્ટિસ્ટના નામ",
        "ડોક્ટરનું નામ આપો", "તમારા ડૉક્ટર", "તમારા ડેન્ટિસ્ટ", "કોણ કોણ ડૉક્ટર", "લિસ્ટ આપો", "નામ આપો",
        "डॉक्टर कौन", "डेंटिस्ट कौन", "डॉक्टर का नाम", "डेंटिस्ट का नाम", "डॉक्टर के नाम",
        "डॉक्टर बताओ", "डेंटिस्ट बताओ", "स्माइल डिज़ाइनर का नाम", "नाम बताओ", "लिस्ट बताओ"
    ]
    if tl in ["list", "names", "doctors", "dentists", "naam", "list please", "name please"]:
        return True
    return any(p in tl for p in patterns)

def is_asking_for_other_dentists(text: str) -> bool:
    if not text:
        return False
    tl = text.lower().strip()
    patterns = [
        "other options", "other option", "other doctors", "other doctor", "other dentist", "other dentists",
        "other name", "other names", "give me other name", "give me other", "hear other options", "hear other",
        "different doctor", "different dentist", "different options", "different option",
        "another doctor", "another dentist", "another option", "another options",
        "more options", "more option", "more doctors", "more dentists", "more names",
        "next doctor", "next option", "next options", "next doctors",
        "choose other dentist", "choose other doctor", "want to choose other",
        "show more", "show other", "show others", "any other", "any others", "any other doctor", "any other options",
        "bija doctor", "bija naam", "bija koi", "bija vikalp", "bija option", "bija options",
        "koi aur doctor", "dusre doctor", "dusra doctor", "aur naam", "aur option", "aur options", "koi aur batao",
        "બીજા ડૉક્ટર", "બીજા નામ", "બીજા કોઈ", "બીજા વિકલ્પ", "બીજા ડેન્ટિસ્ટ", "અન્ય ડૉક્ટર", "અન્ય નામ", "અન્ય વિકલ્પ",
        "दूसरे डॉक्टर", "दूसरे नाम", "कोई और डॉक्टर", "कोई अन्य डॉक्टर", "अन्य विकल्प", "दूसरा डॉक्टर", "और डॉक्टर", "और विकल्प"
    ]
    if any(p in tl for p in patterns):
        return True
    if tl in ["other", "others", "next", "more", "bija", "dusra", "aur"]:
        return True
    return False

def detect_user_language(user_text="", history=None, current_language=None):
    if not user_text and not history and not current_language:
        return "en"

    t_raw = str(user_text or "").strip()
    tl = t_raw.lower()

    # Normalize current_language
    c_lang = None
    if current_language:
        c_lang = str(current_language).strip().lower().split("-")[0]
        if c_lang not in ["en", "hi", "gu", "mr", "bn", "ta", "te", "kn", "ml", "pa", "or"]:
            c_lang = None

    def _detect_lang_from_string(text, established_lang=None):
        if not text:
            return None
        s_raw = str(text).strip()
        sl = s_raw.lower()

        # 0. Check explicit language commands in text (all 11 Indian languages + variants)
        if re.search(r"\b(?:english|eng|in english|english please|speak english|speak in english|talk in english|talk english|switch to english|english mein|english me|english ma)\b", sl):
            return "en"
        if re.search(r"(?:\b(?:hindi|in hindi|hindi please|hindi me|hindi mein|hindi ma|speak hindi|speak in hindi|talk in hindi|switch to hindi|hindi bolo|hindi bol|hindi me baat)\b|हिंदी)", sl):
            return "hi"
        if re.search(r"(?:\b(?:gujarati|gujrati|in gujarati|in gujrati|gujarati please|gujrati please|gujarati ma|gujrati ma|gujaratima|gujratima|gujarati bolo|speak gujarati|speak in gujarati|talk in gujarati|switch to gujarati)\b|ગુજરાતી)", sl):
            return "gu"
        if re.search(r"(?:\b(?:marathi|in marathi|marathi please|marathi madhe|marathimadhe|marathit|marathit bola|speak marathi|speak in marathi|talk in marathi|switch to marathi)\b|मराठी)", sl):
            return "mr"
        if re.search(r"(?:\b(?:tamil|thamizh|tamizh|in tamil|tamil please|tamilil|thamizhil|tamizhil|tamilil pesunga|speak tamil|speak in tamil|talk in tamil|switch to tamil)\b|தமிழ்)", sl):
            return "ta"
        if re.search(r"(?:\b(?:telugu|in telugu|telugu please|telugulo|telugulo matladandi|speak telugu|speak in telugu|talk in telugu|switch to telugu)\b|తెలుగు)", sl):
            return "te"
        if re.search(r"(?:\b(?:bengali|bangla|in bengali|in bangla|bengali please|bangla please|banglate|bengalite|banglate bolun|speak bengali|speak in bengali|talk in bengali|switch to bengali)\b|বাংলা)", sl):
            return "bn"
        if re.search(r"(?:\b(?:kannada|in kannada|kannada please|kannadadalli|kannadadalli mathadi|kannadadalli matadi|speak kannada|speak in kannada|talk in kannada|switch to kannada)\b|ಕನ್ನಡ)", sl):
            return "kn"
        if re.search(r"(?:\b(?:malayalam|in malayalam|malayalam please|malayalathil|malayalathil samsarikku|speak malayalam|speak in malayalam|talk in malayalam|switch to malayalam)\b|മലയാളം)", sl):
            return "ml"
        if re.search(r"(?:\b(?:punjabi|in punjabi|punjabi please|punjabich|punjabich gal karo|speak punjabi|speak in punjabi|talk in punjabi|switch to punjabi)\b|ਪੰਜਾਬੀ)", sl):
            return "pa"
        if re.search(r"(?:\b(?:odia|oriya|in odia|in oriya|odia please|oriya please|odiare|odiare kahantu|odiare katha|speak odia|speak in odia|talk in odia|switch to odia)\b|ଓଡ଼ିଆ)", sl):
            return "or"

        # 1. Unicode script detection
        script_counts = {
            "gu": sum(1 for c in s_raw if 0x0A80 <= ord(c) <= 0x0AFF),
            "bn": sum(1 for c in s_raw if 0x0980 <= ord(c) <= 0x09FF),
            "ta": sum(1 for c in s_raw if 0x0B80 <= ord(c) <= 0x0BFF),
            "te": sum(1 for c in s_raw if 0x0C00 <= ord(c) <= 0x0C7F),
            "kn": sum(1 for c in s_raw if 0x0C80 <= ord(c) <= 0x0CFF),
            "ml": sum(1 for c in s_raw if 0x0D00 <= ord(c) <= 0x0D7F),
            "pa": sum(1 for c in s_raw if 0x0A00 <= ord(c) <= 0x0A7F),
            "or": sum(1 for c in s_raw if 0x0B00 <= ord(c) <= 0x0B7F),
            "devanagari": sum(1 for c in s_raw if 0x0900 <= ord(c) <= 0x097F),
        }
        max_script = max(script_counts, key=script_counts.get)
        if script_counts[max_script] > 0:
            if max_script == "devanagari":
                mr_words = re.findall(r"(?:\b|[\s।.,!?:;\-_])(आहे|आहेत|नाही|नाहीत|माझे|माझा|माझी|माझ्या|तुमचे|तुमचा|तुमची|तुमच्या|आपले|आपला|आपली|आपल्या|मला|तुम्हाला|आम्हाला|त्यांना|त्याला|तिला|सांगा|सांगतो|सांगते|सांग|करावे|करायचे|करायची|करायचा|करावी|झाले|झाला|झाली|झालेत|कसे|कसा|कशी|कशा|नमस्कार|चालेल|नक्की|पाहिजे|हवे|हवी|हवा|होय|राहतो|राहते|राहतात|पुण्यात|मुंबईत|शहरात|दातांचे|दातांची|दातांना|दात|माहित|माहीत|मी|हे|या|ह्या|काय|कधी|कुठे|बोला|मराठीत)(?:\b|[\s।.,!?:;\-_])", sl)
                gu_dev_words = re.findall(r"(?:\b|[\s।.,!?:;\-_])(નથી|છે|નહિ|કરાવવું|જોઈએ|મારે|તમારે|શું|કેમ|સાથે|બરાબર|હરેશ|નરેશ)(?:\b|[\s।.,!?:;\-_])", s_raw)
                hi_words = re.findall(r"(?:\b|[\s।.,!?:;\-_])(है|हैं|हूँ|हूं|हो|था|थी|थे|गा|गी|गे|का|की|के|को|में|से|पर|ने|लिए|मेरा|मेरी|मेरे|मुझे|मुझको|हम|हमारा|हमारी|हमारे|आपका|आपकी|आपके|तुम्हारा|तुम्हारी|तुम्हारे|क्या|क्यों|कहाँ|कहां|कैसे|कैसा|कैसी|कब|कितना|कितनी|कितने|नहीं|नही|हाँ|हां|बताइए|बताओ|करना|करवाना|कराओगी|कराओगे|चाहिए|सकता|सकती|सकते|दांत|दाँत|दांतों|दाँतों|रहता|रहती|रहते|शुरू|शुरु|दीजिए|दीजिये|लीजिए|लीजिये)(?:\b|[\s।.,!?:;\-_])", sl)
                if len(mr_words) > len(hi_words) and len(mr_words) > len(gu_dev_words):
                    return "mr"
                if len(gu_dev_words) > len(hi_words):
                    return "gu"
                return "hi"
            return max_script

        # 2. Guard: If established language is not English, preserve it on short answers/loan words/numbers/names
        is_short_or_numeric = bool(
            re.fullmatch(r"[\d\s+\-_(),.]+", sl) or  # phone / pincode
            re.fullmatch(r"(?:yes|yeah|yep|ok|okay|sure|submit|cancel|done|correct|right|fine|thanks|thank you|no|nope|hello|hi|hey|good|morning|evening)\b[\w\s.,!?]*", sl) or
            len(sl.split()) <= 2 and any(w in sl for w in ["yes", "ok", "okay", "sure", "submit", "cancel"])
        )
        if is_short_or_numeric and established_lang:
            return established_lang

        # 3. Latin-script Token-based Language Detection
        scores = {"gu": 0, "hi": 0, "mr": 0, "bn": 0, "ta": 0, "te": 0, "kn": 0, "ml": 0, "pa": 0, "or": 0, "en": 0}

        # Gujarati tokens
        gu_tokens = re.findall(r"\b(tamaru|tamaro|tamari|tame|maaru|maru|maro|mari|mare|maare|kem|chho|cho|chhe|che|chu|chhu|nathi|nthi|thik|theek|kari|dyo|do|karvu|karvi|karyu|karva|karvavu|karvani|karjo|karine|naakho|nakho|thai|thay|thase|sake|etle|saher|shahar|bhaley|chokkas|aavse|mane|haji|su|shu|pan|saathe|sathe|kaya|kyare|mast|akdum|joie|joye|joiye|barabar|sachu|khotu|aaje|kaale|daant|dant|vaat|karo|bolo|naam|rahu|raho|levu|leva|levo|aapo|batavo|bhai)\b", sl)
        scores["gu"] = len(gu_tokens) * 3

        # Hindi tokens
        hi_tokens = re.findall(r"\b(mera|meri|mere|aapka|aapki|aapke|mujhe|humko|kripya|kripa|theek|bataiye|batao|kardo|karna|karni|karwana|karwani|karwao|karva|chahiye|sakte|sakta|sakti|kya|kyu|kyun|kaise|kahan|kaha|hoga|hogi|hoge|hai|hain|hoon|hun|accha|achha|sahi|zaroor|zarur|aaj|kal|daant|dant|rehta|rehti|rehte|bolo|baat|suno|kro|kariye)\b", sl)
        scores["hi"] = len(hi_tokens) * 3

        # Marathi tokens
        mr_tokens = re.findall(r"\b(maze|tumche|mazya|tumchya|mala|aahe|aahet|nahit|nahi|sangto|sangte|sang|sanga|karaycha|karaychi|havi|hava|kasa|kashi|kashe|kay|chaaleel|chalel|nakki|pahije|dant|dantanche|bola|bolave|naav|madhe|kuthe|rahate|rahato)\b", sl)
        scores["mr"] = len(mr_tokens) * 3

        # Other regional tokens
        scores["bn"] = len(re.findall(r"\b(amar|apnar|naam|nam|achhe|ache|korun|korbo|bhalo|hobe|dante|kemon|ki|shob|ekhon|aajke|korte|chai|lagbe|bolun|katha|parbo|khobor)\b", sl)) * 3
        scores["ta"] = len(re.findall(r"\b(ennudaiya|ungaludaiya|en|ungal|peyar|peru|pallu|pal|irukku|irukinga|irukkeenga|pannunga|pannu|solunga|solli|pesunga|pesu|eppadi|epdi|enna|aamam|seri|enakku|venum|vendum|thevai|kudunga|vaanga)\b", sl)) * 3
        scores["te"] = len(re.findall(r"\b(naa|mee|peru|pallu|panti|undi|undhi|cheyandi|cheppandi|matladandi|ela|enti|avunu|sare|naaku|kavali|kavalanukuntunna|unnaru|ledu)\b", sl)) * 3
        scores["kn"] = len(re.findall(r"\b(nanna|nimma|hesaru|hallu|halla|ide|madi|heli|mathadi|matadi|hege|hegidira|hegiddira|yenu|haudu|sari|nanage|beku|bekagide|kodri|illa)\b", sl)) * 3
        scores["ml"] = len(re.findall(r"\b(ente|ningalude|peru|pallu|palla|undu|cheyyuka|parayu|samsarikku|engane|enthanu|athe|sari|enikku|venam|tharo|illa|sukhamano)\b", sl)) * 3
        scores["pa"] = len(re.findall(r"\b(tuhada|tuhadi|mera|meri|naa|naam|dasso|dass|sat|sri|akal|hovega|hovegi|ki|kive|haanji|theek|mainu|chahidi|chahida|chahide|gal|karo|karda|kardi|si)\b", sl)) * 3
        scores["or"] = len(re.findall(r"\b(mora|moro|apanka|nama|danta|achhi|karantu|kahantu|kipari|kana|han|thik|mote|darkar|achhanti|katha|heba|kemiti)\b", sl)) * 3

        # English grammatical and functional tokens ONLY (excluding neutral dental terms)
        en_tokens = re.findall(r"\b(what|how|why|who|when|where|which|is|are|am|was|were|be|been|being|have|has|had|do|does|did|can|could|will|would|shall|should|may|might|must|i|you|he|she|it|we|they|my|your|his|her|our|their|me|him|them|us|this|that|these|those|the|a|an|in|on|at|to|for|from|with|about|by|into|over|after|before|between|through|under|above|below|and|or|but|if|because|as|until|while|so|not)\b", sl)
        scores["en"] = len(en_tokens)

        # Regional matches take precedence
        regional_scores = {k: v for k, v in scores.items() if k != "en"}
        max_regional = max(regional_scores, key=regional_scores.get)
        if regional_scores[max_regional] > 0 and regional_scores[max_regional] >= scores["en"]:
            return max_regional

        # If user previously established a regional language, ONLY switch back to English
        # if the user speaks a full, complete English sentence (at least 4 English words and no regional words)
        if established_lang and established_lang != "en":
            if scores["en"] >= 4 and len(sl.split()) >= 4 and regional_scores[max_regional] == 0:
                return "en"
            return established_lang

        if scores["en"] >= 2:
            return "en"

        return None

    # Step 1: Dynamic Matching on current utterance
    last_lang = _detect_lang_from_string(user_text, c_lang)
    if last_lang:
        return last_lang

    # Step 2: Fallback to established language if available
    if c_lang:
        return c_lang

    # Step 3: Fallback to USER turns in history in reverse order
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
            hist_lang = _detect_lang_from_string(p, None)
            if hist_lang and hist_lang != "en":
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

CONFIRMATION_CANCEL_MESSAGES_11 = {
    "gu": "તમારી અપૉઇન્ટમેન્ટ રિક્વેસ્ટ કેન્સલ કરવામાં આવી છે. જો તમને બીજી કોઈ મદદ જોઈએ તો જણાવશો.",
    "hi": "आपका अपॉइंटमेंट अनुरोध रद्द कर दिया गया है। अगर आपको किसी और मदद की आवश्यकता हो तो कृपया बताएं।",
    "mr": "तुमची अपॉइंटमेंट विनंती रद्द करण्यात आली आहे. तुम्हाला इतर काही मदत हवी असल्यास कृपया सांगा.",
    "bn": "আপনার অ্যাপয়েন্টমেন্টের অনুরোধ বাতিল করা হয়েছে। আপনার অন্য কোনো সাহায্যের প্রয়োজন হলে দয়া করে জানান।",
    "ta": "உங்கள் அப்பாயின்ட்மென்ட் கோரிக்கை ரத்து செய்யப்பட்டுள்ளது. உங்களுக்கு வேறு ஏதேனும் உதவி தேவைப்பட்டால் தெரியப்படுத்தவும்.",
    "te": "మీ అపాయింట్‌మెంట్ అభ్యర్థన రద్దు చేయబడింది. మీకు ఇంకేమైనా సహాయం కావాలంటే దయచేసి తెలియజేయండి.",
    "kn": "ನಿಮ್ಮ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ವಿನಂತಿಯನ್ನು ರದ್ದುಗೊಳಿಸಲಾಗಿದೆ. ನಿಮಗೆ ಇನ್ನೇನಾದರೂ ಸಹಾಯ ಬೇಕಿದ್ದರೆ ದಯವಿಟ್ಟು ತಿಳಿಸಿ.",
    "ml": "നിങ്ങളുടെ അപ്പോയിന്റ്മെന്റ് അഭ്യർത്ഥന റദ്ദാക്കപ്പെട്ടു. മറ്റെന്തെങ്കിലും സഹായം ആവശ്യമുണ്ടെങ്കിൽ ദയവായി അറിയിക്കുക.",
    "pa": "ਤੁਹਾਡੀ ਮੁਲਾਕਾਤ ਦੀ ਬੇਨਤੀ ਰੱਦ ਕਰ ਦਿੱਤੀ ਗਈ ਹੈ। ਜੇਕਰ ਤੁਹਾਨੂੰ ਕਿਸੇ ਹੋਰ ਮਦਦ ਦੀ ਲੋੜ ਹੈ ਤਾਂ ਕਿਰਪਾ ਕਰਕੇ ਦੱਸੋ।",
    "or": "ଆପଣଙ୍କର ଆପଏଣ୍ଟମେଣ୍ଟ ଅନୁରୋଧ ବାତିଲ କରାଯାଇଛି। ଯଦି ଆପଣଙ୍କୁ ଅନ୍ୟ କୌଣସି ସାହାଯ୍ୟ ଦରକାର, ଦୟାକରି ଜଣାନ୍ତୁ।",
    "en": "Your appointment request has been cancelled. Please let me know if you need anything else."
}

def get_review_summary_prompt(lang, display_name, ph, ct, pin, cn, dr, is_update=False):
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
            "gu": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Warmly acknowledge the update in ONE short phrase, and THEN YOU ARE STRICTLY REQUIRED TO RE-RECITE THE FULL 6-FIELD REVIEW SUMMARY in Gujarati without omitting any line:\n'{gu_open}\n- નામ: {display_name}\n- ફોન: {ph}\n- શહેર: {ct}\n- પિનકોડ: {pin}\n- સમસ્યા: {cn}\n- ડૉક્ટર: {dr_gu}\n\nકૃપા કરીને આ અપડેટ કરેલ અપૉઇન્ટમેન્ટ રિક્વેસ્ટ મોકલવા માટે 'submit' કહો અથવા રદ કરવા માટે 'cancel' કહો.\n🚨 ZERO-CUTOFF MANDATE: YOU MUST RECITE ALL 6 LINES AND SPEAK THE FULL CLOSING SENTENCE WITH BOTH 'SUBMIT' AND 'CANCEL' TO THE VERY LAST WORD WITHOUT CUTTING OFF OR STOPPING EARLY!'",
            "hi": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Warmly acknowledge the update in ONE short phrase, and THEN YOU ARE STRICTLY REQUIRED TO RE-RECITE THE FULL 6-FIELD REVIEW SUMMARY in Hindi without omitting any line:\n'{hi_open}\n- नाम: {display_name}\n- फ़ोन: {ph}\n- शहर: {ct}\n- पिनकोड: {pin}\n- समस्या: {cn}\n- डॉक्टर: {dr_hi}\n\nकृपया इस अपडेट किए गए अपॉइंटमेंट अनुरोध को भेजने के लिए 'submit' कहें या रद्द करने के लिए 'cancel' कहें।\n🚨 ZERO-CUTOFF MANDATE: YOU MUST RECITE ALL 6 LINES AND SPEAK THE FULL CLOSING SENTENCE WITH BOTH 'SUBMIT' AND 'CANCEL' TO THE VERY LAST WORD WITHOUT CUTTING OFF OR STOPPING EARLY!'",
            "mr": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Marathi:\n'{mr_open}\n- नाव: {display_name}\n- फोन: {ph}\n- शहर: {ct}\n- समस्या: {cn}\n- डॉक्टर: {dr_mr}\n\nकृपया ही अपडेट केलेली अपॉइंटमेंट विनंती पाठवण्यासाठी 'submit' म्हणा किंवा रद्द करण्यासाठी 'cancel' म्हणा।\n🚨 ZERO-CUTOFF MANDATE: YOU MUST RECITE ALL 5 LINES AND SPEAK THE FULL CLOSING SENTENCE WITH BOTH 'SUBMIT' AND 'CANCEL' TO THE VERY LAST WORD WITHOUT CUTTING OFF OR STOPPING EARLY!'",
            "bn": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Bengali:\n'{bn_open}\n- নাম: {display_name}\n- ফোন: {ph}\n- শহর: {ct}\n- समस्या: {cn}\n- ডাক্তার: {dr_bn}\n\nদয়া করে এই আপডেট করা অ্যাপয়েন্টমেন্ট অনুরোধ জমা দেওয়ার জন্য 'submit' বলুন বা বাতিল করার জন্য 'cancel' বলুন।\n🚨 ZERO-CUTOFF MANDATE: YOU MUST RECITE ALL 5 LINES AND SPEAK THE FULL CLOSING SENTENCE WITH BOTH 'SUBMIT' AND 'CANCEL' TO THE VERY LAST WORD WITHOUT CUTTING OFF OR STOPPING EARLY!'",
            "ta": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Tamil:\n'{ta_open}\n- பெயர்: {display_name}\n- தொலைபேசி: {ph}\n- நகரம்: {ct}\n- பிரச்சனை: {cn}\n- மருத்துவர்: {dr_ta}\n\nதயவுசெய்து இந்த புதுப்பிக்கப்பட்ட சந்திப்பு கோரிக்கையை அனுப்ப 'submit' என்று சொல்லுங்கள் அல்லது ரத்து செய்ய 'cancel' என்று சொல்லுங்கள்.\n🚨 ZERO-CUTOFF MANDATE: YOU MUST RECITE ALL 5 LINES AND SPEAK THE FULL CLOSING SENTENCE WITH BOTH 'SUBMIT' AND 'CANCEL' TO THE VERY LAST WORD WITHOUT CUTTING OFF OR STOPPING EARLY!'",
            "te": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Telugu:\n'{te_open}\n- పేరు: {display_name}\n- ఫోన్: {ph}\n- నగరం: {ct}\n- సమస్య: {cn}\n- డాక్టర్: {dr_te}\n\nదయచేసి ఈ నవీకరించబడిన అపాయింట్‌మెంట్ అభ్యర్థనను పంపడానికి 'submit' అని చెప్పండి లేదా రద్దు చేయడానికి 'cancel' అని చెప్పండి.\n🚨 ZERO-CUTOFF MANDATE: YOU MUST RECITE ALL 5 LINES AND SPEAK THE FULL CLOSING SENTENCE WITH BOTH 'SUBMIT' AND 'CANCEL' TO THE VERY LAST WORD WITHOUT CUTTING OFF OR STOPPING EARLY!'",
            "kn": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Kannada:\n'{kn_open}\n- ಹೆಸರು: {display_name}\n- ಫೋನ್: {ph}\n- ನಗರ: {ct}\n- సమస్య: {cn}\n- ವೈದ್ಯರು: {dr_kn}\n\nದಯವಿಟ್ಟು ಈ ನವೀಕರಿಸಿದ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ವಿನಂತಿಯನ್ನು ಸಲ್ಲಿಸಲು 'submit' ಎಂದು ಹೇಳಿ ಅಥವಾ ರದ್ದು ಮಾಡಲು 'cancel' ಎಂದು ಹೇಳಿ.\n🚨 ZERO-CUTOFF MANDATE: YOU MUST RECITE ALL 5 LINES AND SPEAK THE FULL CLOSING SENTENCE WITH BOTH 'SUBMIT' AND 'CANCEL' TO THE VERY LAST WORD WITHOUT CUTTING OFF OR STOPPING EARLY!'",
            "ml": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Malayalam:\n'{ml_open}\n- പേര്: {display_name}\n- ഫോൺ: {ph}\n- നഗരം: {ct}\n- പ്രശ്നം: {cn}\n- ഡോക്ടർ: {dr_ml}\n\nഈ അപ്ഡേറ്റ് ചെയ്ത അപ്പോയിന്റ്മെന്റ് അഭ്യർത്ഥന സമർപ്പിക്കാൻ 'submit' എന്ന് പറയുക അല്ലെങ്കിൽ റദ്ദാക്കാൻ 'cancel' എന്ന് പറയുക.\n🚨 ZERO-CUTOFF MANDATE: YOU MUST RECITE ALL 5 LINES AND SPEAK THE FULL CLOSING SENTENCE WITH BOTH 'SUBMIT' AND 'CANCEL' TO THE VERY LAST WORD WITHOUT CUTTING OFF OR STOPPING EARLY!'",
            "pa": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Punjabi:\n'{pa_open}\n- ਨਾਮ: {display_name}\n- ਫ਼ੋਨ: {ph}\n- ਸ਼ਹਿਰ: {ct}\n- ਸਮੱਸਿਆ: {cn}\n- ਡਾਕਟਰ: {dr_pa}\n\nਕਿਰਪਾ ਕਰਕੇ ਇਸ ਅੱਪਡੇਟ ਕੀਤੀ ਮੁਲਾਕਾਤ ਬੇਨਤੀ ਨੂੰ ਭੇਜਣ ਲਈ 'submit' ਕਹੋ ਜਾਂ ਰੱਦ ਕਰਨ ਲਈ 'cancel' ਕਹੋ।\n🚨 ZERO-CUTOFF MANDATE: YOU MUST RECITE ALL 5 LINES AND SPEAK THE FULL CLOSING SENTENCE WITH BOTH 'SUBMIT' AND 'CANCEL' TO THE VERY LAST WORD WITHOUT CUTTING OFF OR STOPPING EARLY!'",
            "or": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Odia:\n'{or_open}\n- ନାମ: {display_name}\n- ଫୋନ୍: {ph}\n- ସହର: {ct}\n- ସମସ୍ୟା: {cn}\n- ଡାକ୍ତର: {dr_or}\n\nଦୟାକରି ଏହି ଅପଡେଟ୍ ହୋଇଥିବା ଆପଏଣ୍ଟମେଣ୍ଟ ଅନୁରୋଧ ଦାଖଲ କରିବା ପାଇଁ 'submit' କୁହନ୍ତୁ କିମ୍ବା ବାତିଲ କରିବା ପାଇଁ 'cancel' କୁହନ୍ତୁ।\n🚨 ZERO-CUTOFF MANDATE: YOU MUST RECITE ALL 5 LINES AND SPEAK THE FULL CLOSING SENTENCE WITH BOTH 'SUBMIT' AND 'CANCEL' TO THE VERY LAST WORD WITHOUT CUTTING OFF OR STOPPING EARLY!'"
        }
        return prompts.get(lang_key, f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Warmly acknowledge the update in ONE short phrase, and THEN YOU ARE STRICTLY REQUIRED TO RE-RECITE THE FULL 6-FIELD REVIEW SUMMARY in full without omitting any line:\n'{en_open}\n- Name: {display_name}\n- Phone: {ph}\n- City: {ct}\n- Pincode: {pin}\n- Concern: {cn}\n- Doctor: {dr_en}\n\nPlease say 'submit' to submit this updated appointment request to our clinic team, or say 'cancel' to cancel it.\n🚨 ZERO-CUTOFF MANDATE: YOU MUST RECITE ALL 6 LINES AND SPEAK THE FULL CLOSING SENTENCE WITH BOTH 'SUBMIT' AND 'CANCEL' TO THE VERY LAST WORD WITHOUT CUTTING OFF OR STOPPING EARLY!")
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
            "gu": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Gujarati with a natural varied opening (such as '{gu_open}') and instruct the user to write/say 'submit' or 'cancel':\n'{gu_open}\n- નામ: {display_name}\n- ફોન: {ph}\n- શહેર: {ct}\n- પિનકોડ: {pin}\n- સમસ્યા: {cn}\n- ડૉક્ટર: {dr_gu}\n\nકૃપા કરીને આ અપૉઇન્ટમેન્ટ રિક્વેસ્ટ મોકલવા માટે 'submit' કહો અથવા રદ કરવા માટે 'cancel' કહો.\n🚨 ZERO-CUTOFF MANDATE: YOU MUST RECITE ALL 6 LINES AND SPEAK THE FULL CLOSING SENTENCE WITH BOTH 'SUBMIT' AND 'CANCEL' TO THE VERY LAST WORD WITHOUT CUTTING OFF OR STOPPING EARLY!'",
            "hi": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Hindi with a natural varied opening (such as '{hi_open}') and instruct the user to write/say 'submit' or 'cancel':\n'{hi_open}\n- नाम: {display_name}\n- फ़ोन: {ph}\n- शहर: {ct}\n- पिनकोड: {pin}\n- समस्या: {cn}\n- डॉक्टर: {dr_hi}\n\nकृपया इस अपॉइंटमेंट अनुरोध को भेजने के लिए 'submit' कहें या रद्द करने के लिए 'cancel' कहें।\n🚨 ZERO-CUTOFF MANDATE: YOU MUST RECITE ALL 6 LINES AND SPEAK THE FULL CLOSING SENTENCE WITH BOTH 'SUBMIT' AND 'CANCEL' TO THE VERY LAST WORD WITHOUT CUTTING OFF OR STOPPING EARLY!'",
            "mr": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Marathi with a natural varied opening (such as '{mr_open}') and instruct the user to write/say 'submit' or 'cancel':\n'{mr_open}\n- नाव: {display_name}\n- फोन: {ph}\n- शहर: {ct}\n- समस्या: {cn}\n- डॉक्टर: {dr_mr}\n\nकृपया ही अपॉइंटमेंट विनंती पाठवण्यासाठी 'submit' म्हणा किंवा रद्द करण्यासाठी 'cancel' म्हणा।\n🚨 ZERO-CUTOFF MANDATE: YOU MUST RECITE ALL 5 LINES AND SPEAK THE FULL CLOSING SENTENCE WITH BOTH 'SUBMIT' AND 'CANCEL' TO THE VERY LAST WORD WITHOUT CUTTING OFF OR STOPPING EARLY!'",
            "bn": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Bengali with a natural varied opening (such as '{bn_open}') and instruct the user to write/say 'submit' or 'cancel':\n'{bn_open}\n- নাম: {display_name}\n- ফোন: {ph}\n- শহর: {ct}\n- समस्या: {cn}\n- ডাক্তার: {dr_bn}\n\nদয়া করে এই অ্যাপয়েন্টমেন্ট অনুরোধ জমা দেওয়ার জন্য 'submit' বলুন বা বাতিল করার জন্য 'cancel' বলুন।\n🚨 ZERO-CUTOFF MANDATE: YOU MUST RECITE ALL 5 LINES AND SPEAK THE FULL CLOSING SENTENCE WITH BOTH 'SUBMIT' AND 'CANCEL' TO THE VERY LAST WORD WITHOUT CUTTING OFF OR STOPPING EARLY!'",
            "ta": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Tamil with a natural varied opening (such as '{ta_open}') and instruct the user to write/say 'submit' or 'cancel':\n'{ta_open}\n- பெயர்: {display_name}\n- தொலைபேசி: {ph}\n- நகரம்: {ct}\n- பிரச்சனை: {cn}\n- மருத்துவர்: {dr_ta}\n\nதயவுசெய்து இந்த சந்திப்பு கோரிக்கையை அனுப்ப 'submit' என்று சொல்லுங்கள் அல்லது ரத்து செய்ய 'cancel' என்று சொல்லுங்கள்.\n🚨 ZERO-CUTOFF MANDATE: YOU MUST RECITE ALL 5 LINES AND SPEAK THE FULL CLOSING SENTENCE WITH BOTH 'SUBMIT' AND 'CANCEL' TO THE VERY LAST WORD WITHOUT CUTTING OFF OR STOPPING EARLY!'",
            "te": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Telugu with a natural varied opening (such as '{te_open}') and instruct the user to write/say 'submit' or 'cancel':\n'{te_open}\n- పేరు: {display_name}\n- ఫోన్: {ph}\n- నగరం: {ct}\n- సమస్య: {cn}\n- డాక్టర్: {dr_te}\n\nదయచేసి ఈ అపాయింట్‌మెంట్ అభ్యర్థనను పంపడానికి 'submit' అని చెప్పండి లేదా రద్దు చేయడానికి 'cancel' అని చెప్పండి.\n🚨 ZERO-CUTOFF MANDATE: YOU MUST RECITE ALL 5 LINES AND SPEAK THE FULL CLOSING SENTENCE WITH BOTH 'SUBMIT' AND 'CANCEL' TO THE VERY LAST WORD WITHOUT CUTTING OFF OR STOPPING EARLY!'",
            "kn": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Kannada with a natural varied opening (such as '{kn_open}') and instruct the user to write/say 'submit' or 'cancel':\n'{kn_open}\n- ಹೆಸರು: {display_name}\n- ಫೋನ್: {ph}\n- ನಗರ: {ct}\n- समस्या: {cn}\n- ವೈದ್ಯರು: {dr_kn}\n\nದಯವಿಟ್ಟು ಈ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ವಿನಂತಿಯನ್ನು ಸಲ್ಲಿಸಲು 'submit' ಎಂದು ಹೇಳಿ ಅಥವಾ ರದ್ದು ಮಾಡಲು 'cancel' ಎಂದು ಹೇಳಿ.\n🚨 ZERO-CUTOFF MANDATE: YOU MUST RECITE ALL 5 LINES AND SPEAK THE FULL CLOSING SENTENCE WITH BOTH 'SUBMIT' AND 'CANCEL' TO THE VERY LAST WORD WITHOUT CUTTING OFF OR STOPPING EARLY!'",
            "ml": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Malayalam with a natural varied opening (such as '{ml_open}') and instruct the user to write/say 'submit' or 'cancel':\n'{ml_open}\n- പേര്: {display_name}\n- ഫോൺ: {ph}\n- നഗരം: {ct}\n- പ്രശ്നം: {cn}\n- ഡോക്ടർ: {dr_ml}\n\nഈ അപ്പോയിന്റ്മെന്റ് അഭ്യർത്ഥന സമർപ്പിക്കാൻ 'submit' എന്ന് പറയുക അല്ലെങ്കിൽ റദ്ദാക്കാൻ 'cancel' എന്ന് പറയുക.\n🚨 ZERO-CUTOFF MANDATE: YOU MUST RECITE ALL 5 LINES AND SPEAK THE FULL CLOSING SENTENCE WITH BOTH 'SUBMIT' AND 'CANCEL' TO THE VERY LAST WORD WITHOUT CUTTING OFF OR STOPPING EARLY!'",
            "pa": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Punjabi with a natural varied opening (such as '{pa_open}') and instruct the user to write/say 'submit' or 'cancel':\n'{pa_open}\n- ਨਾਮ: {display_name}\n- ਫ਼ੋਨ: {ph}\n- ਸ਼ਹਿਰ: {ct}\n- ਸਮੱਸਿਆ: {cn}\n- ਡਾਕਟਰ: {dr_pa}\n\nਕਿਰਪਾ ਕਰਕੇ ਇਸ ਮੁਲਾਕਾਤ ਬੇਨਤੀ ਨੂੰ ਭੇਜਣ ਲਈ 'submit' ਕਹੋ ਜਾਂ ਰੱਦ ਕਰਨ ਲਈ 'cancel' ਕਹੋ।\n🚨 ZERO-CUTOFF MANDATE: YOU MUST RECITE ALL 5 LINES AND SPEAK THE FULL CLOSING SENTENCE WITH BOTH 'SUBMIT' AND 'CANCEL' TO THE VERY LAST WORD WITHOUT CUTTING OFF OR STOPPING EARLY!'",
            "or": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Odia with a natural varied opening (such as '{or_open}') and instruct the user to write/say 'submit' or 'cancel':\n'{or_open}\n- ନାମ: {display_name}\n- ଫୋନ୍: {ph}\n- ସହର: {ct}\n- ସମସ୍ୟା: {cn}\n- ଡାକ୍ତର: {dr_or}\n\nଦୟାକରି ଏହି ଆପଏଣ୍ଟମେଣ୍ଟ ଅନୁରୋଧ ଦାଖଲ କରିବା ପାଇଁ 'submit' କୁହନ୍ତୁ କିମ୍ବା ବାତିଲ କରିବା ପାଇଁ 'cancel' କୁହନ୍ତୁ।\n🚨 ZERO-CUTOFF MANDATE: YOU MUST RECITE ALL 5 LINES AND SPEAK THE FULL CLOSING SENTENCE WITH BOTH 'SUBMIT' AND 'CANCEL' TO THE VERY LAST WORD WITHOUT CUTTING OFF OR STOPPING EARLY!'"
        }
        return prompts.get(lang_key, f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary with a natural varied opening (such as '{en_open}') and instruct the user to write/say 'submit' or 'cancel':\n'{en_open}\n- Name: {display_name}\n- Phone: {ph}\n- City: {ct}\n- Pincode: {pin}\n- Concern: {cn}\n- Doctor: {dr_en}\n\nPlease say 'submit' to submit this appointment request to our clinic team, or say 'cancel' to cancel it.\n🚨 ZERO-CUTOFF MANDATE: YOU MUST RECITE ALL 6 LINES AND SPEAK THE FULL CLOSING SENTENCE WITH BOTH 'SUBMIT' AND 'CANCEL' TO THE VERY LAST WORD WITHOUT CUTTING OFF OR STOPPING EARLY!")

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
        },
        "pincode": {
            "gu": "તમારી અપૉઇન્ટમેન્ટ સબમિટ કરતાં પહેલાં, કૃપા કરીને તમારા વિસ્તારનો 6 અંકનો પિનકોડ જણાવશો?",
            "hi": "आपकी अपॉइंटमेंट सबमिट करने से पहले, कृपया अपने क्षेत्र का 6 अंकों का पिनकोड बता दीजिए?",
            "mr": "तुमची अपॉइंटमेंट सबमिट करण्यापूर्वी, कृपया तुमच्या परिसराचा ६ अंकी पिनकोड सांगा?",
            "bn": "আপনার অ্যাপয়েন্টমেন্ট জমা দেওয়ার আগে, দয়া করে আপনার এলাকার ৬ অঙ্কের পিনকোড দিন?",
            "ta": "உங்கள் அப்பாயின்ட்மென்ட்டை சமர்ப்பிக்கும் முன், தயவுசெய்து உங்கள் 6 இலக்க பின்கோடை வழங்கவும்?",
            "te": "మీ అపాయింట్‌మెంట్‌ను సమర్పించే ముందు, దయచేసి మీ 6 అంకెల పిన్‌కోడ్‌ను ఇవ్వండి?",
            "kn": "ನಿಮ್ಮ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಸಲ್ಲಿಸುವ ಮೊದಲು, ದಯವಿಟ್ಟು ನಿಮ್ಮ 6 ಅಂಕಿಗಳ ಪಿನ್‌ಕೋಡ್ ತಿಳಿಸಿ?",
            "ml": "നിങ്ങളുടെ അപ്പോയിന്റ്മെന്റ് സമർപ്പിക്കുന്നതിന് മുമ്പ്, ദയവായി നിങ്ങളുടെ 6 അക്ക പിൻകോഡ് നൽകുക?",
            "pa": "ਤੁਹਾਡੀ ਮੁਲਾਕਾਤ ਦਰਜ ਕਰਨ ਤੋਂ ਪਹਿਲਾਂ, ਕਿਰਪਾ ਕਰਕੇ ਆਪਣੇ ਇਲਾਕੇ ਦਾ 6 ਅੰਕਾਂ ਦਾ ਪਿੰਨ ਕੋਡ ਦੱਸੋ?",
            "or": "ଆପଣଙ୍କ ଆପଏଣ୍ଟମେଣ୍ଟ ଦାଖଲ କରିବା ପୂର୍ବରୁ, ଦୟାକରି ଆପଣଙ୍କ ଅଞ୍ଚଳର 6 ଅଙ୍କ ବିଶିଷ୍ଟ ପିନକୋଡ୍ ପ୍ରଦାନ କରନ୍ତୁ?",
            "en": "Before I can submit your appointment request, could you please provide your 6-digit area pincode?"
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

    def _dentists_listed_in_last_reply(self):
        """Doctors Riya named in her previous reply, in spoken order (she sometimes lists them without the tool,
        leaving recommended_dentists empty). Only Latin-script 'Dr. Name' mentions are recognised."""
        import re
        for turn in reversed(self.session.get_history_turns(max_turns=6)):
            if turn.get("role") in ["model", "assistant"]:
                names = re.findall(r"Dr\.?\s+[A-Z][A-Za-z.]*(?:\s+[A-Z][A-Za-z.]*){0,3}", get_turn_text(turn))
                listed = []
                for n in names:
                    n = n.strip(" .,")
                    canonical = find_doctor_in_text(n, city=None) or n
                    if canonical not in [d["name"] for d in listed]:
                        listed.append({"name": canonical})
                return listed if len(listed) >= 2 else []
        return []

    def _ordinal_dentist(self, text: str, listed=None):
        """'first one' / 'पहले वाले' / 'બીજા ડૉક્ટર' -> that position in the list of doctors Riya just named."""
        import re
        # The list the patient actually HEARD wins over the server's list (Riya sometimes names a different set)
        listed = listed if listed is not None else (self._dentists_listed_in_last_reply() or getattr(self.session, 'recommended_dentists', None))
        if not text or not listed:
            return None
        tl = text.lower().strip()
        # Not a selection when correcting details, or when asking for OTHER doctors (Gujarati 'બીજા' means both 'second' and 'other')
        is_edit_context = any(ew in tl for ew in [
            "change", "update", "edit", "wrong", "खोટું", "ખોટો", "ખોટી", "ખોટા", "બદલ", "સુધાર",
            "गलत", "बदल", "सुधार", "phone", "number", "નંબર", "ફોન", "मोबाइल", "ખો તો"
        ])
        if is_edit_context or is_asking_for_other_dentists(text):
            return None
        ordinals = [
            # Bare "pehle/पहले/પહેલા" also means "earlier" ("jo pehle choose kiya tha" = the one I chose before),
            # so it only counts as "first" together with wala/vala ("पहले वाले")
            (0, r"\b(first|1st|pehla|pahla|pehli|first one|first doctor|1st one|pehle wal[ae]|pehle val[ae]|pahle wal[ae]|pahle val[ae])\b",
             ["पहला", "पहली", "पहले वाल", "પહેલું", "પહેલો", "પહેલી", "પહેલા વાળ", "पहिला", "पहिली", "पहिले वाल"]),
            (1, r"\b(second|2nd|bijo|bija|biju|dusra|dusre|doosra|second one|second doctor|2nd one)\b",
             ["दूसरा", "दूसरे", "दूसरी", "બીજા", "બીજું", "બીજો", "બીજી", "दुसरा", "दुसरे", "दुसरी"]),
            (2, r"\b(third|3rd|trijo|trija|teesra|tisra|teesre|third one|third doctor|3rd one)\b",
             ["तीसरा", "तीसरे", "तीसरी", "ત્રીજા", "ત્રીજું", "ત્રીજો", "ત્રીજી", "तिसरा", "तिसरे", "तिसरी"]),
        ]
        bare = {"1": 0, "one": 0, "2": 1, "two": 1, "3": 2, "three": 2}
        for idx, latin_re, native_words in ordinals:
            # Native scripts: substring check (\b is unreliable around Indic vowel signs)
            if re.search(latin_re, tl) or any(w in text for w in native_words) or bare.get(tl) == idx:
                return listed[idx].get("name", "") if len(listed) > idx else None
        return None

    def _match_recommended_dentist(self, text: str):
        """Robust fuzzy, phonetic, ordinal, and typo-tolerant matcher against recommended dentists."""
        listed = self._dentists_listed_in_last_reply() or getattr(self.session, 'recommended_dentists', None)
        if not text or not listed:
            return None
        import difflib
        import re
        tl = text.lower().strip()

        # 1. Ordinals check (first / पहले / પહેલા / second / दूसरे / બીજો ...)
        ord_doc = self._ordinal_dentist(text, listed)
        if ord_doc:
            return ord_doc

        # 2. Exact substring match (both raw text and transliterated English)
        raw_eng = transliterate_to_english(text).lower() if any(ord(c) > 127 for c in text) else tl
        for rd in listed:
            rd_name = rd.get("name", "")
            if rd_name and (rd_name.lower() in tl or rd_name.lower() in raw_eng):
                return rd_name

        # 3. Phonetic match on full name
        norm_t = _norm_phon(raw_eng)
        if len(norm_t) >= 4:
            for rd in listed:
                rd_name = rd.get("name", "")
                rd_norm = _norm_phon(rd_name)
                # CRITICAL GUARD: Both must have at least 4 characters to avoid empty string substring matches
                if len(rd_norm) >= 4 and (rd_norm in norm_t or (len(norm_t) >= 6 and norm_t in rd_norm)):
                    return rd_name

        # 4. Word-level fuzzy similarity, duplicate-collapse, and partial part matching
        user_words = [w.lower() for w in re.findall(r"[a-zA-Z]{3,}", raw_eng)]
        stopwords = {
            "doctor", "dentist", "dr", "want", "choose", "consult", "with", "appointment", "book",
            "please", "can", "the", "and", "for", "i", "to", "my", "our", "me", "expert", "usd",
            "mane", "tamare", "sathe", "saath", "mujhe", "chahiye", "karvu", "karna", "hai",
            "other", "options", "option", "more", "next", "mobile", "mobail", "nambar", "number",
            "khoto", "galat", "badlo", "maro", "mera"
        }
        filtered_words = [w for w in user_words if w not in stopwords and len(w) >= 3]

        for rd in listed:
            rd_name = rd.get("name", "")
            # Extract doctor name parts: e.g. "Dr. Prasanna Patel" -> ["prasanna", "patel"]
            doc_parts = [p.lower() for p in re.findall(r"[a-zA-Z]{3,}", rd_name) if p.lower() not in ["dr", "doctor"]]
            for w in filtered_words:
                w_collapsed = re.sub(r"(.)\1+", r"\1", w)
                w_norm = _norm_phon(w)
                if len(w_norm) < 4:
                    continue
                for dp in doc_parts:
                    dp_collapsed = re.sub(r"(.)\1+", r"\1", dp)
                    dp_norm = _norm_phon(dp)
                    if len(dp_norm) < 4:
                        continue
                    # A. Collapsed consecutive duplicates match (e.g. prasana == prasanna == prassana)
                    if len(w_collapsed) >= 4 and w_collapsed == dp_collapsed:
                        return rd_name
                    # B. Phonetic part match
                    if len(w_norm) >= 4 and len(dp_norm) >= 4 and (w_norm == dp_norm or (len(w_norm) >= 5 and w_norm in dp_norm)):
                        return rd_name
                    # C. SequenceMatcher similarity
                    ratio = difflib.SequenceMatcher(None, w, dp).ratio()
                    if ratio >= 0.80 and len(w) >= 4 and len(dp) >= 4:
                        return rd_name

        return None

    def update_session_memory(self, user_text="", history=None, data=None):
        """Ultra-robust session memory tracking for patient name, city, doctor, concern, and phone."""
        import re

        # Voice turns arrive without client history; without it every "last bot question" check
        # (asked city / pincode / phone) is blind and phone/city guards misfire
        if not history:
            history = self.session.get_history_turns()

        # Detect and lock user language across all turns
        if user_text:
            self.session.has_user_spoken = True
            det_lang = detect_user_language(user_text, history, getattr(self.session, 'current_language', None))
            if det_lang:
                if det_lang != "en":
                    self.session.current_language = f"{det_lang}-IN"
                    self.session.is_language_established = True
                elif getattr(self.session, 'is_language_established', False):
                    ut_l = user_text.lower()
                    # Misheard audio is often transcribed as Spanish/Latin-script junk, so require real English words
                    english_hits = len(set(re.findall(r"[a-z']+", ut_l)) & {"the", "is", "i", "my", "you", "your", "what", "how", "can", "please", "want", "to", "and", "for", "me", "do", "are", "it", "this", "have"})
                    if re.search(r"\b(?:english|in english|speak english|speak in english|talk in english)\b", ut_l) or (len(user_text.split()) >= 4 and english_hits >= 2 and detect_user_language(user_text, None, None) == "en"):
                        self.session.current_language = "en-IN"
                else:
                    self.session.current_language = "en-IN"
            ut_lower = user_text.lower()
            affirm_words = [
                "yes", "ha", "haan", "sure", "ok", "okay", "kar do", "kardo", "chalu", "chokkas",
                "booking", "appointment", "consultation", "karvi che", "karvavvu che", "karni hai",
                "hogi", "bataiye", "batao", "book", "अपॉइंटमेंट", "अपोइंटमेंट", "बुक", "बुकिंग",
                "करा दो", "करानी है", "करनी है", "हाँ", "हां", "બુક", "અપૉઇન્ટમેન્ટ", "અપોઈન્ટમેન્ટ",
                "હા", "ચોક્કસ", "કરાવો", "લેવી છે", "કરવી છે", "appointment book", "book appointment"
            ]
            def _is_affirm_in_text(word_list, text):
                for w in word_list:
                    if any(ord(c) > 127 for c in w):
                        if w in text:
                            return True
                    else:
                        if re.search(r"\b" + re.escape(w) + r"\b", text):
                            return True
                return False

            if self.session.user_concern and not getattr(self.session, "consultation_agreed", False):
                if _is_affirm_in_text(affirm_words, ut_lower):
                    self.session.consultation_agreed = True
                    self.session.profession_asked = True
                    if not self.session.booking_slots.get("pincode"):
                        self.session.asking_for_field = "pincode"
            elif _is_affirm_in_text(["appointment", "book", "अपॉइंटमेंट", "बुक", "બુક"], ut_lower):
                self.session.consultation_agreed = True
                self.session.profession_asked = True
                if not self.session.booking_slots.get("pincode"):
                    self.session.asking_for_field = "pincode"

        if data:
            client_slots = data.get("slots")
            if client_slots and isinstance(client_slots, dict):
                # ⚡ GUARD: Never blindly overwrite sensitive fields from frontend JS state.
                # 'pincode', 'city', and 'doctor_name' are validated below via corpus checks.
                # Allowing them through here causes stale JS-held values to resurrect after
                # the bot explicitly cleared them (e.g. after a city edit).
                _protected_slot_keys = {"pincode", "city", "doctor_name"}
                for k, v in client_slots.items():
                    if k in _protected_slot_keys:
                        continue  # handled by validated paths below
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
            user_texts_in_hist = [get_turn_text(t) for t in (history or []) if t.get("role") in ["user", "client"]]
            all_user_corpus = " ".join([user_text or ""] + user_texts_in_hist)
            all_digits_corpus = "".join(filter(str.isdigit, all_user_corpus))

            client_city = data.get("userCity")
            if client_city and isinstance(client_city, str) and client_city.strip() and not self.session.booking_slots.get("city"):
                # Only accept if mentioned in conversation corpus
                if client_city.lower() in all_user_corpus.lower():
                    self.session.booking_slots["city"] = client_city.strip()
            client_doc = data.get("userDoctor")
            if client_doc and isinstance(client_doc, str) and client_doc.strip() and not self.session.booking_slots.get("doctor_name"):
                if client_doc.lower() in all_user_corpus.lower():
                    self.session.booking_slots["doctor_name"] = client_doc.strip()
            client_phone = data.get("userPhone")
            if client_phone and isinstance(client_phone, str) and client_phone.strip() and not self.session.booking_slots.get("phone"):
                ph_d = "".join(filter(str.isdigit, client_phone))
                if len(ph_d) == 10 and ph_d in all_digits_corpus:
                    self.session.booking_slots["phone"] = client_phone.strip()
            client_pincode = data.get("userPincode")
            if client_pincode and isinstance(client_pincode, str) and client_pincode.strip() and not self.session.booking_slots.get("pincode"):
                pin_d = "".join(filter(str.isdigit, client_pincode))
                if len(pin_d) == 6 and pin_d in all_digits_corpus:
                    self.session.booking_slots["pincode"] = client_pincode.strip()

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
            "mp", "uttarakhand", "kashmir", "assam", "goa", "sikkim", "gangtok", "namchi", "singtam", "pakyong",
            "siliguri", "darjeeling", "kalimpong", "south", "north", "east", "west", "india", "bharat",
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
            "list", "aapo", "nahi", "nathi", "karvu", "karo", "submit", "cancel", "yes", "no", "ok", "okay", "ookay", "okie", "okies", "fine", "sure", "done",
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
            from voice_agent.services.dentist_service import detect_indian_state
            if detect_indian_state(fn) or (ln and ln != "-" and detect_indian_state(ln)):
                return False
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

        # Flag appointment cancellation if detected in current utterance
        if user_text and is_cancel_submit(user_text, self.session):
            self.session.booking_slots["is_cancel"] = True
            self.session.pending_cancellation = True
            print(f"[CANCELLATION-FLAGGED] User utterance '{user_text}' flagged session cancellation!")

        # Scan history for review summary if present - ALWAYS UNCONDITIONALLY OVERWRITE WITH REVIEW SUMMARY
        if history and isinstance(history, list):
            user_mentioned_doctors = set()
            for h_t in history:
                if h_t.get("role") in ["user", "client"]:
                    u_t_text = get_turn_text(h_t)
                    d_m = find_doctor_in_text(u_t_text)
                    if d_m:
                        user_mentioned_doctors.add(d_m.lower())

            # Find the last assistant review summary turn
            rev_turn_idx = -1
            for idx in range(len(history) - 1, -1, -1):
                turn = history[idx]
                if turn.get("role") in ["model", "assistant"]:
                    p_txt = get_turn_text(turn)
                    if p_txt and is_submit_review_summary(p_txt):
                        rev_turn_idx = idx
                        break

            if rev_turn_idx >= 0:
                p_txt = get_turn_text(history[rev_turn_idx])
                sum_slots_last = extract_slots_from_review_summary(p_txt)
                if sum_slots_last:
                    # Check if user mentioned city edit or new city in turns AFTER this review summary
                    subsequent_user_texts = [
                        get_turn_text(history[j]) for j in range(rev_turn_idx + 1, len(history))
                        if history[j].get("role") in ["user", "client"]
                    ] + [user_text or ""]
                    subsequent_user_combined = " ".join(subsequent_user_texts).lower()

                    has_subsequent_city_edit = bool(re.search(r"\b(city|shahar|shaher|sahar|શહેર|शहर)\b", subsequent_user_combined))
                    subsequent_city_found = None
                    for u_sub in subsequent_user_texts:
                        c_cand = extract_city_from_text(u_sub)
                        if c_cand:
                            subsequent_city_found = c_cand
                            break

                    old_sum_city = str(sum_slots_last.get("city") or "")
                    if has_subsequent_city_edit or (subsequent_city_found and subsequent_city_found.lower() != old_sum_city.lower()):
                        # User is editing or changed city after the review summary!
                        # Clear stale pincode and doctor tied to the old city so they don't resurrect!
                        sum_slots_last.pop("pincode", None)
                        sum_slots_last.pop("doctor_name", None)
                        if subsequent_city_found:
                            sum_slots_last["city"] = subsequent_city_found
                        elif has_subsequent_city_edit:
                            sum_slots_last.pop("city", None)

                    if sum_slots_last.get("doctor_name"):
                        d_check = sum_slots_last["doctor_name"].lower()
                        if not any(d_check in umd or umd in d_check for umd in user_mentioned_doctors):
                            sum_slots_last.pop("doctor_name", None)
                    from voice_agent.utils.helpers import is_valid_indian_mobile, get_review_summary_problem
                    summary_is_valid = not get_review_summary_problem({
                        "user_name": self.session.user_name, "user_concern": self.session.user_concern,
                        **{k: v for k, v in self.session.booking_slots.items() if k != "phone"}, **sum_slots_last
                    })
                    if sum_slots_last.get("phone") and not is_valid_indian_mobile(sum_slots_last["phone"]):
                        sum_slots_last.pop("phone", None)
                    # A newer phone the patient gave after this summary must not be reverted to the summary's old one
                    if any(extract_valid_phone(u_sub) for u_sub in subsequent_user_texts):
                        sum_slots_last.pop("phone", None)
                        summary_is_valid = False
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
                    # Only a fully valid summary may become the submission source of truth, and never one that was
                    # already used for a submission (re-reading history would otherwise revive it every turn)
                    if summary_is_valid and p_txt.strip() not in getattr(self.session, "consumed_summary_texts", set()):
                        self.session.last_review_summary_slots = dict(sum_slots_last)
                        self.session.last_review_summary_text = p_txt

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
                    # ✅ GUARD: If user is actively editing/changing their city, do NOT restore
                    # old city/pincode/doctor from history — that would undo the edit intent.
                    _city_edit_in_progress = (getattr(self.session, 'asking_for_field', None) == "city")

                    # Check city in history (accepts all certified and regional residence cities)
                    c_found = extract_city_from_text(p)
                    if c_found and not self.session.booking_slots.get("city") and not _city_edit_in_progress:
                        from voice_agent.services.dentist_service import detect_indian_state
                        st_found = detect_indian_state(c_found)
                        if st_found and c_found.lower() == st_found.lower():
                            self.session.user_state = st_found
                        else:
                            self.session.booking_slots["city"] = c_found
                            self.session.city_manually_confirmed = True  # ✅ User said this city explicitly
                            self.session.unsupported_city = None

                    # Check phone in history
                    valid_phone_h = extract_valid_phone(p)
                    if valid_phone_h and not self.session.booking_slots.get("phone"):
                        self.session.booking_slots["phone"] = valid_phone_h

                    # Check pincode in history
                    valid_pin_h = extract_valid_pincode(p, phone=self.session.booking_slots.get("phone"))
                    if valid_pin_h and not self.session.booking_slots.get("pincode") and not _city_edit_in_progress:
                        self.session.booking_slots["pincode"] = valid_pin_h

                    # Check doctor name in history
                    doc_h = find_doctor_in_text(p, self.session.booking_slots.get("city"))
                    if doc_h and not self.session.booking_slots.get("doctor_name") and not _city_edit_in_progress:
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
            self.session.slot_just_updated = False
            
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
            
            is_locked = getattr(self.session, "city_pincode_locked", False)
            is_phone_edit_req = is_update_intent and bool(re.search(r"\b(phone|number|mobile|fon|fone|ફોન|નંબર|મોબાઇલ|फोन|नंबर|मोबाइल)\b", text.lower()))
            is_pincode_edit_req = is_update_intent and not is_locked and bool(re.search(r"\b(pincode|pin code|postal|zip|pinkod|પિનકોડ|पिनकोड|पिन कोड)\b", text.lower()))
            is_city_edit_req = is_update_intent and not is_locked and has_city_kw
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
            
            # ⚡ Step 1: City extraction from user text (Always extract BEFORE Pincode & Doctor to support simultaneous updates) ⚡
            last_model_turn_text = ""
            if history and isinstance(history, list):
                for turn in reversed(history):
                    if turn.get("role") in ["model", "assistant"]:
                        last_model_turn_text = get_turn_text(turn).lower()
                        break

            last_model_asked_city = bool(re.search(r"(કયા શહેરમાં|ક્યા શહેરમાં|કયા શહેર|શહેરમાં રહો|ક્યાં રહો છો|which city|what city|city do you reside|किस शहर|कौन से शहर|शहर में रहते|কোন্ শহরে)", last_model_turn_text))
            last_model_asked_pincode = bool(re.search(r"(પિનકોડ|pincode|pin code|postal code|पिनकोड|পিনকোড)", last_model_turn_text))
            last_model_asked_phone = bool(re.search(r"(મોબાઇલ|મોબાઈલ|ફોન નંબર|phone|mobile|फ़ोन|फोन नंबर|মোবাইল)", last_model_turn_text))
            last_model_asked_concern = bool(re.search(r"(dental concern|smile goal|દાંતની કઈ સમસ્યા|દાંતની સમસ્યા|દાંત ની સમસ્યા|દાંતમાં|दांतों की क्या समस्या|दांत की क्या समस्या|दांतों में क्या समस्या)", last_model_turn_text))

            # Detect strict valid 10-digit Indian phone pattern
            valid_phone = extract_valid_phone(text)
            digits_in_text = "".join(filter(str.isdigit, text))
            if valid_phone:
                if self.session.booking_slots.get("phone") != valid_phone:
                    self.session.booking_slots["phone"] = valid_phone
                    self.session.booking_slots["is_submitted"] = False
                    self.session.slot_just_updated = True
                self.session.last_invalid_phone_input = None
                self.session.phone_invalid = False
                self.session.asking_for_field = None
            elif is_update_intent and is_phone_edit_req:
                # User specifically asked to change phone number, but hasn't given the 10 digits yet
                self.session.booking_slots["phone"] = ""
                self.session.booking_slots["is_submitted"] = False
                self.session.slot_just_updated = False
                self.session.asking_for_field = "phone"
            elif len(digits_in_text) >= 4 and not self.session.booking_slots.get("phone"):
                # Guard: Don't flag a 6-digit pincode as an invalid phone number
                is_likely_pincode = (len(digits_in_text) == 6 and digits_in_text[0] in "123456789")
                if not is_likely_pincode:
                    self.session.last_invalid_phone_input = digits_in_text
                    if len(digits_in_text) in [7, 8, 9, 11, 12, 13] or last_model_asked_phone or getattr(self.session, 'asking_for_field', None) == "phone":
                        self.session.phone_invalid = True

            if last_model_asked_city and not getattr(self.session, 'asking_for_field', None):
                self.session.asking_for_field = "city"
            elif last_model_asked_pincode and not getattr(self.session, 'asking_for_field', None):
                self.session.asking_for_field = "pincode"
            elif last_model_asked_phone and not getattr(self.session, 'asking_for_field', None):
                self.session.asking_for_field = "phone"

            # ⚡ City confirmation check when Riya asked to confirm city from pincode ⚡
            if getattr(self.session, 'city_confirm_needed', False) or getattr(self.session, 'asking_for_field', None) == "city_confirmation":
                pending_c = getattr(self.session, 'pending_city', '')
                pending_disp = getattr(self.session, 'pending_display_city', '')
                pending_p = getattr(self.session, 'pending_pincode', '')
                clean_txt = text.lower().strip()
                aff_words = [
                    "ha", "haa", "haan", "yes", "yeah", "yep", "sure", "correct", "right",
                    "sahi", "sahi hai", "barabar", "barabar chhe", "chokkas", "ha ji", "haan ji",
                    "bilkul", "thik", "theek", "kharekhar", "satya", "ok", "okay"
                ]
                is_affirmative = (
                    is_affirmative_submit(text)
                    or any(re.search(rf"\b{re.escape(w)}\b", clean_txt) for w in aff_words)
                    or any(w in clean_txt for w in ["हाँ", "हां", "सही", "બરાબર", "હા", "સાચું", "નક્કી", "होय"])
                    or (pending_c and pending_c.lower() in clean_txt)
                    or (pending_disp and any(part.strip().lower() in clean_txt for part in pending_disp.split(",") if len(part.strip()) >= 3))
                )
                neg_words = ["no", "na", "nahi", "nahin", "nathi", "not", "nthi"]
                is_negative = any(re.search(rf"\b{re.escape(w)}\b", clean_txt) for w in neg_words) and not any(w in clean_txt for w in ["right", "correct", "sahi", "barabar"])

                if is_affirmative and not is_negative:
                    self.session.city_confirm_needed = False
                    self.session.booking_slots["city"] = pending_c
                    self.session.booking_slots["pincode"] = pending_p
                    if getattr(self.session, 'pending_area', None):
                        self.session.booking_slots["area"] = self.session.pending_area
                    self.session.city_pincode_locked = True
                    self.session.city_manually_confirmed = True
                    self.session.pending_pincode = None
                    self.session.pending_city = None
                    self.session.pending_display_city = None
                    self.session.pending_area = None
                    self.session.pincode_just_updated = True
                    self.session.asking_for_field = "doctor_selection"
                    self.session.recommended_dentists = []
                    self.session.recommended_dentists_spoken = False
                    self.session.doctor_guidance_asked = False
                    # A changed residence must be re-confirmed in a new summary before it is submitted
                    if self.session.booking_slots.get("submission_id") or getattr(self.session, "submitted_lead_id", None):
                        self.session.slots_edited_after_submit = True
                    self.session.booking_slots["is_submitted"] = False
                    print(f"[CITY-CONFIRMED] City '{pending_c}' confirmed from pincode '{pending_p}'!")
                elif not is_affirmative and is_negative:
                    self.session.city_confirm_needed = False
                    self.session.pending_pincode = None
                    self.session.pending_city = None
                    self.session.pending_display_city = None
                    self.session.pending_area = None
                    self.session.pending_city = None
                    self.session.booking_slots["city"] = ""
                    self.session.booking_slots["pincode"] = ""
                    self.session.city_pincode_locked = False
                    self.session.asking_for_field = "pincode"
                    print(f"[CITY-CONFIRM-REJECTED] User rejected city '{pending_c}', re-asking pincode!")

            asking_c = (getattr(self.session, 'asking_for_field', None) == "city" or last_model_asked_city)
            from voice_agent.services.dentist_service import detect_indian_state
            detected_st = detect_indian_state(text)
            c_user = extract_city_from_text(text, asking_for_city=asking_c)

            # Check if user mentioned an Indian State rather than a specific city
            if detected_st and (not c_user or c_user.lower() == detected_st.lower()):
                self.session.user_state = detected_st
                self.session.state_clarification_needed = detected_st
                self.session.asking_for_field = "city"
                self.session.booking_slots["city"] = ""
                self.session.city_pincode_mismatch = False
                self.session.city_pincode_mismatch_data = None
                print(f"[STATE-DETECTED] User mentioned Indian state '{detected_st}', asking for specific city/town inside {detected_st}!")
            else:
                if detected_st and c_user and c_user.lower() != detected_st.lower():
                    self.session.user_state = detected_st
                    self.session.state_clarification_needed = None
                old_c = self.session.booking_slots.get("city") or getattr(self.session, 'pending_city', '')
                is_locked = getattr(self.session, 'city_pincode_locked', False) or bool(self.session.booking_slots.get("city") and self.session.booking_slots.get("pincode"))
                if is_locked:
                    self.session.city_pincode_locked = True

                has_explicit_residence = bool(re.search(
                    r"\b(?:i live in|i stay in|i am from|living in|staying in|reside in|my city is|mari city|maru saher|mera shahar|maru shaher|mera sahar|shifted to|moved to|now in|hve hu|hu .* rahu chu|me .* rehta hoon)\b", 
                    text, re.IGNORECASE
                ))
                is_city_edit_req = bool(re.search(r"\b(?:change\s+city|update\s+city|edit\s+city|city\s+change|city\s+update|city\s+badalna|change\s+my\s+city)\b", text, re.IGNORECASE))
                # Answer to "which city do you live in?" is a residence update, not a trip to another city.
                # Only real questions count: the confirmation "you live in Surat, right?" must NOT switch to loose city
                # matching, or answers like "सही है" / "पहले वाले" get read as towns (Sahee, Wale -> phantom travel booking)
                last_model_asked_residence = bool(re.search(r"(ક્યાં રહો|કયા શહેરમાં રહો|where do you live|which city do you live|which city do you reside|what city do you live|किस शहर में रह|कौन से शहर में रह|कहाँ रहते|कहां रहते)", last_model_turn_text))
                if last_model_asked_residence and c_user:
                    asking_c = True

                if has_explicit_residence or is_city_edit_req or (last_model_asked_residence and c_user):
                    # Explicit command to change residence city: unlock city to allow residence update
                    is_locked = False
                    self.session.city_pincode_locked = False
                    travel_dest = None
                else:
                    travel_dest = extract_travel_destination_request(text)
                    if not travel_dest and c_user and old_c and c_user.lower() != old_c.lower():
                        travel_dest = c_user
                        print(f"[TRAVEL-INQUIRY] User with residence '{old_c}' inquired about '{c_user}'. Keeping residence locked, serving '{c_user}' dentists!")

                if travel_dest and getattr(self.session, 'pending_city', None):
                    # Patient was in middle of pincode confirmation and directly requested another city!
                    self.session.booking_slots["city"] = self.session.pending_city
                    self.session.booking_slots["pincode"] = getattr(self.session, 'pending_pincode', '')
                    self.session.city_pincode_locked = True
                    self.session.city_manually_confirmed = True
                    self.session.city_confirm_needed = False
                    self.session.pending_city = None
                    self.session.pending_pincode = None
                    old_c = self.session.booking_slots.get("city")
                    is_locked = True

                if travel_dest and (is_locked or old_c):
                    # ⚡ TRAVEL BOOKING IN ANOTHER CITY (e.g. resident of Mumbai booking in Surat) ⚡
                    # Rule: Residence City & Pincode are LOCKED and NEVER change!
                    if not self.session.booking_slots.get("pincode"):
                        cand_pin = getattr(self.session, 'pending_pincode', None) or getattr(self.session, 'last_recommended_pincode', None)
                        if cand_pin and len(str(cand_pin)) == 6:
                            self.session.booking_slots["pincode"] = str(cand_pin)
                    print(f"[TRAVEL-BOOKING] Resident of '{old_c}' ({self.session.booking_slots.get('pincode')}) requests appointment in '{travel_dest}'!")
                    self.session.booking_slots["clinic_city"] = travel_dest
                    self.session.travel_destination_city = travel_dest
                    self.session.is_travel_booking_turn = True
                    doc_in_turn = find_doctor_in_text(text, travel_dest) or find_doctor_in_text(text, city=None)
                    if doc_in_turn:
                        self.session.booking_slots["doctor_name"] = doc_in_turn
                        self.session.asking_for_field = "phone"
                    else:
                        self.session.booking_slots["doctor_name"] = ""
                        self.session.asking_for_field = "doctor_selection"
                    self.session.recommended_dentists = []
                    self.session.recommended_dentists_spoken = False
                    self.session.doctor_guidance_asked = False
                    self.session.last_review_summary_slots = {}
                    self.session.last_review_summary_text = ""
                    from voice_agent.services.dentist_service import get_nearest_dentists_for_travel
                    p_pin = self.session.booking_slots.get("pincode") or ""
                    t_docs = get_nearest_dentists_for_travel(p_pin, old_c or "", travel_dest)
                    self.session.recommended_dentists = t_docs
                elif not is_locked:
                    if c_user:
                        has_explicit_residence = bool(re.search(r"\b(?:i live in|i stay in|i am from|living in|staying in|reside in|my city is|mari city|maru saher|mera shahar|maru shaher|mera sahar)\b", text, re.IGNORECASE))
                        clean_u_text = re.sub(r"[^a-zA-Z\s]", "", text).strip().lower()
                        is_pure_city_input = bool(c_user and (clean_u_text == c_user.lower() or clean_u_text in [f"in {c_user.lower()}", f"{c_user.lower()} city"]))
                        if not old_c or is_city_edit_req or has_explicit_residence or (asking_c and (is_pure_city_input or c_user)) or getattr(self.session, 'city_pincode_mismatch', False):
                            if old_c != c_user:
                                self.session.booking_slots["city"] = c_user
                                self.session.city_manually_confirmed = True  # ✅ Mark city as user-explicitly confirmed
                                self.session.unsupported_city = None
                                self.session.city_doctor_mismatch = None
                                self.session.booking_slots["is_submitted"] = False
                                self.session.slot_just_updated = True
                                self.session.city_just_changed = True
                                self.session.state_clarification_needed = None
                                self.session.last_review_summary_slots = {}
                                self.session.last_review_summary_text = ""
                                if asking_c:
                                    self.session.asking_for_field = None
                                # Check if newly updated city resolves a previous city-pincode mismatch!
                                if getattr(self.session, 'city_pincode_mismatch', False):
                                    from voice_agent.services.dentist_service import validate_city_pincode_match
                                    m_pin = getattr(self.session, 'city_pincode_mismatch_data', {}).get("pincode")
                                    if m_pin:
                                        is_m_ok, m_det, _ = validate_city_pincode_match(c_user, m_pin)
                                        if is_m_ok:
                                            self.session.city_pincode_mismatch = False
                                            self.session.city_pincode_mismatch_data = None
                                            self.session.booking_slots["pincode"] = m_pin
                                            self.session.pincode_just_updated = True
                                            self.session.asking_for_field = "doctor_selection"
                                            self.session.recommended_dentists = []
                                            self.session.recommended_dentists_spoken = False
                                            self.session.doctor_guidance_asked = False
                                            self.session.city_pincode_locked = True
                                            print(f"[PINCODE-MISMATCH-RESOLVED] User updated city to '{c_user}', matched pending pincode '{m_pin}'!")
                                        else:
                                            # User clarified/changed city to c_user, but the previously rejected pincode does NOT match this new city
                                            self.session.city_pincode_mismatch = False
                                            self.session.city_pincode_mismatch_data = None
                                            self.session.booking_slots["pincode"] = ""
                                            self.session.asking_for_field = "pincode"
                                            self.session.city_updated_need_pincode = True
                                            print(f"[PINCODE-MISMATCH-CITY-CHANGED] User clarified city to '{c_user}', cleared old mismatch pincode '{m_pin}'!")
                                    else:
                                        self.session.city_pincode_mismatch = False
                                        self.session.city_pincode_mismatch_data = None
                                        self.session.booking_slots["pincode"] = ""
                                        self.session.asking_for_field = "pincode"
                                        self.session.city_updated_need_pincode = True
                                else:
                                    # ✅ City changed or set without prior mismatch -> always clear pincode & doctor and prompt for pincode!
                                    self.session.booking_slots["pincode"] = ""
                                    self.session.booking_slots["doctor_name"] = ""
                                    self.session.recommended_dentists = []
                                    self.session.recommended_dentists_spoken = False
                                    self.session.doctor_guidance_asked = False
                                    self.session.asking_for_field = "pincode"
                                    self.session.city_updated_need_pincode = True
                                    self.session.last_review_summary_slots = {}
                                    self.session.last_review_summary_text = ""
                                    print(f"[CITY-CHANGED] City changed from '{old_c}' to '{c_user}', clearing pincode and doctor, asking for new pincode!")
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
                        self.session.booking_slots["pincode"] = ""         # ✅ Clear stale pincode so old city's pincode doesn't cause mismatch
                        self.session.booking_slots["doctor_name"] = ""     # ✅ Clear doctor tied to old city
                        self.session.city_doctor_mismatch = None
                        self.session.city_pincode_mismatch = False         # ✅ Clear any prior mismatch flag
                        self.session.city_pincode_mismatch_data = None     # ✅ Clear mismatch data (had old city name in it)
                        self.session.city_manually_confirmed = False       # ✅ Allow new city to be confirmed fresh
                        self.session.recommended_dentists = []
                        self.session.recommended_dentists_spoken = False
                        self.session.doctor_guidance_asked = False
                        self.session.booking_slots["is_submitted"] = False
                        self.session.slot_just_updated = False
                        self.session.last_review_summary_slots = {}       # ✅ Clear cached review so pincode doesn't resurrect from it
                        self.session.last_review_summary_text = ""
                        self.session.city_updated_need_pincode = True      # ✅ Ensure pincode is re-asked after new city is provided
                        self.session.asking_for_field = "city"

            # ⚡ Step 2: Strict valid 6-digit area pincode detection + CITY LOCK VALIDATION ⚡
            valid_pincode = extract_valid_pincode(text, phone=self.session.booking_slots.get("phone"))
            if valid_pincode and getattr(self.session, "pending_pincode", None) == valid_pincode and getattr(self.session, "asking_for_field", None) == "city_confirmation":
                pass  # new pincode already awaiting the patient's city confirmation (handled above on "yes")
            elif valid_pincode and getattr(self.session, "city_pincode_locked", False) and valid_pincode != str(self.session.booking_slots.get("pincode") or valid_pincode):
                # A DIFFERENT pincode while the residence is locked = the patient is changing residence: confirm the
                # city from the new pincode instead of silently keeping the old city (summary showed Surat + 360001)
                from voice_agent.services.dentist_service import validate_pincode_online, get_pincode_city_info
                ok_pin, det_city, _ = validate_pincode_online(valid_pincode)
                if ok_pin:
                    info = get_pincode_city_info(valid_pincode) or {}
                    self.session.pending_pincode = valid_pincode
                    self.session.pending_city = info.get("canonical_city") or det_city or ""
                    self.session.pending_display_city = info.get("display_city") or det_city or ""
                    self.session.pending_area = info.get("area") or ""
                    self.session.city_pincode_locked = False
                    self.session.city_confirm_needed = True
                    self.session.asking_for_field = "city_confirmation"
                    self.session.recommended_dentists = []
                    print(f"[CITY-CHANGE] New pincode '{valid_pincode}' -> confirming city '{self.session.pending_display_city}'")
                else:
                    self.session.pincode_invalid = True
                    self.session.last_invalid_pincode_input = valid_pincode
            elif valid_pincode and getattr(self.session, "city_pincode_locked", False):
                print(f"[PINCODE-LOCKED] Residence city/pincode already locked as '{self.session.booking_slots.get('city')}' ({self.session.booking_slots.get('pincode')}). Pincode '{valid_pincode}' will not change residence.")
            elif valid_pincode:
                from voice_agent.services.dentist_service import validate_pincode_online, get_location_for_pincode, get_pincode_city_info, validate_city_pincode_match
                is_valid_pin, detected_pin_city, pin_err = validate_pincode_online(valid_pincode)
                city_info = get_pincode_city_info(valid_pincode) if is_valid_pin else {}
                canonical_city = city_info.get("canonical_city") or detected_pin_city or ""
                display_city = city_info.get("display_city") or detected_pin_city or ""
                sub_area = city_info.get("area") or ""

                if not is_valid_pin:
                    # 🚨 INVALID PINCODE (NOT FOUND IN INDIA POSTAL API)
                    self.session.pincode_invalid = True
                    self.session.last_invalid_pincode_input = valid_pincode
                    self.session.city_confirm_needed = False
                    self.session.asking_for_field = "pincode"
                    print(f"[PINCODE-INVALID] Pincode '{valid_pincode}' rejected: {pin_err}")
                else:
                    # ✅ VALID PINCODE
                    self.session.pincode_invalid = False
                    self.session.last_invalid_pincode_input = None
                    active_city = self.session.booking_slots.get("city")
                    is_locked = getattr(self.session, 'city_pincode_locked', False)
                    city_manually_confirmed = getattr(self.session, 'city_manually_confirmed', False)

                    if active_city and (is_locked or city_manually_confirmed):
                        # City is already confirmed; validate match
                        is_match, detected_dist, mismatch_err = validate_city_pincode_match(active_city, valid_pincode)
                        if not is_match:
                            cur_mismatch_count = getattr(self.session, 'pincode_mismatch_count', 0) + 1
                            self.session.pincode_mismatch_count = cur_mismatch_count
                            if cur_mismatch_count >= 3:
                                print(f"[PINCODE-MISMATCH-OVERRIDE] Accepted '{valid_pincode}' after 3 attempts.")
                                is_match = True
                                self.session.city_pincode_mismatch = False
                                self.session.city_pincode_mismatch_data = None
                                self.session.pincode_mismatch_count = 0
                            else:
                                self.session.city_pincode_mismatch = True
                                self.session.city_pincode_mismatch_data = {
                                    "city": active_city,
                                    "pincode": valid_pincode,
                                    "detected_city": detected_dist
                                }
                                self.session.pincode_just_updated = False
                                self.session.asking_for_field = "pincode_mismatch"
                                print(f"[PINCODE-MISMATCH #{cur_mismatch_count}] City '{active_city}' != Pincode '{valid_pincode}' ({detected_dist})")

                        if is_match:
                            self.session.pincode_mismatch_count = 0
                            self.session.city_pincode_mismatch = False
                            self.session.city_pincode_mismatch_data = None
                            self.session.booking_slots["pincode"] = valid_pincode
                            self.session.pincode_just_updated = True
                            self.session.asking_for_field = "doctor_selection"
                            self.session.recommended_dentists = []
                            self.session.recommended_dentists_spoken = False
                            self.session.doctor_guidance_asked = False
                            self.session.city_pincode_locked = True
                    elif c_user and detected_pin_city and (c_user.lower() in detected_pin_city.lower() or detected_pin_city.lower() in c_user.lower()):
                        # User stated both city and pincode together in this turn and they match!
                        self.session.city_confirm_needed = False
                        self.session.booking_slots["city"] = canonical_city or c_user
                        self.session.booking_slots["pincode"] = valid_pincode
                        if sub_area:
                            self.session.booking_slots["area"] = sub_area
                        self.session.city_pincode_locked = True
                        self.session.city_manually_confirmed = True
                        self.session.pincode_just_updated = True
                        self.session.asking_for_field = "doctor_selection"
                        self.session.recommended_dentists = []
                        self.session.recommended_dentists_spoken = False
                        self.session.doctor_guidance_asked = False
                        print(f"[PINCODE-CITY-SIMULTANEOUS] Confirmed city '{self.session.booking_slots.get('city')}' & pincode '{valid_pincode}'!")
                    else:
                        # ⚡ PINCODE FIRST FLOW: Valid pincode provided first, now trigger city confirmation!
                        self.session.city_confirm_needed = True
                        self.session.pending_pincode = valid_pincode
                        self.session.pending_city = canonical_city
                        self.session.pending_display_city = display_city
                        self.session.pending_area = sub_area
                        self.session.asking_for_field = "city_confirmation"
                        print(f"[PINCODE-FIRST] Valid pincode '{valid_pincode}' -> Trigger city confirmation for '{display_city}' (canonical: '{canonical_city}')")

                    # Clear any invalid phone flag set by the same 6-digit input
                    if getattr(self.session, 'last_invalid_phone_input', None) == valid_pincode:
                        self.session.last_invalid_phone_input = None
            elif is_update_intent and is_pincode_edit_req:
                self.session.booking_slots["pincode"] = ""
                self.session.booking_slots["is_submitted"] = False
                self.session.slot_just_updated = False
                self.session.asking_for_field = "pincode"
            else:
                pin_digits = "".join(filter(str.isdigit, text))
                if pin_digits and len(pin_digits) in [3, 4, 5, 7, 8, 9] and getattr(self.session, 'asking_for_field', None) == "pincode":
                    self.session.last_invalid_pincode_input = pin_digits

            # Check if user requested other dentists (pagination) or asked for dentist names
            if is_asking_for_other_dentists(text) and self.session.booking_slots.get("pincode"):
                self.session.asking_for_field = "doctor_selection"
                self.session.is_other_dentists_requested = True
            elif is_asking_for_dentist_names(text) and not self.session.booking_slots.get("pincode"):
                self.session.pincode_asked_for_dentist = True
                self.session.asking_for_field = "pincode"
            elif is_asking_for_dentist_names(text) and self.session.booking_slots.get("pincode"):
                # User asked for dentist names / list and pincode is already known!
                self.session.asking_for_field = "doctor_selection"
                self.session.pincode_just_updated = True

            # ⚡ Step 2: Doctor detection in user text (evaluated using active/updated city) ⚡
            active_city = self.session.booking_slots.get("clinic_city") or self.session.booking_slots.get("city")
            # An ordinal ("the first one") refers to the list Riya just read out; check it before fuzzy name search
            doc_found = self._ordinal_dentist(text)
            if not doc_found:
                doc_found = find_doctor_in_text(text, active_city)
            if not doc_found:
                doc_found = find_doctor_in_text(text, city=None)
            # Also check against recommended dentists with robust fuzzy, phonetic, ordinal matching
            if not doc_found:
                doc_found = self._match_recommended_dentist(text)

            # If user wants to skip selecting a doctor or proceed to booking directly
            if not doc_found and (getattr(self.session, 'asking_for_field', None) == "doctor_selection" or getattr(self.session, 'recommended_dentists_spoken', False)):
                is_skip_doc = any(re.search(rf"\b{p}\b", text.lower()) for p in [
                    "book my appointment", "book appointment", "appointment book", "proceed", "continue",
                    "any doctor", "koi bhi doctor", "koi pan doctor", "no preference", "you choose", "you decide",
                    "clinic team", "skip", "aage badho", "aage", "chalega", "guide", "team will guide",
                    "anyone", "anybody", "any", "koi pan", "koi bhi", "assign doctor", "assign"
                ])
                if not is_skip_doc and getattr(self.session, 'doctor_guidance_asked', False):
                    # If guidance was already asked once and user says generic acknowledgement again
                    if text.lower().strip() in ["okay", "ookay", "ok", "fine", "sure", "yes", "ha", "haa", "chalega", "chalse"]:
                        is_skip_doc = True
                if is_skip_doc:
                    self.session.asking_for_field = "phone"
                    self.session.pending_doctor_candidate = None
            if doc_found:
                if self.session.booking_slots.get("doctor_name") != doc_found:
                    self.session.booking_slots["doctor_name"] = doc_found
                    self.session.booking_slots["is_submitted"] = False
                    self.session.slot_just_updated = True
                self.session.pending_doctor_candidate = None
                self.session.last_uncertified_doctor = None
                self.session.city_doctor_mismatch = None
                self.session.asking_for_field = None
                self.session.pincode_asked_for_dentist = False
                # No silent DB/CRM update here: a changed doctor marks the booking unsubmitted (above), and it reaches
                # the database only through a new review summary that the patient confirms with "submit"
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
            if not concern and locals().get('last_model_asked_concern') and len(text.strip()) >= 3 and not is_update_intent and not is_affirmative_submit(text):
                # Fallback: User directly answered Riya's question asking what dental concern or smile goal they have
                t_lower = text.lower().strip()
                if not any(k in t_lower for k in ["naam", "name", "dr", "doctor", "submit", "cancel", "pincode"]):
                    concern = text.strip()

            if concern:
                # Riya no longer asks "your name is X, right?"; moving on to the concern accepts the name
                if self.session.user_name:
                    self.session.name_confirmed = True
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
            
            # Check if user explicitly declined consultation
            decline_words = [
                "don't want to book", "dont want to book", "do not want to book", "no booking",
                "no appointment", "not now", "no consultation", "nahi karni", "nahi karwani",
                "nahi chahiye", "abhi nahi", "nahi book", "nathi karvi", "nathi joiye", "nathi karvavvu",
                "just explain", "sirf batao", "khali samjav", "only explain", "not interested",
                "vadhu nahi", "nahi karvani"
            ]
            t_clean = text.lower().strip()
            if any(dw in t_clean for dw in decline_words) or (t_clean in ["no", "nahi", "nathi", "na", "no thanks"]):
                self.session.consultation_declined = True
                self.session.consultation_agreed = False

            # Check if user agreed to consultation or initiated booking
            booking_words = ["book", "appointment", "consultation", "अपॉइंटमेंट", "અપૉઇન્ટમેન્ટ", "મુલાકાત", "बुक", "करा दो", "कर दो", "બુક કરો", "બુકિંગ"]
            if any(w in text.lower() for w in booking_words):
                self.session.consultation_agreed = True
                self.session.profession_asked = True
                if not self.session.booking_slots.get("pincode"):
                    self.session.asking_for_field = "pincode"
            elif self.session.user_concern and not self.session.booking_slots.get("pincode"):
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
                        self.session.profession_asked = True
                        if not self.session.booking_slots.get("pincode"):
                            self.session.asking_for_field = "pincode"
            if self.session.booking_slots.get("city") or self.session.booking_slots.get("pincode"):
                self.session.consultation_agreed = True
                self.session.profession_asked = True

            # Track whether profession was asked by Riya or shared by user
            prof_triggers = [
                "what do you do for work", "what is your profession", "aap kya kaam karte",
                "tame su kaam karo", "tame shu kaam karo", "tamaro vyavasay", "aapka pesha",
                "aapka profession", "profession", "व्यवसाय", "पेशा", "પ્રોફેશન",
                "કામ કરો છો", "काम करते हैं", "काम करते हो", "તમે શું કામ કરો છો"
            ]
            prof_jobs = [
                "doctor", "dentist", "lawyer", "advocate", "teacher", "professor", "engineer", "developer",
                "receptionist", "salesperson", "sales", "nurse", "architect", "accountant", "ca", "pilot",
                "founder", "businessman", "business woman", "student", "housewife", "homemaker", "designer",
                "manager", "banker", "model", "actor", "actress", "photographer"
            ]
            ut_low = str(user_text or "").lower()
            if any(j in ut_low for j in prof_jobs) and any(w in ut_low for w in ["i am", "i'm", "im", "hoon", "hu", "chu", "chhu", "me", "main", "maro", "mera"]):
                self.session.profession_asked = True

            if history and isinstance(history, list):
                for h in history:
                    h_txt = ""
                    if isinstance(h, dict):
                        parts = h.get("parts", [])
                        if parts and isinstance(parts[0], dict) and "text" in parts[0]:
                            h_txt = parts[0]["text"].lower()
                        elif isinstance(h.get("text"), str):
                            h_txt = h.get("text", "").lower()
                    if h_txt and any(pt in h_txt for pt in prof_triggers):
                        self.session.profession_asked = True
                        break


    async def stream_chat_text_response(self, user_text, history, system_prompt):
        """⚡ Blazing fast sub-second Gemini 3.5 Flash Lite streaming specifically for Chat Mode ⚡"""
        # Worker thread: slot parsing can make blocking postal/dentist API calls
        await asyncio.to_thread(self.update_session_memory, user_text, history)
        
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
        user_lang = detect_user_language(user_text, history, getattr(self.session, 'current_language', None))
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
            f"Every response MUST begin with the tag [{user_lang}-IN]. Example: '[{user_lang}-IN] ...'. "
            f"DO NOT switch, mix, or drift into Hindi, Gujarati, or English unless the patient explicitly spoke in that language in this turn.\n"
            f"🚨 ONE QUESTION PER REPLY: your reply may contain only ONE question. Never combine two asks (e.g. name confirmation + concern, concern + consultation offer, city confirmation + profession, dentist names + phone number).\n"
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
                f"No matter what topic was discussed or what question the user asked, your follow-up question at the end of this response MUST COMPULSORILY BE to ask what their profession is in {lang_display}: '{prof_q}'. It must be the ONLY question in this reply.\n"
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

        patient_pincode = self.session.booking_slots.get("pincode")
        if patient_pincode:
            active_memory += f"\n- CURRENT CONFIRMED AREA PINCODE: {patient_pincode} (Confirmed 6-digit area pincode. Do NOT re-ask)."
        elif getattr(self.session, 'last_invalid_pincode_input', None):
            active_memory += f"\n- CURRENT PATIENT PINCODE: INVALID INPUT ({self.session.last_invalid_pincode_input} is not a 6-digit area pincode). Politely re-ask: 'Please provide your complete 6-digit area pincode'."
        else:
            active_memory += "\n- CURRENT PATIENT PINCODE: Unknown (User has not provided their 6-digit area pincode yet. Mandatory to ask)."

        if getattr(self.session, 'recommended_dentists', None) and patient_pincode:
            from voice_agent.services.dentist_service import format_dentist_recommendation_prompt
            active_memory += "\n" + format_dentist_recommendation_prompt(
                self.session.recommended_dentists,
                patient_pincode,
                getattr(self.session, 'dentist_page_offset', 0)
            )

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
        pin = self.session.booking_slots.get("pincode")
        cn = self.session.booking_slots.get("message") or self.session.user_concern
        dr = self.session.booking_slots.get("doctor_name")
        ph = self.session.booking_slots.get("phone")

        asking_field = getattr(self.session, 'asking_for_field', None)
        display_name = f"{fn} {ln}".strip() if (ln and ln != "-" and ln.lower() != fn.lower()) else (self.session.user_name or fn or "Patient")

        # ⚡ 0aa. State-to-City Clarification: If user provided an Indian State instead of City, ask for city inside that state!
        if getattr(self.session, 'state_clarification_needed', None):
            st = self.session.state_clarification_needed
            self.session.state_clarification_needed = None
            from voice_agent.services.dentist_service import format_state_to_city_speech
            speech_text = format_state_to_city_speech(st, user_lang)
            _turn = self.session.current_voice_turn_id
            _tag = detect_best_tag(user_text, speech_text)
            await self.send_json({"type": "sync_slots", "slots": self.session.booking_slots})
            await self.send_json({"type": "bot_text_chunk", "text": speech_text, "tag": _tag, "turnId": _turn})
            await self.send_json({"type": "bot_spoken_text", "text": speech_text, "tag": _tag, "turnId": _turn})
            await self.send_json({
                "type": "reply_complete",
                "userText": user_text,
                "botText": speech_text,
                "tag": _tag,
                "totalChunks": 1,
                "slots": dict(self.session.booking_slots),
                "userName": self.session.user_name,
                "userConcern": self.session.user_concern,
                "userCity": "",
                "userDoctor": self.session.booking_slots.get("doctor_name"),
                "userPhone": self.session.booking_slots.get("phone"),
                "userPincode": self.session.booking_slots.get("pincode")
            })
            self.session.add_transcript_turn("model", speech_text)
            print(f"[STATE-CLARIFICATION-SENT] Sent directly: {speech_text[:100]}")
            return

        # ⚡ 0a. City Updated after mismatch or clarification: Prompt immediately for new city's area pincode
        if getattr(self.session, 'city_updated_need_pincode', False):
            self.session.city_updated_need_pincode = False
            self.session.asking_for_field = "pincode"
            from voice_agent.services.dentist_service import format_city_updated_speech
            active_c = self.session.booking_slots.get("city") or ct or ""
            speech_text = format_city_updated_speech(active_c, user_lang)
            _turn = self.session.current_voice_turn_id
            _tag = detect_best_tag(user_text, speech_text)
            await self.send_json({"type": "sync_slots", "slots": self.session.booking_slots})
            await self.send_json({"type": "bot_text_chunk", "text": speech_text, "tag": _tag, "turnId": _turn})
            await self.send_json({"type": "bot_spoken_text", "text": speech_text, "tag": _tag, "turnId": _turn})
            await self.send_json({
                "type": "reply_complete",
                "userText": user_text,
                "botText": speech_text,
                "tag": _tag,
                "totalChunks": 1,
                "slots": dict(self.session.booking_slots),
                "userName": self.session.user_name,
                "userConcern": self.session.user_concern,
                "userCity": self.session.booking_slots.get("city"),
                "userDoctor": self.session.booking_slots.get("doctor_name"),
                "userPhone": self.session.booking_slots.get("phone"),
                "userPincode": ""
            })
            self.session.add_transcript_turn("model", speech_text)
            print(f"[CITY-UPDATED-SENT] Sent directly: {speech_text[:100]}")
            return

        # ⚡ 0a. Invalid Pincode check: If invalid/unregistered pincode entered, reject immediately
        if getattr(self.session, 'pincode_invalid', False):
            self.session.pincode_invalid = False
            from voice_agent.services.dentist_service import format_invalid_pincode_speech
            bad_pin = getattr(self.session, 'last_invalid_pincode_input', '') or ''
            speech_text = format_invalid_pincode_speech(bad_pin, user_lang)
            _turn = self.session.current_voice_turn_id
            _tag = detect_best_tag(user_text, speech_text)
            await self.send_json({"type": "sync_slots", "slots": self.session.booking_slots})
            await self.send_json({"type": "bot_text_chunk", "text": speech_text, "tag": _tag, "turnId": _turn})
            await self.send_json({"type": "bot_spoken_text", "text": speech_text, "tag": _tag, "turnId": _turn})
            await self.send_json({
                "type": "reply_complete",
                "userText": user_text,
                "botText": speech_text,
                "tag": _tag,
                "totalChunks": 1,
                "slots": dict(self.session.booking_slots),
                "userName": self.session.user_name,
                "userConcern": self.session.user_concern,
                "userCity": self.session.booking_slots.get("city"),
                "userDoctor": self.session.booking_slots.get("doctor_name"),
                "userPhone": self.session.booking_slots.get("phone"),
                "userPincode": ""
            })
            self.session.add_transcript_turn("model", speech_text)
            print(f"[PINCODE-INVALID-SENT] Sent directly: {speech_text[:100]}")
            return

        # ⚡ 0aa. Invalid Phone check: If non-10-digit phone entered (e.g. 9 digits like 984255299), reject immediately
        if getattr(self.session, 'phone_invalid', False):
            self.session.phone_invalid = False
            from voice_agent.services.dentist_service import format_invalid_phone_speech
            bad_ph = getattr(self.session, 'last_invalid_phone_input', '') or ''
            speech_text = format_invalid_phone_speech(bad_ph, user_lang)
            _turn = self.session.current_voice_turn_id
            _tag = detect_best_tag(user_text, speech_text)
            await self.send_json({"type": "sync_slots", "slots": self.session.booking_slots})
            await self.send_json({"type": "bot_text_chunk", "text": speech_text, "tag": _tag, "turnId": _turn})
            await self.send_json({"type": "bot_spoken_text", "text": speech_text, "tag": _tag, "turnId": _turn})
            await self.send_json({
                "type": "reply_complete",
                "userText": user_text,
                "botText": speech_text,
                "tag": _tag,
                "totalChunks": 1,
                "slots": dict(self.session.booking_slots),
                "userName": self.session.user_name,
                "userConcern": self.session.user_concern,
                "userCity": self.session.booking_slots.get("city"),
                "userDoctor": self.session.booking_slots.get("doctor_name"),
                "userPhone": self.session.booking_slots.get("phone"),
                "userPincode": self.session.booking_slots.get("pincode")
            })
            self.session.add_transcript_turn("model", speech_text)
            print(f"[PHONE-INVALID-SENT] Sent directly: {speech_text[:100]}")
            return

        # ⚡ 0b. City confirmation from Pincode check: Prompt user to confirm city based on pincode
        if getattr(self.session, 'city_confirm_needed', False):
            from voice_agent.services.dentist_service import format_city_confirm_speech
            p_pin = getattr(self.session, 'pending_pincode', '') or ''
            p_cit = getattr(self.session, 'pending_display_city', '') or getattr(self.session, 'pending_city', '') or ''
            speech_text = format_city_confirm_speech(p_pin, p_cit, user_lang)
            _turn = self.session.current_voice_turn_id
            _tag = detect_best_tag(user_text, speech_text)
            await self.send_json({"type": "sync_slots", "slots": self.session.booking_slots})
            await self.send_json({"type": "bot_text_chunk", "text": speech_text, "tag": _tag, "turnId": _turn})
            await self.send_json({"type": "bot_spoken_text", "text": speech_text, "tag": _tag, "turnId": _turn})
            await self.send_json({
                "type": "reply_complete",
                "userText": user_text,
                "botText": speech_text,
                "tag": _tag,
                "totalChunks": 1,
                "slots": dict(self.session.booking_slots),
                "userName": self.session.user_name,
                "userConcern": self.session.user_concern,
                "userCity": p_cit,
                "userDoctor": self.session.booking_slots.get("doctor_name"),
                "userPhone": self.session.booking_slots.get("phone"),
                "userPincode": p_pin
            })
            self.session.add_transcript_turn("model", speech_text)
            print(f"[CITY-CONFIRM-SENT] Sent directly: {speech_text[:100]}")
            return

        # ⚡ 0. City-Pincode Mismatch check: If mismatch detected, reject immediately with clarification prompt
        if getattr(self.session, 'city_pincode_mismatch', False):
            from voice_agent.services.dentist_service import format_city_pincode_mismatch_speech
            m_data = getattr(self.session, 'city_pincode_mismatch_data', {}) or {}
            m_city = self.session.booking_slots.get("city") or m_data.get("city", ct or "")
            m_pin = m_data.get("pincode", "")
            m_det = m_data.get("detected_city", "")
            speech_text = format_city_pincode_mismatch_speech(m_city, m_pin, m_det, user_lang)
            _turn = self.session.current_voice_turn_id
            _tag = detect_best_tag(user_text, speech_text)
            await self.send_json({"type": "sync_slots", "slots": self.session.booking_slots})
            await self.send_json({"type": "bot_text_chunk", "text": speech_text, "tag": _tag, "turnId": _turn})
            await self.send_json({"type": "bot_spoken_text", "text": speech_text, "tag": _tag, "turnId": _turn})
            await self.send_json({
                "type": "reply_complete",
                "userText": user_text,
                "botText": speech_text,
                "tag": _tag,
                "totalChunks": 1,
                "slots": dict(self.session.booking_slots),
                "userName": self.session.user_name,
                "userConcern": self.session.user_concern,
                "userCity": self.session.booking_slots.get("city"),
                "userDoctor": self.session.booking_slots.get("doctor_name"),
                "userPhone": self.session.booking_slots.get("phone"),
                "userPincode": ""
            })
            self.session.add_transcript_turn("model", speech_text)
            print(f"[PINCODE-MISMATCH-SENT] Sent directly: {speech_text[:100]}")
            return

        # ⚡ 0. Travel destination dentist speech check (e.g. user from Bhavnagar wants appointment in Surat)
        if getattr(self.session, 'is_travel_booking_turn', False):
            self.session.is_travel_booking_turn = False
            from voice_agent.services.dentist_service import format_travel_dentists_speech_text, get_nearest_dentists_for_travel
            p_city = self.session.booking_slots.get("city") or ""
            p_pin = self.session.booking_slots.get("pincode") or ""
            t_city = getattr(self.session, 'travel_destination_city', "") or self.session.booking_slots.get("clinic_city") or "Surat"
            dentists_now = getattr(self.session, 'recommended_dentists', [])
            if not dentists_now:
                import asyncio as _asyncio
                dentists_now = await _asyncio.to_thread(get_nearest_dentists_for_travel, p_pin, p_city, t_city)
                self.session.recommended_dentists = dentists_now

            speech_text = format_travel_dentists_speech_text(
                dentists_now, p_city, t_city, user_lang
            )
            print(f"[TRAVEL-DENTIST-SPEECH] speech_text={speech_text!r}")
            if speech_text:
                self.session.recommended_dentists_spoken = True
                self.session._dentist_fastpath_text = None
                self.session.asking_for_field = "doctor_selection"
                _turn = self.session.current_voice_turn_id
                _tag = detect_best_tag(user_text, speech_text)
                await self.send_json({"type": "sync_slots", "slots": self.session.booking_slots})
                await self.send_json({"type": "bot_text_chunk", "text": speech_text, "tag": _tag, "turnId": _turn})
                await self.send_json({"type": "bot_spoken_text", "text": speech_text, "tag": _tag, "turnId": _turn})
                await self.send_json({
                    "type": "reply_complete",
                    "userText": user_text,
                    "botText": speech_text,
                    "tag": _tag,
                    "totalChunks": 1,
                    "slots": dict(self.session.booking_slots),
                    "userName": self.session.user_name,
                    "userConcern": self.session.user_concern,
                    "userCity": self.session.booking_slots.get("city"),
                    "userDoctor": self.session.booking_slots.get("doctor_name"),
                    "userPhone": self.session.booking_slots.get("phone"),
                    "userPincode": self.session.booking_slots.get("pincode")
                })
                self.session.add_transcript_turn("model", speech_text)
                print(f"[TRAVEL-DENTIST-SENT] Sent directly: {speech_text[:100]}")
                return

        # ⚡ 1. Direct dentist speech check: If user entered pincode or requested other options, handle direct-send
        # ⚡ 1. Direct dentist speech check: ONLY speak dentists when pincode and city are confirmed!
        is_pincode_turn = bool(getattr(self.session, 'pincode_just_updated', False) and not getattr(self.session, 'city_confirm_needed', False) and not getattr(self.session, 'pincode_invalid', False))
        is_other = is_asking_for_other_dentists(user_text) or getattr(self.session, 'is_other_dentists_requested', False)
        is_doc_req = is_asking_for_dentist_names(user_text) and bool(pin)
        self.session.is_other_dentists_requested = False
        active_pin = pin or (extract_valid_pincode(user_text, phone=self.session.booking_slots.get("phone")) if not getattr(self.session, 'city_confirm_needed', False) and not getattr(self.session, 'pincode_invalid', False) else "")
        is_sub_cmd = is_explicit_submit_command(user_text)
        is_dentist_needed = (
            not getattr(self.session, 'city_pincode_mismatch', False) and
            not getattr(self.session, 'city_confirm_needed', False) and
            not getattr(self.session, 'pincode_invalid', False) and
            not is_sub_cmd and (
                is_pincode_turn or
                (is_other and bool(active_pin)) or
                (is_doc_req and bool(active_pin)) or
                (bool(active_pin) and not dr and not getattr(self.session, 'recommended_dentists_spoken', False))
            )
        )
        if is_dentist_needed and active_pin:
            # ⚡ DENTIST DIRECT-SEND: Fetch names and send immediately — DO NOT go through Gemini ⚡
            from voice_agent.services.dentist_service import format_dentists_speech_text, get_nearest_dentists
            is_pincode_update = bool(getattr(self.session, 'pincode_was_changed', False))
            self.session.pincode_just_updated = False
            self.session.pincode_was_changed = False
            self.session.booking_slots["pincode"] = active_pin
            try:
                import asyncio as _asyncio
                _offset = getattr(self.session, 'dentist_page_offset', 0)
                if is_other:
                    _offset += 3
                else:
                    _offset = 0
                dentist_slice, _total, _next_off = await _asyncio.to_thread(get_nearest_dentists, active_pin, _offset, 3)
                self.session.recommended_dentists = dentist_slice
                self.session.dentist_page_offset = _offset

                # Infer city from pincode location ONLY if user has not provided a city yet
                if not self.session.booking_slots.get("city"):
                    from voice_agent.services.dentist_service import get_location_for_pincode
                    loc = get_location_for_pincode(active_pin)
                    if loc and loc.get("district"):
                        self.session.booking_slots["city"] = loc["district"]

                print(f"[DENTIST-FETCH] Got {len(dentist_slice)} dentists for pincode {active_pin} (offset={_offset}, city={self.session.booking_slots.get('city')})")
            except Exception as _fetch_err:
                print(f"[DENTIST-FETCH-WARN] {_fetch_err}")

            dentists_now = getattr(self.session, 'recommended_dentists', [])
            speech_text = format_dentists_speech_text(
                dentists_now, active_pin or "", user_lang, 
                is_more=is_other, is_update=is_pincode_update, 
                user_city=self.session.booking_slots.get("city")
            )
            print(f"[DENTIST-SPEECH] speech_text={speech_text!r}")
            if speech_text:
                # ✅ SEND DIRECTLY — bypass Gemini entirely for this turn
                self.session.recommended_dentists_spoken = True
                self.session._dentist_fastpath_text = None
                self.session.asking_for_field = "doctor_selection"
                _turn = self.session.current_voice_turn_id
                _tag = detect_best_tag(user_text, speech_text)
                await self.send_json({"type": "sync_slots", "slots": self.session.booking_slots})
                await self.send_json({"type": "bot_text_chunk", "text": speech_text, "tag": _tag, "turnId": _turn})
                await self.send_json({"type": "bot_spoken_text", "text": speech_text, "tag": _tag, "turnId": _turn})
                await self.send_json({
                    "type": "reply_complete",
                    "userText": user_text,
                    "botText": speech_text,
                    "tag": _tag,
                    "totalChunks": 1,
                    "slots": dict(self.session.booking_slots),
                    "userName": self.session.user_name,
                    "userConcern": self.session.user_concern,
                    "userCity": self.session.booking_slots.get("city"),
                    "userDoctor": self.session.booking_slots.get("doctor_name"),
                    "userPhone": self.session.booking_slots.get("phone"),
                    "userPincode": active_pin
                })
                self.session.add_transcript_turn("model", speech_text)
                print(f"[DENTIST-SENT] Sent directly: {speech_text[:100]}")
                return
            # Fallback: dentists unavailable — let Gemini handle with instruction
            self.session.recommended_dentists_spoken = True
            self.session._dentist_fastpath_text = None

        is_direct_doc_inquiry = getattr(self.session, 'pincode_asked_for_dentist', False) or is_asking_for_dentist_names(user_text)

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
                f"STEP 1 -> 2 (GREET BY NAME + DENTAL CONCERN, ONE QUESTION ONLY):\n"
                f"The patient shared their name '{display_name}'. Greet them by name and ask ONLY about their dental concern in {user_lang}. Do NOT ask them to confirm their name:\n"
                f"• Gujarati: 'નમસ્તે {display_name}! તમારા દાંત કે સ્માઇલમાં તમને શું સમસ્યા આવી રહી છે?'\n"
                f"• Hindi: 'नमस्ते {display_name}! आपके दाँतों या स्माइल में आपको क्या समस्या आ रही है?'\n"
                f"• English: 'Nice to meet you, {display_name}! What specific concern or goal do you have regarding your teeth or smile?'\n"
                f"🚨 MANDATORY: Do NOT jump to city, doctor, pincode, or review summary yet."
            )
        elif asking_field == "name":
            next_step_instruction = f"STEP 1 (NAME UPDATE): The patient wants to update their name. Do NOT present the review summary yet. Ask for their correct full name in {user_lang}: 'Sure! What is your correct full name?' ('ચોક્કસ! તમારું સાચું પૂરું નામ શું છે?')."
        elif is_direct_doc_inquiry and not getattr(self.session, 'consultation_agreed', False):
            if not pin:
                next_step_instruction = (
                    f"DIRECT INQUIRY FOR DENTIST NAMES (PINCODE REQUIRED FIRST):\n"
                    f"The patient directly asked for USD Certified Smile Designer / dentist names before booking an appointment.\n"
                    f"You MUST ask for their 6-digit area pincode first so you can find their nearest USD Certified Smile Designer:\n"
                    f"• English: 'To help find your nearest USD Certified Smile Designer, could you please tell me your 6-digit area pincode?'\n"
                    f"• Gujarati: 'તમારા સૌથી નજીકના USD સર્ટિફાઇડ સ્માઇલ ડિઝાઇનર શોધવા માટે, કૃપા કરીને તમારા વિસ્તારનો 6 અંકનો પિનકોડ જણાવશો?'\n"
                    f"• Hindi: 'आपके सबसे नजदीकी USD सर्टिफाइड स्माइल डिज़ाइनर ढूंढने के लिए, कृपया अपने क्षेत्र का 6 अंकों का पिनकोड बता दीजिए?'"
                )
            else:
                from voice_agent.services.dentist_service import format_dentists_speech_text
                speech_rec = format_dentists_speech_text(
                    getattr(self.session, 'recommended_dentists', []), 
                    pin, 
                    user_lang,
                    user_city=self.session.booking_slots.get("city")
                )
                next_step_instruction = (
                    f"DIRECT INQUIRY FOR DENTIST NAMES (SPEAK 3 NEAREST DENTISTS + OFFER BOOKING):\n"
                    f"Speak the 3 nearest USD Certified Smile Designers for pincode {pin}, and then ask if we should continue their appointment booking with one of these dentists:\n"
                    f"'{speech_rec}'\n"
                    f"Follow-up question in {user_lang}: 'Should we continue with your appointment booking with one of these dentists?'\n"
                    f"• Gujarati: 'શું આપણે આમાંથી કોઈ ડૉક્ટર સાથે તમારી અપૉઇન્ટમેન્ટ બુકિંગ આગળ વધારીએ?'\n"
                    f"• Hindi: 'क्या हम इनमें से किसी डॉक्टर के साथ आपकी अपॉइंटमेंट बुकिंग आगे बढ़ाएं?'\n"
                    f"• English: 'Should we continue with your appointment booking with one of these dentists?'"
                )
        elif not cn or asking_field == "concern":
            next_step_instruction = (
                f"STEP 2 (CONVERSATIONAL CONSULTATION & CONCERN EXPLORATION): The patient's name is '{display_name}'.\n"
                f"- If the patient is asking about or exploring our Smile Design philosophy, porcelain veneers, Adele craft, or good vs superior smile: Answer their question thoroughly, warmly, and educationally in {user_lang} as an expert AI Smile Consultant!\n"
                f"- If the patient shares their profession (doctor, lawyer, teacher, engineer, etc.): Connect their profession naturally using the appropriate profession analogy from the knowledge base without any cosmetic pressure or forcing booking.\n"
                f"- If the patient has not stated any dental concern or smile goal yet and you need to ask: Ask what specific concern or smile goal they have in {user_lang}: 'What specific concern or issue are you experiencing with your teeth or smile, {display_name}?' ('તમને તમારા દાંત કે સ્માઇલ વિશે કઈ સમસ્યા છે, {display_name}?').\n"
                f"🚨 MANDATORY: DO NOT ask for City, Pincode, or Doctor yet! DO NOT force appointment booking until they express a specific dental concern or request booking!"
            )
        elif not getattr(self.session, 'consultation_agreed', False) and not ct:
            if getattr(self.session, "consultation_declined", False) or getattr(self.session, "consultation_offered", False):
                next_step_instruction = (
                    f"SMILE CONSULTATION & EXPLORATION (CONSULTATION ALREADY OFFERED / DECLINED):\n"
                    f"The patient '{display_name}' has either declined appointment booking or consultation was already offered once.\n"
                    f"🚨 CRITICAL MANDATORY: DO NOT ask to book an appointment or consultation again! ONCE IS ENOUGH!\n"
                    f"DO NOT ask for City, Pincode, Doctor, or Phone!\n"
                    f"Converse purely as an expert, caring AI Smile Consultant: answer their dental questions, explain USD treatments, philosophy, or veneers helpfully, and converse naturally without pushing appointments or booking!"
                )
            else:
                self.session.consultation_offered = True
                next_step_instruction = (
                    f"STEP 2.5 (MESSAGE 4 - CONCERN ACKNOWLEDGEMENT & CONSULTATION OFFER - MANDATORY PERMISSION GATE):\n"
                    f"The patient '{display_name}' revealed their dental concern: '{cn}'.\n"
                    f"Empathetically acknowledge their specific concern in {user_lang} and ask if they would like you to help book a consultation appointment with our USD Certified Smile Designer to resolve it!\n"
                    f"🚨 CRITICAL MANDATORY GATE: DO NOT ask for profession yet in Message 4! DO NOT start booking, DO NOT ask for City, Pincode, or Doctor yet in this turn until the patient explicitly says YES or agrees!\n"
                    f"🚨 ONCE IS ENOUGH: If the patient declines, says no, or asks a question, NEVER RE-ASK for consultation booking again!\n"
                    f"• Gujarati: 'હું સમજી શકું છું કે તમને {cn}ની સમસ્યા છે, {display_name}. શું હું આના ઉકેલ માટે અમારા USD સર્ટિફાઇડ સ્માઇલ ડિઝાઇનર સાથે કન્સલ્ટેશન અપૉઇન્ટમેન્ટ બુક કરવામાં મદદ કરું?'\n"
                    f"• Hindi: 'मैं समझ सकती हूँ कि आपको {cn} की समस्या आ रही है, {display_name}। क्या मैं इसके समाधान के लिए हमारे USD सर्टिफाइड स्माइल डिज़ाइनर के साथ अपॉइंटमेंट बुक करने में आपकी मदद करूँ?'\n"
                    f"• English: 'I understand you are experiencing {cn}, {display_name}. Would you like me to help book a consultation appointment with our USD Certified Smile Designer for this?'"
                )
        elif getattr(self.session, 'city_confirm_needed', False) or asking_field == "city_confirmation":
            self.session.asking_for_field = "city_confirmation"
            p_pin = getattr(self.session, 'pending_pincode', '') or pin or ''
            p_cit = getattr(self.session, 'pending_display_city', '') or getattr(self.session, 'pending_city', '') or ct or 'your'
            next_step_instruction = (
                f"STEP 3.5 (CONFIRM CITY FROM PINCODE):\n"
                f"The patient provided 6-digit pincode '{p_pin}'. Indian postal records indicate this is in '{p_cit}' area.\n"
                f"Ask the patient to confirm if they reside in '{p_cit}' area in {user_lang}:\n"
                f"• Gujarati: 'તમારા પિનકોડ {p_pin} મુજબ, તમે {p_cit} વિસ્તારમાં રહો છો, બરાબર ને?'\n"
                f"• Hindi: 'आपके पिनकोड {p_pin} के अनुसार, आप {p_cit} क्षेत्र में रहते हैं, सही ना?'\n"
                f"• English: 'Based on your pincode {p_pin}, you reside in {p_cit} area, right?'\n"
                f"🚨 CRITICAL MANDATORY: Once confirmed, lock city and pincode, then recommend the 3 nearest USD Certified Smile Designers!"
            )
        elif not pin or asking_field == "pincode":
            self.session.asking_for_field = "pincode"
            next_step_instruction = (
                f"STEP 3 (6-DIGIT AREA PINCODE FIRST):\n"
                f"The patient '{display_name}' has agreed to consultation for concern '{cn}'.\n"
                f"Ask for their 6-digit area pincode in {user_lang} so you can identify their area and find their nearest USD Certified Smile Designer:\n"
                f"• Gujarati: 'તમારા સૌથી નજીકના USD સર્ટિફાઇડ સ્માઇલ ડિઝાઇનર શોધવા માટે, તમારા વિસ્તારનો 6 અંકનો પિનકોડ જણાવશો?'\n"
                f"• Hindi: 'आपके सबसे नजदीकी USD सर्टिफाइड स्माइल डिज़ाइनर ढूंढने के लिए, आपके क्षेत्र का 6 अंकों का पिनकोड क्या है?'\n"
                f"• English: 'Great, {display_name}! To help find your nearest USD Certified Smile Designer, could you please tell me your 6-digit area pincode?'\n"
                f"🚨 CRITICAL MANDATORY: Pincode must be 6 digits. Do NOT ask for city or doctor yet!"
            )
        elif not ct or asking_field == "city":
            self.session.asking_for_field = "city"
            next_step_instruction = (
                f"STEP 3.5 (CITY / RESIDENCE LOCATION): Ask which city they reside in {user_lang}: 'Which city do you reside in?' ('તમે કયા શહેરમાં રહો છો?')."
            )
        elif not dr and (asking_field in ["doctor", "doctor_selection"] or getattr(self.session, 'recommended_dentists_spoken', False)):
            doc_list = getattr(self.session, 'recommended_dentists', [])
            doc_names_list = [d.get('name') for d in doc_list if d.get('name')]
            doc_names_hint = ", ".join(doc_names_list[:3]) if doc_names_list else "the doctors mentioned"

            is_generic_ok = user_text.lower().strip() in [
                "okay", "ookay", "ok", "k", "fine", "sure", "yes", "yeah", "yep",
                "ha", "haa", "haan", "theek", "theek hai", "thik hai", "thik",
                "saaru", "saru", "barabar", "acha", "achha", "right"
            ]
            is_generic_no = user_text.lower().strip() in [
                "no", "nah", "nope", "na", "naa", "nahi", "nahin", "nathi",
                "nahi chahiye", "nathi joie", "nathi joitu", "nathi karvu", "nahi karna",
                "reva do", "rehvado", "reva dyo", "chhod do", "mat karo", "na karsho",
                "not interested", "dont want", "don't want", "dont book", "don't book",
                "no thanks", "no thank you", "reva de"
            ] or any(user_text.lower().strip().startswith(p + " ") or user_text.lower().strip().endswith(" " + p) for p in ["no", "nah", "nahi", "nathi", "reva do", "no thanks"])
            was_guidance_asked = getattr(self.session, 'doctor_guidance_asked', False)

            if is_generic_no:
                self.session.consultation_declined = True
                self.session.asking_for_field = None
                self.session.doctor_guidance_asked = False
                self.session.recommended_dentists_spoken = False
                next_step_instruction = (
                    f"STEP 4 (PATIENT DECLINED CONSULTATION / SAID 'NO'):\n"
                    f"The patient explicitly declined consultation/appointment booking ('{user_text}').\n"
                    f"Warmly and gracefully acknowledge that there is no problem at all, and offer to assist with any general questions about smile design or treatments in {user_lang}:\n"
                    f"• English: 'No problem at all! We completely understand. If you have any other questions about your smile or wish to consult later, feel free to ask anytime. How else can I assist you today?'\n"
                    f"• Gujarati: 'ચોક્કસ, કોઈ વાંધો નહીં! અમે સમજી શકીએ છીએ. જો તમને સ્માઇલ ડિઝાઇન કે ટ્રીટમેન્ટ વિશે કોઈ પ્રશ્ન હોય અથવા ભવિષ્યમાં કન્સલ્ટ કરવું હોય, તો ગમે ત્યારે પૂછી શકો છો. આજે હું તમને બીજી કઈ રીતે મદદ કરી શકું?'\n"
                    f"• Hindi: 'बिल्कुल, कोई बात नहीं! हम समझ सकते हैं। यदि आपके मन में स्माइल डिज़ाइन या ट्रीटमेंट को लेकर कोई सवाल हो या आप कभी कंसल्ट करना चाहें, तो आप कभी भी पूछ सकते हैं। आज मैं आपकी और क्या मदद कर सकती हूँ?'\n"
                    f"🚨 ABSOLUTE MANDATORY BAN: DO NOT ask for phone number, DO NOT ask to book an appointment, and DO NOT name any doctors again!"
                )
            elif is_generic_ok and not was_guidance_asked:
                self.session.doctor_guidance_asked = True
                next_step_instruction = (
                    f"STEP 4 (DOCTOR SELECTION - USER SAID 'OKAY' / AFFIRMATIVE):\n"
                    f"The patient responded with an affirmative/acknowledgement ('{user_text}') without picking a specific doctor yet.\n"
                    f"Warmly ask which doctor they prefer from the list, or offer our team's guidance in {user_lang}:\n"
                    f"• English: 'Great! Which doctor would you like to choose: {doc_names_hint}? Or would you prefer our clinic team to assign the best specialist for you?'\n"
                    f"• Gujarati: 'સરસ! તમે આમાંથી કયા ડૉક્ટર પસંદ કરવા માંગો છો: {doc_names_hint}? અથવા અમારી ટીમ તમારા માટે યોગ્ય નિષ્ણાત નક્કી કરે?'\n"
                    f"• Hindi: 'बहुत बढ़िया! आप इनमें से किस डॉक्टर को चुनना चाहेंगे: {doc_names_hint}? या फिर हमारी टीम आपके लिए सबसे सही डॉक्टर तय करे?'"
                )
            elif is_generic_ok and was_guidance_asked:
                self.session.asking_for_field = "phone"
                next_step_instruction = (
                    f"STEP 5 (DOCTOR SELECTION CONFIRMED AS TEAM GUIDANCE + 10-DIGIT MOBILE NUMBER):\n"
                    f"The patient acknowledged ('{user_text}'). Accept clinic team guidance for doctor selection and immediately ask for their 10-digit mobile number in {user_lang}:\n"
                    f"• English: 'Wonderful! Our clinic team will connect you with the best available USD Certified Smile Designer. Could you please provide your 10-digit mobile phone number so our team can contact you?'\n"
                    f"• Gujarati: 'બહુ સરસ! અમારી ટીમ તમારા માટે યોગ્ય USD સર્ટિફાઇડ સ્માઇલ ડિઝાઇનર નક્કી કરશે. કૃપા કરીને તમારો 10 અંકનો મોબાઇલ નંબર જણાવશો જેથી અમારી ટીમ તમારો સંપર્ક કરી શકે?'\n"
                    f"• Hindi: 'बहुत बढ़िया! हमारी टीम आपके लिए सबसे उपयुक्त USD सर्टिफाइड स्माइल डिज़ाइनर तय करेगी। कृपया अपना 10 अंकों का मोबाइल नंबर बता दीजिए ताकि हमारी टीम आपसे संपर्क कर सके?'\n"
                    f"🚨 MANDATORY: DO NOT show review summary until a valid 10-digit mobile phone number is provided!"
                )
            else:
                next_step_instruction = (
                    f"STEP 4 (DOCTOR SELECTION - GUIDANCE):\n"
                    f"The 3 nearest USD Certified Smile Designers for pincode {pin} ({doc_names_hint}) have ALREADY been spoken to the patient.\n"
                    f"🚨 CRITICAL MANDATORY: DO NOT repeat or re-read the full 3 doctor names announcement again!\n"
                    f"Warmly ask the patient if they would like to consult with one of these doctors, or if they would prefer our clinic team to guide and assist them:\n"
                    f"• Gujarati: 'શું તમે આમાંથી કોઈ ડૉક્ટર સાથે કન્સલ્ટ કરવા માંગો છો, અથવા અમારી ટીમ તમને યોગ્ય નિષ્ણાત શોધવામાં માર્ગદર્શન આપે?'\n"
                    f"• Hindi: 'क्या आप इनमें से किसी डॉक्टर से कंसल्ट करना चाहेंगे, या हमारी टीम आपको सही डॉक्टर चुनने में मार्गदर्शन दे?'\n"
                    f"• English: 'Would you like to consult with one of these doctors, or would you prefer our clinic team to guide and assist you?'\n"
                    f"🚨 CRITICAL: If the patient says 'book my appointment', 'proceed', 'continue', 'any doctor', or skips choosing, accept it and immediately ask for their 10-digit mobile number!"
                )
        elif not ph or asking_field == "phone":
            if dr:
                next_step_instruction = (
                    f"STEP 5 (DOCTOR CONFIRMED: {dr} + MANDATORY 10-DIGIT MOBILE NUMBER):\n"
                    f"The patient selected '{dr}'. Skip asking for doctor name! Warmly confirm doctor '{dr}' and immediately ask for their 10-digit mobile number in {user_lang}:\n"
                    f"• Gujarati: 'બહુ સરસ! {dr} સાથે કન્સલ્ટેશન માટે, કૃપા કરીને તમારો 10 અંકનો મોબાઇલ નંબર જણાવશો જેથી અમારી ટીમ તમારો સંપર્ક કરી શકે?'\n"
                    f"• Hindi: 'बहुत बढ़िया! {dr} के साथ कंसल्टेशन के लिए, कृपया अपना 10 अंकों का मोबाइल नंबर बता दीजिए ताकि हमारी टीम आपसे संपर्क कर सके?'\n"
                    f"• English: 'Wonderful! For your consultation with {dr}, could you please provide your 10-digit mobile phone number so our clinic team can contact you?'\n"
                    f"🚨 MANDATORY: DO NOT show review summary until a valid 10-digit mobile phone number is provided!\n"
                    f"🚨 ZERO-CUTOFF MANDATE: Speak the full phone number question to the very last word!"
                )
            else:
                next_step_instruction = (
                    f"STEP 5 (MANDATORY 10-DIGIT MOBILE NUMBER):\n"
                    f"Doctor selection was skipped or left for clinic team guidance. Ask for their 10-digit mobile number in {user_lang} so our clinic team can contact them:\n"
                    f"• Gujarati: 'અમારી ટીમ તમારો સંપર્ક કરીને યોગ્ય ડૉક્ટર સાથે કન્સલ્ટેશન નક્કી કરવામાં મદદ કરશે. કૃપા કરીને તમારો 10 અંકનો મોબાઇલ નંબર જણાવશો જેથી અમારી ટીમ તમારો સંપર્ક કરી શકે?'\n"
                    f"• Hindi: 'हमारी टीम आपसे संपर्क करके उचित डॉक्टर से कंसल्टेशन में मदद करेगी। कृपया अपना 10 अंकों का मोबाइल नंबर बता दीजिए ताकि हमारी टीम आपसे संपर्क कर सके?'\n"
                    f"• English: 'Our clinic team will reach out to help connect you with the right specialist. Could you please provide your 10-digit mobile phone number so our team can contact you?'\n"
                    f"🚨 MANDATORY: DO NOT show review summary until a valid 10-digit mobile phone number is provided!\n"
                    f"🚨 ZERO-CUTOFF MANDATE: Speak the full phone number question to the very last word!"
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
                next_step_instruction = get_review_summary_prompt(user_lang, display_name, ph, ct, pin or (confirmed_review_slots.get("pincode") or "-"), cn, dr, is_update=is_update)

        active_memory += f"\n- STEP-BY-STEP ONE-QUESTION-AT-A-TIME DIRECTIVE:\n{next_step_instruction}\n(CRITICAL: Never re-ask details already confirmed. Ask ONLY the single missing step)."

        user_turn_count = len([h for h in (history or []) if isinstance(h, dict) and h.get("role") in ["user", "model", "assistant"]]) // 2
        if getattr(self.session, "profession_asked", False):
            active_memory += (
                "\n- 🚨 CRITICAL ONE-TIME PROFESSION RULE: The user's profession has ALREADY been asked or discussed! "
                "You are STRICTLY FORBIDDEN from asking 'what is your profession?' or 'what do you do for work?' again! "
                "Never ask about their profession again in this conversation."
            )
        elif user_turn_count < 4:
            active_memory += (
                "\n- 🚨 TIMING RULE FOR MESSAGES 1 TO 4: Do NOT ask about profession in messages 1, 2, 3, or 4! "
                "Focus on Greeting (Msg 1), Name Confirmation (Msg 2), Dental Concern (Msg 3), and Consultation Permission (Msg 4). "
                "Ask for their profession strictly at Message 5 (once consultation is agreed)."
            )
        else:
            active_memory += (
                "\n- 🌟 PROFESSION INQUIRY (MESSAGE 5 - MANDATORY EXACTLY ONCE): "
                "If not asked yet, warmly ask the patient about their work/profession in this turn (Message 5): "
                "('By the way, [Name], what do you do for work?' / 'તેમ છતાં, [Name], તમે શું કામ કરો છો?' / 'वैसे, [Name], आप क्या काम करते हैं?'). "
                "Remember: Once asked or provided, never repeat this question in future turns."
            )

        await self.send_json({
            "type": "sync_slots",
            "slots": self.session.booking_slots
        })

        # ⚡ Instant Fast-Path Submission / Cancellation when User Confirms Review Summary ⚡
        user_txt_l = user_text.lower().strip()
        is_affirmative = is_affirmative_submit(user_text)
        is_explicit_submit = is_explicit_submit_command(user_text)
        is_cancel = is_cancel_submit(user_text, self.session)

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
            if self.session.booking_slots.get("city"):
                rev_city = str(confirmed_review_slots.get("city", "")).strip().lower()
                cur_city = str(self.session.booking_slots.get("city", "")).strip().lower()
                if rev_city and cur_city and rev_city != cur_city:
                    confirmed_review_slots.pop("pincode", None)
                    confirmed_review_slots.pop("doctor_name", None)
            for k, v in confirmed_review_slots.items():
                if v and str(v).lower() not in ["none", "null", "-", "--"]:
                    # ONLY fill in if the session slot is currently empty,
                    # DO NOT overwrite user's actively updated slots!
                    if not self.session.booking_slots.get(k):
                        self.session.booking_slots[k] = v
            if confirmed_review_slots.get("user_name") and not self.session.user_name:
                self.session.user_name = confirmed_review_slots["user_name"]
            if (confirmed_review_slots.get("user_concern") or confirmed_review_slots.get("message")) and not self.session.user_concern:
                self.session.user_concern = confirmed_review_slots.get("user_concern") or confirmed_review_slots.get("message")
            if not self.session.booking_slots.get("message") and self.session.user_concern:
                self.session.booking_slots["message"] = self.session.user_concern

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
        has_pincode = bool(slots.get("pincode") and len("".join(filter(str.isdigit, str(slots["pincode"])))) == 6)
        has_doc = bool(slots.get("doctor_name") and slots["doctor_name"].strip() and slots["doctor_name"].lower() not in ["", "none", "null", "usd certified smile designer", "doctor", "dentist", "any", "not selected", "pending"])
        has_concern = bool(slots.get("message") and len(slots["message"].strip()) >= 3 and slots["message"].lower() not in ["none", "null", "dental consultation appointment request"])
        has_phone = bool(slots.get("phone") and len("".join(filter(str.isdigit, str(slots["phone"])))) == 10)

        all_slots_complete = has_fn and has_city and has_pincode and has_concern and has_phone
        is_already_submitted = bool(self.session.booking_slots.get("is_submitted") or self.session.booking_slots.get("submission_id"))

        has_rev_fn = bool(confirmed_review_slots.get("first_name") or confirmed_review_slots.get("user_name"))
        has_rev_ph = bool(confirmed_review_slots.get("phone") and len("".join(filter(str.isdigit, str(confirmed_review_slots["phone"])))) == 10)
        has_rev_city = bool(confirmed_review_slots.get("city"))
        has_rev_pin = bool(confirmed_review_slots.get("pincode") and len("".join(filter(str.isdigit, str(confirmed_review_slots["pincode"])))) == 6)
        has_rev_doc = bool(confirmed_review_slots.get("doctor_name"))
        has_rev_msg = bool(confirmed_review_slots.get("message") or confirmed_review_slots.get("user_concern"))
        is_full_review_ready = has_rev_fn and has_rev_ph and has_rev_city and has_rev_pin and has_rev_msg

        # If user explicitly requests submit or confirms submit after review summary, but ANY mandatory field is missing -> ask for missing field!
        has_review_shown = bool(last_rev_txt and is_submit_review_summary(last_rev_txt))
        if (is_explicit_submit or (is_affirmative and has_review_shown)) and not all_slots_complete and not is_cancel:
            if not has_fn:
                missing_msg = get_missing_field_message(user_lang, "name")
                self.session.asking_for_field = "name"
            elif not has_concern:
                missing_msg = get_missing_field_message(user_lang, "concern")
                self.session.asking_for_field = "concern"
            elif not has_pincode:
                missing_msg = get_missing_field_message(user_lang, "pincode")
                self.session.asking_for_field = "pincode"
            elif not has_city:
                missing_msg = get_missing_field_message(user_lang, "city")
                self.session.asking_for_field = "city"
            elif not has_phone:
                missing_msg = get_missing_field_message(user_lang, "phone")
                self.session.asking_for_field = "phone"
            else:
                missing_msg = get_missing_field_message(user_lang, "phone")
                self.session.asking_for_field = "phone"

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

        has_lead_context = bool(is_already_submitted or all_slots_complete or self.session.booking_slots.get("submission_id") or self.session.booking_slots.get("phone") or is_full_review_ready or (self.session.booking_slots.get("first_name") and self.session.booking_slots.get("city")))
        is_user_confirming_submit = False
        
        # If user requests cancellation and it was already cancelled, reply immediately
        if is_cancel and self.session.booking_slots.get("is_cancel"):
            already_cancel_msg = "Your appointment request has already been cancelled. Please let me know if you would like to book a new appointment or need any assistance."
            if user_lang in ["gu", "gujarati"]:
                already_cancel_msg = "તમારી એપોઇન્ટમેન્ટ વિનંતી પહેલેથી જ રદ કરવામાં આવી છે. જો તમને નવી એપોઇન્ટમેન્ટ બુક કરવી હોય અથવા અન્ય કોઈ સહાયની જરૂર હોય તો જણાવશો."
            elif user_lang in ["hi", "hindi"]:
                already_cancel_msg = "आपका अपॉइंटमेंट अनुरोध पहले ही रद्द कर दिया गया है। अगर आप नया अपॉइंटमेंट बुक करना चाहते हैं या कोई मदद चाहिए तो कृपया बताएं।"
            await self.send_json({
                "type": "bot_text_chunk",
                "text": already_cancel_msg,
                "tag": None,
                "turnId": self.session.current_voice_turn_id
            })
            await self.send_json({
                "type": "bot_spoken_text",
                "text": already_cancel_msg,
                "tag": None,
                "turnId": self.session.current_voice_turn_id
            })
            await self.send_json({
                "type": "reply_complete",
                "userText": user_text,
                "botText": already_cancel_msg,
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

        if is_cancel and has_lead_context:
            is_user_confirming_submit = True
        elif is_explicit_submit and all_slots_complete:
            is_user_confirming_submit = True
        elif is_affirmative and all_slots_complete and is_full_review_ready:
            is_user_confirming_submit = True
        elif is_cancel:
            # User wants to cancel but no lead was created yet
            self.session.booking_slots["is_cancel"] = True
            self.session.booking_slots["is_submitted"] = False
            confirm_msg = CONFIRMATION_CANCEL_MESSAGES_11.get(user_lang, CONFIRMATION_CANCEL_MESSAGES_11["en"])
            await self.send_json({
                "type": "bot_text_chunk",
                "text": confirm_msg,
                "tag": None,
                "turnId": self.session.current_voice_turn_id
            })
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

        if is_user_confirming_submit:
            action_type = "cancelling" if is_cancel else "submitting"
            
            submit_args = dict(self.session.booking_slots)
            # Ensure every field confirmed in review message is strictly used in payload
            if confirmed_review_slots:
                for k in ["first_name", "last_name", "phone", "city", "pincode", "doctor_name", "message"]:
                    if confirmed_review_slots.get(k):
                        submit_args[k] = confirmed_review_slots[k]
                        self.session.booking_slots[k] = confirmed_review_slots[k]
            
            # Strict submission guard: If not cancel, all mandatory fields must be present
            if not is_cancel:
                s_fn = bool(submit_args.get("first_name") and submit_args["first_name"].strip() and submit_args["first_name"].lower() not in ["", "none", "null", "patient", "user"])
                s_concern = bool(submit_args.get("message") and len(submit_args["message"].strip()) >= 2 and submit_args["message"].lower() not in ["none", "null", "dental consultation appointment request", ""])
                s_city = bool(submit_args.get("city") and len(str(submit_args["city"]).strip()) >= 2 and str(submit_args["city"]).lower() not in ["", "none", "null", "india"])
                s_pin = bool(submit_args.get("pincode") and len("".join(filter(str.isdigit, str(submit_args["pincode"])))) == 6)
                s_phone = bool(submit_args.get("phone") and len("".join(filter(str.isdigit, str(submit_args["phone"])))) == 10)
                
                if not (s_fn and s_concern and s_city and s_pin and s_phone):
                    missing_f = "phone"
                    if not s_fn: missing_f = "name"
                    elif not s_concern: missing_f = "concern"
                    elif not s_city: missing_f = "city"
                    elif not s_pin: missing_f = "pincode"
                    
                    missing_msg = get_missing_field_message(user_lang, missing_f)
                    self.session.asking_for_field = missing_f
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

            print(f"[INFO] Fast-path {action_type} appointment for {submit_args.get('first_name')} {submit_args.get('last_name')} in {submit_args.get('city')} (Pincode: {submit_args.get('pincode', '-')}) with {submit_args.get('doctor_name')} (Phone: {submit_args.get('phone')})...")
            
            await self.send_json({
                "type": "status_update",
                "status": "submitting",
                "text": f"Riya is {action_type}..."
            })
            
            sub_id = self.session.booking_slots.get("submission_id") or getattr(self.session, "submitted_lead_id", None)
            submit_args["is_cancel"] = is_cancel
            submit_args["is_update"] = bool(sub_id) or bool(self.session.booking_slots.get("is_submitted"))
            submit_args["submission_id"] = sub_id
            submit_args["id"] = sub_id
            if self.session.booking_slots.get("old_phone"):
                submit_args["old_phone"] = self.session.booking_slots.get("old_phone")
            if self.session.booking_slots.get("godaddy_id"):
                submit_args["godaddy_id"] = self.session.booking_slots.get("godaddy_id")
            if self.session.booking_slots.get("api_id"):
                submit_args["api_id"] = self.session.booking_slots.get("api_id")

            # ⚡ Attach full conversation transcript to appointment lead email ⚡
            transcript_text = self._build_transcript_text()
            if transcript_text:
                submit_args["transcript"] = transcript_text
            
            res = await submit_consultation_appointment(submit_args)
            if res.get("status") != "success":
                m_raw = res.get("missing_field", "phone")
                m_type = "name" if m_raw == "first_name" else ("concern" if m_raw == "message" else m_raw)
                missing_msg = get_missing_field_message(user_lang, m_type)
                self.session.asking_for_field = m_type
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

            if res.get("status") == "success":
                if is_cancel:
                    self.session.booking_slots["is_cancel"] = True
                    self.session.booking_slots["is_submitted"] = False
                else:
                    self.session.booking_slots["is_submitted"] = True
                if isinstance(res.get("details"), dict):
                    ret_id = res["details"].get("id") or res["details"].get("submission_id")
                    if ret_id:
                        self.session.booking_slots["submission_id"] = ret_id
                        self.session.submitted_lead_id = ret_id
                    if res["details"].get("godaddy_id"):
                        self.session.booking_slots["godaddy_id"] = res["details"]["godaddy_id"]
                    if res["details"].get("api_id"):
                        self.session.booking_slots["api_id"] = res["details"]["api_id"]

                # ⚡ Keep VoiceRecordingLog in sync with successful appointment submission ⚡
                try:
                    from voice_agent.models import VoiceRecordingLog
                    from asgiref.sync import sync_to_async
                    call_id = getattr(self.session, 'call_id', None)
                    if call_id:
                        doc_lbl = submit_args.get('doctor_name') or 'USD Dentist'
                        sub_id_val = self.session.booking_slots.get('submission_id')
                        sub_lbl = f"Lead #{sub_id_val}" if sub_id_val else "Submitted"
                        rating_str = f"Appointment Cancelled ({sub_lbl})" if is_cancel else f"Appointment Booked: {doc_lbl} ({sub_lbl})"

                        @sync_to_async
                        def update_log_on_submit():
                            log_rec = VoiceRecordingLog.objects.filter(call_id=call_id).first()
                            if log_rec:
                                log_rec.save_type = 'submit_feedback'
                                log_rec.rating = rating_str
                                log_rec.save()
                                print(f"[INFO] Synced VoiceRecordingLog #{log_rec.id} to submit_feedback ({rating_str})")

                        asyncio.create_task(update_log_on_submit())
                except Exception as log_up_err:
                    print(f"[WARN] Error updating VoiceRecordingLog on submit: {log_up_err}")
                
                await self.send_json({
                    "type": "sync_slots",
                    "slots": self.session.booking_slots
                })
            
            if is_cancel:
                confirm_msg = CONFIRMATION_CANCEL_MESSAGES_11.get(user_lang, CONFIRMATION_CANCEL_MESSAGES_11["en"])
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

        # ⚡ DENTIST FAST-PATH: Send doctor names DIRECTLY to client, bypassing Gemini ⚡
        # This guarantees real names are shown — Gemini was hallucinating generic text instead.
        _dentist_direct = getattr(self.session, '_dentist_fastpath_text', None)
        if _dentist_direct:
            self.session._dentist_fastpath_text = None  # clear flag
            _turn = self.session.current_voice_turn_id
            _tag = detect_best_tag(user_text, _dentist_direct)
            await self.send_json({"type": "bot_text_chunk", "text": _dentist_direct, "tag": _tag, "turnId": _turn})
            await self.send_json({"type": "bot_spoken_text", "text": _dentist_direct, "tag": _tag, "turnId": _turn})
            await self.send_json({
                "type": "reply_complete",
                "userText": user_text,
                "botText": _dentist_direct,
                "tag": _tag,
                "totalChunks": 1,
                "slots": dict(self.session.booking_slots),
                "userName": self.session.user_name,
                "userConcern": self.session.user_concern,
                "userCity": self.session.booking_slots.get("city"),
                "userDoctor": self.session.booking_slots.get("doctor_name"),
                "userPhone": self.session.booking_slots.get("phone")
            })
            self.session.add_transcript_turn("model", _dentist_direct)
            print(f"[DENTIST-FASTPATH] Sent directly to client: {_dentist_direct[:80]}...")
            return

        full_system_prompt = system_prompt
        full_system_prompt += (
            "\n\n=========================================\n"
            "🚨 CRITICAL SYSTEM MANDATE: ZERO-CUTOFF & FULL-LENGTH COMPLETENESS\n"
            "- You have an ample 800-token output limit. 'Concise' NEVER means cutting off sentences in half!\n"
            "- You are STRICTLY FORBIDDEN from stopping mid-sentence, dropping words, or leaving trailing dashes (e.g. NEVER stop at '. કૃપા કરીને તમારો—')!\n"
            "- EVERY sentence started MUST be completed to its final punctuation mark.\n"
            "- GREETINGS, PROFESSION INQUIRIES & FOLLOW-UPS, ASKING FOR DETAILS (CITY, DOCTOR, 10-DIGIT MOBILE NUMBER), REVIEW SUMMARIES, AND DETAILED EXPLANATIONS ('EXPLAIN IN DETAIL') MUST ALWAYS BE SPOKEN IN FULL LENGTH!\n"
            "========================================="
        )

        if active_memory:
            full_system_prompt += f"\n\n=========================================\nACTIVE PATIENT MEMORY (HIGH PRIORITY OVERRIDE):\n{active_memory}\n========================================="

        payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": full_system_prompt}]},
            "generationConfig": {
                "temperature": 0.25,
                "maxOutputTokens": 2048
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
                                                    call_args = func_call.get("args") or {}
                                                    gemini_is_cancel = bool(call_args.get("is_cancel"))
                                                    effective_is_cancel = is_cancel or gemini_is_cancel
                                                    has_sub_id = bool(self.session.booking_slots.get("submission_id") or getattr(self.session, "submitted_lead_id", None))
                                                    can_submit_req = effective_is_cancel or (not self.session.booking_slots.get("is_submitted") and all_slots_complete) or (has_sub_id and (is_explicit_submit or is_user_confirming_submit))
                                                    if (is_user_confirming_submit or effective_is_cancel or is_explicit_submit) and can_submit_req:
                                                        submit_args = dict(self.session.booking_slots)
                                                        sub_id = self.session.booking_slots.get("submission_id") or getattr(self.session, "submitted_lead_id", None)
                                                        submit_args["is_cancel"] = effective_is_cancel
                                                        submit_args["is_update"] = bool(sub_id) or bool(self.session.booking_slots.get("is_submitted"))
                                                        submit_args["submission_id"] = sub_id
                                                        submit_args["id"] = sub_id
                                                        if self.session.booking_slots.get("old_phone"):
                                                            submit_args["old_phone"] = self.session.booking_slots.get("old_phone")
                                                        if self.session.booking_slots.get("godaddy_id"):
                                                            submit_args["godaddy_id"] = self.session.booking_slots.get("godaddy_id")
                                                        if self.session.booking_slots.get("api_id"):
                                                            submit_args["api_id"] = self.session.booking_slots.get("api_id")
                                                        transcript_text = self._build_transcript_text()
                                                        if transcript_text:
                                                            submit_args["transcript"] = transcript_text
                                                        res = await submit_consultation_appointment(submit_args)
                                                        if res.get("status") == "success":
                                                            if effective_is_cancel:
                                                                self.session.booking_slots["is_cancel"] = True
                                                                self.session.booking_slots["is_submitted"] = False
                                                                confirm_msg = CONFIRMATION_CANCEL_MESSAGES_11.get(user_lang, CONFIRMATION_CANCEL_MESSAGES_11["en"])
                                                            else:
                                                                self.session.booking_slots["is_submitted"] = True
                                                                self.session.slots_edited_after_submit = False
                                                                confirm_msg = CONFIRMATION_MESSAGES_11.get(user_lang, CONFIRMATION_MESSAGES_11["en"])
                                                            if isinstance(res.get("details"), dict):
                                                                ret_id = res["details"].get("id") or res["details"].get("submission_id")
                                                                if ret_id:
                                                                    self.session.booking_slots["submission_id"] = ret_id
                                                                    self.session.submitted_lead_id = ret_id
                                                                if res["details"].get("godaddy_id"):
                                                                    self.session.booking_slots["godaddy_id"] = res["details"]["godaddy_id"]
                                                                if res["details"].get("api_id"):
                                                                    self.session.booking_slots["api_id"] = res["details"]["api_id"]
                                                            await self.send_json({
                                                                "type": "sync_slots",
                                                                "slots": self.session.booking_slots
                                                            })
                                                            full_text = confirm_msg
                                                            await self.send_json({
                                                                "type": "bot_text_chunk",
                                                                "text": confirm_msg,
                                                                "tag": None,
                                                                "turnId": self.session.current_voice_turn_id
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
            if is_cancel or getattr(self.session, 'booking_slots', {}).get("is_cancel"):
                full_text = CONFIRMATION_CANCEL_MESSAGES_11.get(user_lang, CONFIRMATION_CANCEL_MESSAGES_11["en"])
            elif self.session.booking_slots.get("is_submitted"):
                submitted_msgs = {
                    "gu": "તમારી અપૉઇન્ટમેન્ટ રિક્વેસ્ટ સફળતાપૂર્વક સબમિટ થઈ ગઈ છે! જો તમારે કોઈ ફેરફાર કરવો હોય કે રદ કરવી હોય તો જણાવશો.",
                    "hi": "आपका अपॉइंटमेंट अनुरोध पहले ही हमारी टीम को भेजा जा चुका है! यदि आप कोई बदलाव करना चाहते हैं या इसे रद्द करना चाहते हैं तो कृपया बताएं।",
                    "en": "Your appointment request has already been submitted to our team! Please let me know if you would like to make any changes or cancel."
                }
                full_text = submitted_msgs.get(user_lang, submitted_msgs["en"])
            elif not fn and not self.session.user_name:
                name_missing_msgs = {
                    "gu": "નમસ્તે! હું રિયા, USD કન્સલ્ટન્ટ છું. ચાલો તમારા સુંદર નામથી શરૂઆત કરીએ, તમારું નામ શું છે?",
                    "hi": "नमस्ते! मैं रिया, USD कंसल्टेंट हूँ। चलिए आपके सुंदर नाम से शुरुआत करते हैं, आपका नाम क्या है?",
                    "en": "Namaste! I am Riya, your USD Consultant. Let's start with your beautiful name, what is your name?"
                }
                full_text = name_missing_msgs.get(user_lang, name_missing_msgs["en"])
            elif not getattr(self.session, 'name_confirmed', False):
                name_confirm_msgs = {
                    "gu": f"નમસ્તે {display_name}! તમને તમારા દાંત કે સ્માઇલ વિશે કઈ સમસ્યા છે?",
                    "hi": f"नमस्ते {display_name}! आपको अपने दाँतों या स्माइल में क्या समस्या आ रही है?",
                    "en": f"Nice to meet you, {display_name}! What specific concern or goal do you have regarding your teeth or smile?"
                }
                full_text = name_confirm_msgs.get(user_lang, name_confirm_msgs["en"])
            elif not cn:
                concern_missing_msgs = {
                    "gu": f"તમને તમારા દાંત કે સ્માઇલ વિશે કઈ સમસ્યા છે, {display_name}?",
                    "hi": f"आपको अपने दाँतों या स्माइल में क्या समस्या आ रही है, {display_name}?",
                    "en": f"What specific concern or issue are you experiencing with your teeth or smile, {display_name}?"
                }
                full_text = concern_missing_msgs.get(user_lang, concern_missing_msgs["en"])
            elif not getattr(self.session, 'consultation_agreed', False):
                if getattr(self.session, "consultation_declined", False) or getattr(self.session, "consultation_offered", False):
                    decline_msgs = {
                        "gu": f"હું સમજી શકું છું, {display_name}. જો તમને દાંત કે સ્માઇલ ડિઝાઇન વિશે કોઈ પ્રશ્ન હોય તો મને પૂછી શકો છો!",
                        "hi": f"मैं समझ सकती हूँ, {display_name}। दाँतों या स्माइल डिज़ाइन के बारे में कोई भी प्रश्न हो तो आप बेझिझक पूछ सकते हैं!",
                        "en": f"I understand, {display_name}. Please let me know if you have any questions about our USD smile design or treatments!"
                    }
                    full_text = decline_msgs.get(user_lang, decline_msgs["en"])
                else:
                    self.session.consultation_offered = True
                    gate_msgs = {
                        "gu": f"હું સમજી શકું છું કે તમને {cn or 'દાંતની'} સમસ્યા છે, {display_name}. શું હું આના ઉકેલ માટે અમારા USD સર્ટિફાઇડ સ્માઇલ ડિઝાઇનર સાથે કન્સલ્ટેશન અપૉઇન્ટમેન્ટ બુક કરવામાં મદદ કરું?",
                        "hi": f"मैं समझ सकती हूँ कि आपको {cn or 'दाँतों की'} समस्या आ रही है, {display_name}। क्या मैं इसके समाधान के लिए हमारे USD सर्टिफाइड स्माइल डिज़ाइनर के साथ अपॉइंटमेंट बुक करने में आपकी मदद करूँ?",
                        "en": f"I understand you are experiencing {cn or 'dental concern'}, {display_name}. Would you like me to help book a consultation appointment with our USD Certified Smile Designer for this?"
                    }
                    full_text = gate_msgs.get(user_lang, gate_msgs["en"])
            elif not getattr(self.session, 'profession_asked', False):
                self.session.profession_asked = True
                prof_msgs = {
                    "gu": f"તેમ છતાં, {display_name}, જો હું પૂછી શકું, તમે શું કામ કરો છો?",
                    "hi": f"वैसे, {display_name}, अगर मैं पूछ सकती हूँ, आप क्या काम करते हैं?",
                    "en": f"By the way, {display_name}, what do you do for work?"
                }
                full_text = prof_msgs.get(user_lang, prof_msgs["en"])
            elif getattr(self.session, 'is_travel_booking_turn', False):
                from voice_agent.services.dentist_service import format_travel_dentists_speech_text, get_nearest_dentists_for_travel
                r_cit = self.session.booking_slots.get("city", "") or getattr(self.session, 'pending_city', '')
                r_pin = self.session.booking_slots.get("pincode", "") or getattr(self.session, 'pending_pincode', '')
                t_dest = getattr(self.session, "travel_destination_city", "") or self.session.booking_slots.get("clinic_city", "")
                t_docs = getattr(self.session, "recommended_dentists", [])
                if not t_docs:
                    t_docs = get_nearest_dentists_for_travel(r_pin, r_cit, t_dest)
                    self.session.recommended_dentists = t_docs
                full_text = format_travel_dentists_speech_text(t_docs, r_cit, t_dest, user_lang)
                self.session.is_travel_booking_turn = False
                self.session.asking_for_field = "doctor_selection"
                self.session.recommended_dentists_spoken = True
            elif getattr(self.session, 'city_confirm_needed', False) or (getattr(self.session, 'pending_pincode', None) and not getattr(self.session, 'city_pincode_locked', False)):
                from voice_agent.services.dentist_service import format_city_confirm_speech
                p_pin = getattr(self.session, 'pending_pincode', '') or pin or ''
                p_cit = getattr(self.session, 'pending_display_city', '') or getattr(self.session, 'pending_city', '') or ct or 'your'
                full_text = format_city_confirm_speech(p_pin, p_cit, user_lang)
            elif not pin:
                pincode_msgs = {
                    "gu": f"ખૂબ સરસ, {display_name}! તમારા સૌથી નજીકના USD સર્ટિફાઇડ સ્માઇલ ડિઝાઇનર શોધવા માટે, તમારા વિસ્તારનો 6 અંકનો પિનકોડ શું છે?",
                    "hi": f"बहुत बढ़िया, {display_name}! आपके सबसे नजदीकी USD सर्टिफाइड સ્માઇલ ડિઝાઇનર ढूंढने के लिए, आपके क्षेत्र का 6 अंकों का पिनकोड क्या है?",
                    "en": f"Great, {display_name}! To help find your nearest USD Certified Smile Designer, could you please tell me your 6-digit area pincode?"
                }
                full_text = pincode_msgs.get(user_lang, pincode_msgs["en"])
            elif not ct:
                city_msgs = {
                    "gu": f"બહુ સરસ, {display_name}! તમે કયા શહેરમાં રહો છો જેથી અમારી ટીમ તમારી વિગતો નોંધી શકે?",
                    "hi": f"बहुत बढ़िया, {display_name}! आप किस शहर में रहते हैं ताकि हमारी टीम आपका विवरण दर्ज कर सके?",
                    "en": f"Great, {display_name}! Which city do you reside in so our team can record your location?"
                }
                full_text = city_msgs.get(user_lang, city_msgs["en"])
            elif not dr and (asking_field in ["doctor", "doctor_selection"] or getattr(self.session, 'recommended_dentists_spoken', False)):
                doctor_msgs = {
                    "gu": f"{ct or 'તમારા શહેર'}માં શું તમે કોઈ ચોક્કસ USD સર્ટિફાઇડ સ્માઇલ ડિઝાઇનર પસંદ કરવા માંગો છો, કે પછી અમારી ટીમ માર્ગદર્શન આપે?",
                    "hi": f"{ct or 'आपके शहर'} में क्या आप किसी विशेष USD सर्टिफाइड स्माइल डिज़ाइनर को चुनना चाहेंगे, या हमारी टीम मार्गदर्शन करे?",
                    "en": f"Would you like to select a specific USD Certified Smile Designer in {ct or 'your city'}, or would you prefer our clinic team to guide you?"
                }
                full_text = doctor_msgs.get(user_lang, doctor_msgs["en"])
            elif not ph:
                phone_msgs = {
                    "gu": "કૃપા કરીને તમારો 10 અંકનો મોબાઇલ નંબર જણાવશો જેથી અમારી ટીમ તમારો સંપર્ક કરી શકે?",
                    "hi": "कृपया अपना 10 अंकों का मोबाइल नंबर बता दीजिए ताकि हमारी टीम आपसे संपर्क कर सके?",
                    "en": "Could you please provide your 10-digit mobile phone number so our team can contact you?"
                }
                full_text = phone_msgs.get(user_lang, phone_msgs["en"])
            else:
                summary_msgs = {
                    "gu": f"બહુ સરસ! તમારી બધી વિગતો નોંધી લીધી છે:\n- નામ: {display_name}\n- ફોન: {ph}\n- શહેર: {ct}\n- પિનકોડ: {pin}\n- સમસ્યા: {cn}\n- ડૉક્ટર: {dr or 'પસંદ કરેલ નથી (અમારી ટીમ માર્ગદર્શન આપશે)'}\n\nકૃપા કરીને આ અપૉઇન્ટમેન્ટ રિક્વેસ્ટ મોકલવા માટે 'submit' કહો અથવા રદ કરવા માટે 'cancel' કહો.",
                    "hi": f"बहुत बढ़िया! आपके सभी विवरण दर्ज कर लिए गए हैं:\n- नाम: {display_name}\n- फ़ोन: {ph}\n- शहर: {ct}\n- पिनकोड: {pin}\n- समस्या: {cn}\n- डॉक्टर: {dr or 'चयनित नहीं (हमारी टीम मार्गदर्शन करेगी)'}\n\nकृपया इस अपॉइंटमेंट अनुरोध को भेजने के लिए 'submit' कहें या रद्द करने के लिए 'cancel' कहें।",
                    "en": f"Great! All your details have been recorded:\n- Name: {display_name}\n- Phone: {ph}\n- City: {ct}\n- Pincode: {pin}\n- Concern: {cn}\n- Doctor: {dr or 'Not selected (Our team will guide you)'}\n\nPlease say 'submit' to submit this appointment request to our clinic team, or say 'cancel' to cancel it."
                }
                full_text = summary_msgs.get(user_lang, summary_msgs["en"])
            await self.send_json({
                "type": "bot_text_chunk",
                "text": full_text,
                "tag": None,
                "turnId": self.session.current_voice_turn_id
            })

        clean_text = clean_assistant_text(full_text)

        # 🚨 Track profession inquiry without destructive text stripping
        was_profession_already_asked = getattr(self.session, "profession_asked", False)
        prof_re_patterns = [
            r"(?:by the way,?\s+)?(?:what is your profession|what do you do for work|may i ask what profession you are in|may i ask what you do for work)\??",
            r"(?:તેમ છતાં,?\s*(?:જો હું પૂછી શકું,?\s*)?)?(?:તમે શું કામ કરો છો|તમારો વ્યવસાય શું છે|તમારો વ્યવસાય \(પ્રોફેશન\) શું છે)\??",
            r"(?:वैसे,?\s*(?:अगर मैं पूछ सकती हूँ,?\s*)?)?(?:आप क्या काम करते हैं|आपका पेशा या प्रोफेशन क्या है|आप किस प्रोफेशन में हैं)\??"
        ]
        if not was_profession_already_asked and clean_text:
            for pat in prof_re_patterns:
                if re.search(pat, clean_text, flags=re.IGNORECASE):
                    self.session.profession_asked = True
                    break

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
                        user_lang = detect_user_language(user_text, history, getattr(self.session, 'current_language', None))
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

        # ⚡ Post-Generation Cancellation & Submission Safety Net in Chat Mode ⚡
        bot_txt_lower = (clean_text or full_text).lower()
        is_cancel_detected = is_cancel or is_cancel_response_text(bot_txt_lower)
        is_submit_detected = is_explicit_submit or is_submit_response_text(bot_txt_lower)

        if is_cancel_detected and not self.session.booking_slots.get("is_cancel"):
            has_sub_or_lead = bool(self.session.booking_slots.get("submission_id") or self.session.booking_slots.get("is_submitted") or self.session.booking_slots.get("phone") or (self.session.booking_slots.get("first_name") and self.session.booking_slots.get("city")))
            if has_sub_or_lead:
                cancel_args = dict(self.session.booking_slots)
                cancel_args["is_cancel"] = True
                cancel_args["is_update"] = True
                cancel_args["submission_id"] = self.session.booking_slots.get("submission_id")
                if self.session.booking_slots.get("godaddy_id"):
                    cancel_args["godaddy_id"] = self.session.booking_slots.get("godaddy_id")
                if self.session.booking_slots.get("api_id"):
                    cancel_args["api_id"] = self.session.booking_slots.get("api_id")
                transcript_text = self._build_transcript_text()
                if transcript_text:
                    cancel_args["transcript"] = transcript_text
                try:
                    c_res = await submit_consultation_appointment(cancel_args)
                    if c_res.get("status") == "success":
                        self.session.booking_slots["is_submitted"] = True
                        self.session.booking_slots["is_cancel"] = True
                        if isinstance(c_res.get("details"), dict):
                            ret_id = c_res["details"].get("id") or c_res["details"].get("submission_id")
                            if ret_id:
                                self.session.booking_slots["submission_id"] = ret_id
                            if c_res["details"].get("godaddy_id"):
                                self.session.booking_slots["godaddy_id"] = c_res["details"]["godaddy_id"]
                            if c_res["details"].get("api_id"):
                                self.session.booking_slots["api_id"] = c_res["details"]["api_id"]
                        await self.send_json({
                            "type": "sync_slots",
                            "slots": self.session.booking_slots
                        })
                        print(f"[INFO] Post-generation Chat Mode appointment cancelled: {cancel_args}")
                except Exception as ce:
                    print(f"[WARN] Error executing post-generation cancellation in Chat Mode: {ce}")

        # ⚡ Post-Generation Premature Submission Interceptor in Chat Mode ⚡
        has_lead_sub = bool(self.session.booking_slots.get("submission_id") or getattr(self.session, "submitted_lead_id", None))
        if not is_cancel and not self.session.booking_slots.get("is_submitted") and not has_lead_sub and is_submit_response_text(bot_txt_lower):
            s_slots = self.session.booking_slots
            h_f = bool(s_slots.get("first_name") and s_slots["first_name"].lower() not in ["", "none", "null", "patient", "user"])
            h_c = bool(s_slots.get("city") and len(str(s_slots["city"]).strip()) >= 2 and str(s_slots["city"]).lower() not in ["", "none", "null", "india"])
            h_p = bool(s_slots.get("pincode") and len("".join(filter(str.isdigit, str(s_slots["pincode"])))) == 6)
            h_m = bool(s_slots.get("message") and len(s_slots["message"].strip()) >= 2 and s_slots["message"].lower() not in ["none", "null", "dental consultation appointment request", ""])
            h_ph = bool(s_slots.get("phone") and len("".join(filter(str.isdigit, str(s_slots["phone"])))) == 10)

            missing_f = "phone"
            if not h_f: missing_f = "name"
            elif not h_m: missing_f = "concern"
            elif not h_c: missing_f = "city"
            elif not h_p: missing_f = "pincode"

            user_lang = detect_user_language(user_text, history, getattr(self.session, 'current_language', None))
            missing_msg = get_missing_field_message(user_lang, missing_f)
            self.session.asking_for_field = missing_f
            clean_text = missing_msg
            full_text = missing_msg

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
        if user_text and user_text != "Hello":
            self.session.add_transcript_turn("user", user_text)
        if clean_text or full_text:
            self.session.add_transcript_turn("model", clean_text or full_text)
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
                    "phone": "", "city": "", "pincode": "", "message": "", "doctor_name": "",
                    "is_booking_active": False, "is_submitted": False
                }
            
            # Frontend control prompts (silence nudge, reconnect, greeting) are not patient speech:
            # never parse them for slots and never let them trigger the canned interception replies
            is_system_instruction = self.session.latest_typed_user_text.strip().startswith("SYSTEM INSTRUCTION")
            # Worker thread: slot parsing can make blocking postal/dentist API calls
            if is_system_instruction:
                await asyncio.to_thread(self.update_session_memory, "", self.session.latest_client_history, data)
            else:
                await asyncio.to_thread(self.update_session_memory, self.session.latest_typed_user_text, self.session.latest_client_history, data)

            user_text = self.session.latest_typed_user_text or "Hello"
            self.session.is_interrupted = False
            self.session.chunk_index = 0
            self.session.display_str = ""
            self.session.full_bot_reply = ""
            self.session.live_pcm_buffer = bytearray()
            self.session.assistant_audio_buffer = bytearray()
            
            # If city-pincode mismatch or dentist recommendation is needed, handle directly via stream_chat_text_response
            is_pin_turn = bool(getattr(self.session, 'pincode_just_updated', False) or (extract_valid_pincode(user_text, phone=self.session.booking_slots.get("phone")) and not getattr(self.session, 'recommended_dentists_spoken', False)))
            is_oth = is_asking_for_other_dentists(user_text) or getattr(self.session, 'is_other_dentists_requested', False)
            has_pin = self.session.booking_slots.get("pincode") or extract_valid_pincode(user_text, phone=self.session.booking_slots.get("phone"))
            needs_dentist_speech = (is_pin_turn or (is_oth and bool(has_pin)) or (is_asking_for_dentist_names(user_text) and bool(has_pin))) and not getattr(self.session, 'city_pincode_mismatch', False)

            if is_system_instruction and self.session.latest_client_is_voice_mode:
                self.session.clear_voice_intercept_flags()
            elif getattr(self.session, 'phone_invalid', False) or getattr(self.session, 'state_clarification_needed', None) or getattr(self.session, 'city_pincode_mismatch', False) or getattr(self.session, 'pincode_invalid', False) or getattr(self.session, 'city_confirm_needed', False) or getattr(self.session, 'is_travel_booking_turn', False) or needs_dentist_speech or getattr(self.session, 'city_updated_need_pincode', False):
                asyncio.create_task(self.stream_chat_text_response(user_text, self.session.latest_client_history, system_prompt))
                return

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
                    if getattr(self.session, 'has_user_spoken', False) and getattr(self.session, 'is_language_established', False) and getattr(self.session, 'current_language', None):
                        active_mem_lines.append(f"- MANDATORY LANGUAGE: The user's active language is {self.session.current_language}. You MUST respond in {self.session.current_language} beginning with [{self.session.current_language}]. However, if the user switches to another Indian language (e.g. Hindi, Gujarati, Marathi, English), immediately switch with them to that language!")
                    else:
                        active_mem_lines.append("- STARTING LANGUAGE & DYNAMIC MATCHING: Start with greeting in Indian English beginning with [en-IN]. However, as soon as the user speaks in Hindi [hi-IN], Gujarati [gu-IN], Marathi [mr-IN], or any of the 11 supported Indian languages, YOU MUST IMMEDIATELY SWITCH YOUR RESPONSE to that same language and prefix with the appropriate language tag!")

                    # Sequential step-by-step flow enforcement (STRICT ONE QUESTION AT A TIME)
                    if not self.session.user_name:
                        active_mem_lines.append("- CURRENT SEQUENTIAL STEP (MANDATORY): Step 1 (Greeting & Patient Name). Ask warmly for their name. DO NOT ask for City, Concern, Doctor, Pincode, or Phone yet!")
                    elif not self.session.user_concern:
                        active_mem_lines.append(f"- CURRENT SEQUENTIAL STEP (MANDATORY): Step 1 done -> Step 2 (Dental Concern). Greet {self.session.user_name} by name and ask ONLY what specific dental concern or smile goal they have (do NOT ask them to confirm their name). YOU ARE STRICTLY FORBIDDEN from asking for City, Doctor, Pincode, or Phone!")
                    elif not getattr(self.session, "consultation_agreed", False) and not self.session.booking_slots.get("pincode"):
                        active_mem_lines.append(f"- CURRENT SEQUENTIAL STEP (MANDATORY): Step 2 confirmed -> Step 2.5 (Consultation Permission Gate). Acknowledge dental concern ({self.session.user_concern}), and ask ONLY: 'Would you like me to help book a consultation appointment with our USD Certified Smile Designer for this?'. YOU MUST WAIT FOR PATIENT TO SAY YES before asking for Pincode! DO NOT ask about profession or pincode in this turn!")
                    elif not self.session.booking_slots.get("pincode"):
                        active_mem_lines.append(f"- CURRENT SEQUENTIAL STEP (MANDATORY): Step 3 (Pincode FIRST). Ask ONLY for their 6-digit area pincode ('What is your 6-digit area pincode?'). YOU ARE STRICTLY FORBIDDEN from asking for city, doctor, or phone in this turn! DO NOT ask about profession!")
                    elif getattr(self.session, "city_confirm_needed", False) or not self.session.booking_slots.get("city"):
                        p_pin = self.session.booking_slots.get("pincode") or getattr(self.session, 'pending_pincode', '')
                        p_cit = getattr(self.session, 'pending_display_city', '') or getattr(self.session, 'pending_city', '') or self.session.booking_slots.get("city")
                        active_mem_lines.append(f"- CURRENT SEQUENTIAL STEP (MANDATORY): Step 3.5 (Confirm City from Pincode ONLY). Pincode is {p_pin} ({p_cit} area). Ask ONLY: 'Based on your pincode {p_pin}, you reside in {p_cit} area, right?'. 🚨 DO NOT recommend doctors, DO NOT ask doctor guidance, DO NOT ask phone number!")
                    elif getattr(self.session, "is_travel_booking_turn", False) or (getattr(self.session, "travel_destination_city", None) and not self.session.booking_slots.get("doctor_name")):
                        t_dest = getattr(self.session, "travel_destination_city", "") or self.session.booking_slots.get("clinic_city", "")
                        r_cit = self.session.booking_slots.get("city", "")
                        r_pin = self.session.booking_slots.get("pincode", "")
                        active_mem_lines.append(f"- CURRENT SEQUENTIAL STEP (MANDATORY): Travel Booking in {t_dest}. Patient resides in {r_cit} ({r_pin}) and wants appointment in {t_dest}. DO NOT change residence city/pincode! DO NOT ask for pincode in {t_dest}! Recommend the 3 nearest dentists in {t_dest} closest to arrival route.")
                    elif getattr(self.session, "consultation_declined", False):
                        active_mem_lines.append("- CONSULTATION DECLINED: Patient previously declined consultation or appointment booking. Converse purely as a helpful smile consultant answering their dental/treatment questions. DO NOT push appointment booking or ask for doctor/phone!")
                    elif not self.session.booking_slots.get("doctor_name") and not getattr(self.session, "doctor_guidance_asked", False):
                        if getattr(self.session, "recommended_dentists_spoken", False):
                            active_mem_lines.append(f"- CURRENT SEQUENTIAL STEP (MANDATORY): Step 4 (Doctor Choice Follow-up). The 3 nearest dentist names for pincode {self.session.booking_slots.get('pincode')} have ALREADY been spoken to the patient. 🚨 ABSOLUTE BAN: DO NOT repeat or speak the dentist names again! Ask if they prefer one of those doctors or want clinic team to guide them. If patient says 'no', 'nahi', 'nathi', accept gracefully without asking again!")
                        else:
                            active_mem_lines.append(f"- CURRENT SEQUENTIAL STEP (MANDATORY): Step 4 (Doctor Guidance ONLY). Speak the 3 nearest dentist names for pincode {self.session.booking_slots.get('pincode')} and ask if they prefer one or want clinic team to guide them. YOU ARE STRICTLY FORBIDDEN from asking for phone number in Step 4! Wait for their doctor response!")
                    elif not self.session.booking_slots.get("phone"):
                        active_mem_lines.append(f"- CURRENT SEQUENTIAL STEP (MANDATORY): Step 5 (Phone Number ONLY). Doctor addressed. Ask ONLY for their 10-digit mobile number so clinic team can contact them ('Could you please provide your 10-digit mobile phone number?'). DO NOT recite review summary yet! DO NOT ask to submit yet!")
                    elif not self.session.booking_slots.get("is_submitted"):
                        active_mem_lines.append(f"- CURRENT SEQUENTIAL STEP (MANDATORY): Step 6 (Review Summary). Present confirmed details in full 6 lines and ask: 'Please say submit to submit this appointment request to our clinic team, or say cancel to cancel it.'")

                    if getattr(self.session, "profession_asked", False) or getattr(self.session, "consultation_agreed", False) or self.session.booking_slots.get("city"):
                        active_mem_lines.append("- PROFESSION INQUIRY STRICTLY FORBIDDEN: Profession was already asked or booking flow is active. You are STRICTLY FORBIDDEN from asking 'what is your profession?', 'what do you do for work?', or 'about your work' under ANY circumstance!")
                    active_mem_lines.append("- ONE QUESTION PER REPLY (ABSOLUTE): Your reply may contain only ONE question. Never combine two asks (e.g. name confirmation + concern, concern + consultation offer, city confirmation + profession, dentist names + phone number).")

                    if self.session.user_name:
                        active_mem_lines.append(f"- Confirmed Patient Name: {self.session.user_name}")
                    if self.session.booking_slots.get("city"):
                        active_mem_lines.append(f"- Confirmed City: {self.session.booking_slots.get('city')}")
                    if self.session.booking_slots.get("pincode"):
                        active_mem_lines.append(f"- Confirmed 6-digit Pincode: {self.session.booking_slots.get('pincode')}")
                    if self.session.booking_slots.get("phone"):
                        active_mem_lines.append(f"- Confirmed 10-digit Phone: {self.session.booking_slots.get('phone')}")
                    if self.session.booking_slots.get("doctor_name"):
                        active_mem_lines.append(f"- Confirmed Doctor: {self.session.booking_slots.get('doctor_name')}")
                    pin_str = str(self.session.booking_slots.get("pincode") or "").strip()
                    if pin_str and len(pin_str) == 6 and pin_str.isdigit() and not getattr(self.session, "recommended_dentists", None):
                        try:
                            from voice_agent.services.dentist_service import get_nearest_dentists
                            d_slice, _, _ = await asyncio.to_thread(get_nearest_dentists, pin_str, 0, 3)
                            self.session.recommended_dentists = d_slice
                        except Exception:
                            pass
                    if getattr(self.session, "recommended_dentists", None):
                        from voice_agent.services.dentist_service import format_dentist_recommendation_prompt
                        active_mem_lines.append(format_dentist_recommendation_prompt(
                            self.session.recommended_dentists,
                            self.session.booking_slots.get("pincode") or getattr(self.session, "last_recommended_pincode", "") or "",
                            getattr(self.session, "dentist_page_offset", 0)
                        ))
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
            await self.send_json({"type": "user_speaking_status", "is_speaking": False})
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
        await self.send_json({"type": "user_speaking_status", "is_speaking": False})
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
            
            if user_text and user_text != "Voice Message" and user_text != "Hello":
                self.session.add_transcript_turn("user", user_text)
            if clean_text and clean_text != "(Voice message played)":
                self.session.add_transcript_turn("model", clean_text)

            # If user or model cancelled appointment in this turn, ensure DB is updated
            is_cancel_turn = is_cancel_submit(user_text, self.session) or \
                             is_cancel_response_text(clean_text) or \
                             bool(getattr(self.session, "pending_cancellation", False)) or \
                             bool(self.session.booking_slots.get("is_cancel"))
            if is_cancel_turn:
                self.session.booking_slots["is_cancel"] = True
                self.session.pending_cancellation = False
                c_args = dict(self.session.booking_slots)
                c_args["is_cancel"] = True
                c_args["is_update"] = True
                sub_id = self.session.booking_slots.get("submission_id") or getattr(self.session, "submitted_lead_id", None)
                if sub_id:
                    c_args["submission_id"] = sub_id
                    c_args["id"] = sub_id
                try:
                    c_res = await submit_consultation_appointment(c_args)
                    print(f"[SUCCESS] Voice Mode cancellation synced to DB in transcribe_and_sync_bot_text: {c_res}")
                except Exception as ce:
                    print(f"[WARN] Error executing cancellation in transcribe_and_sync_bot_text: {ce}")
            
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
                now = time.time()
                elapsed = now - self.session.last_activity_time
                is_voice = getattr(self.session, 'latest_client_is_voice_mode', True)
                current_timeout = 300 if is_voice else 360
                if elapsed >= current_timeout:
                    print("⏳ Inactivity timeout reached (300s). Disconnecting client...")
                    await self.send_json({"type": "error", "error": "Session timed out due to inactivity."})
                    await close_ws_callback()
                    break
                
                # Sleep for the remaining time (capped between 2.0 and 15.0 seconds for responsiveness)
                sleep_time = max(2.0, min(15.0, current_timeout - elapsed))
                await asyncio.sleep(sleep_time)
            except Exception as e:
                print(f"Error in inactivity monitor: {e}")
                break
