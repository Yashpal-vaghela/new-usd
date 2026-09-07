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
    print(log_msg, flush=True)

import os
import re
import json
import base64
import asyncio
import httpx
from voice_agent.utils.constants import INACTIVITY_TIMEOUT
from voice_agent.utils.helpers import clean_assistant_text, clean_hallucinations, extract_slots_from_review_summary, transliterate_to_english, strip_diacritics, ALL_CERTIFIED_DOCTORS_LIST
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
    key = os.getenv("GEMINI_API_KEY_NEW", "").strip()
    return [key] if key else []

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

MULTILINGUAL_CITY_MAP = {
    # Gujarati
    "અમદાવાદ": "Ahmedabad", "સુરત": "Surat", "વડોદરા": "Vadodara", "બરોડા": "Vadodara",
    "રાજકોટ": "Rajkot", "જામનગર": "Jamnagar", "ભરૂચ": "Bharuch", "હળવદ": "Halvad",
    "ધ્રાંગધ્રા": "Dhrangadhra", "મુંબઈ": "Mumbai", "મુંબઇ": "Mumbai", "પુણે": "Pune", "પુના": "Pune",
    "દિલ્હી": "New Delhi", "નવી દિલ્હી": "New Delhi", "બેંગલોર": "Bangalore", "બેંગલુરુ": "Bangalore",
    "હૈદરાબાદ": "Hyderabad", "ચેન્નાઈ": "Chennai", "ગ્વાલિયર": "Gwalior", "ઈન્દોર": "Indore", "ઇન્દોર": "Indore",
    "સાંગલી": "Sangli", "ગુવાહાટી": "Guwahati", "ગુંટુર": "Guntur", "ફરીદકોટ": "Faridkot",
    "શ્રી ગંગાનગર": "Sri Ganganagar", "માલદા": "Malda",
    # Hindi / Marathi
    "अहमदाबाद": "Ahmedabad", "सूरत": "Surat", "वडोदरा": "Vadodara", "बड़ौदा": "Vadodara",
    "राजकोट": "Rajkot", "जामनगर": "Jamnagar", "भरूच": "Bharuch", "हलवद": "Halvad",
    "ध्रांगध्रा": "Dhrangadhra", "मुंबई": "Mumbai", "पुणे": "Pune", "दिल्ली": "New Delhi",
    "नई दिल्ली": "New Delhi", "बैंगलोर": "Bangalore", "बेंगलुरु": "Bangalore",
    "हैदराबाद": "Hyderabad", "चेन्नई": "Chennai", "ग्वालियर": "Gwalior", "इंदौर": "Indore",
    "सांगली": "Sangli", "गुवाहाटी": "Guwahati", "गुंटूर": "Guntur", "फरीदकोट": "Faridkot",
    "श्री गंगानगर": "Sri Ganganagar", "मालदा": "Malda",
    # Bengali
    "আহমেদাবাদ": "Ahmedabad", "সুরাট": "Surat", "ভদোদরা": "Vadodara", "রাজকোট": "Rajkot",
    "মুম্বাই": "Mumbai", "পুনে": "Pune", "দিল্লি": "New Delhi", "বেঙ্গালুরু": "Bangalore",
    "হায়দ্রাবাদ": "Hyderabad", "চেন্নাই": "Chennai", "মালদা": "Malda", "গোয়ালিয়র": "Gwalior", "ইন্দোর": "Indore",
    # Tamil
    "அகமதாபாத்": "Ahmedabad", "சூரத்": "Surat", "வதோதரா": "Vadodara", "ராஜ்கோட்": "Rajkot",
    "மும்பை": "Mumbai", "புனே": "Pune", "டெல்லி": "New Delhi", "பெங்களூரு": "Bangalore",
    "ஹைதராபாத்": "Hyderabad", "சென்னை": "Chennai", "சென்னையில்": "Chennai", "குண்டூர்": "Guntur",
    # Telugu
    "అహ్మదాబాద్": "Ahmedabad", "సూరత్": "Surat", "వడోదర": "Vadodara", "రాజ్‌కోట్": "Rajkot",
    "ముంబై": "Mumbai", "పూణే": "Pune", "ఢిల్లీ": "New Delhi", "బెంగళూరు": "Bangalore",
    "హైదరాబాద్": "Hyderabad", "చెన్నై": "Chennai", "గుంటూరు": "Guntur", "గుంటూరులో": "Guntur",
    # Kannada
    "ಅಹಮದಾಬಾದ್": "Ahmedabad", "ಸೂರತ್": "Surat", "ವಡೋದರಾ": "Vadodara", "ರಾಜ್‌ಕೋಟ್": "Rajkot",
    "ಮುಂಬೈ": "Mumbai", "ಪುಣೆ": "Pune", "ದೆಹಲಿ": "New Delhi", "ಬೆಂಗಳೂರು": "Bangalore", "ಬೆಂಗಳೂರಿನಲ್ಲಿ": "Bangalore",
    "ಹೈದರಾಬಾದ್": "Hyderabad", "ಚೆನ್ನೈ": "Chennai", "ಗುಂಟೂರು": "Guntur",
    # Malayalam
    "അഹമ്മദാബാദ്": "Ahmedabad", "സൂററ്റ്": "Surat", "വഡോദര": "Vadodara", "മുംബൈ": "Mumbai",
    "പുണെ": "Pune", "ഡൽഹി": "New Delhi", "ബെംഗളൂരു": "Bangalore", "ഹൈദരാബാദ്": "Hyderabad", "ചെന്നൈ": "Chennai",
    # Punjabi
    "ਅਹਿਮਦਾਬਾਦ": "Ahmedabad", "ਸੂਰਤ": "Surat", "ਵਡੋਦਰਾ": "Vadodara", "ਮੁੰਬਈ": "Mumbai",
    "ਪੁਣੇ": "Pune", "ਦਿੱਲੀ": "New Delhi", "ਬੰਗਲੌਰ": "Bangalore", "ਹੈਦਰਾਬਾਦ": "Hyderabad", "ਚੇਨਈ": "Chennai", "ਫ਼ਰੀਦਕੋਟ": "Faridkot",
    # Odia
    "ଅହମ୍ମଦାବାଦ": "Ahmedabad", "ସୁରଟ": "Surat", "ଭଦୋଦରା": "Vadodara", "ମୁମ୍ବାଇ": "Mumbai",
    "ପୁଣେ": "Pune", "ଦିଲ୍ଲୀ": "New Delhi", "ବେଙ୍ଗାଲୁରୁ": "Bangalore", "ହାଇଦ୍ରାବାଦ": "Hyderabad", "ଚେନ୍ନାଇ": "Chennai",
    # English variations
    "ahmedabad": "Ahmedabad", "surat": "Surat", "vadodara": "Vadodara", "baroda": "Vadodara",
    "rajkot": "Rajkot", "jamnagar": "Jamnagar", "bharuch": "Bharuch", "halvad": "Halvad",
    "dhrangadhra": "Dhrangadhra", "mumbai": "Mumbai", "bombay": "Mumbai", "pune": "Pune", "poona": "Pune",
    "delhi": "New Delhi", "new delhi": "New Delhi", "gurugram": "Gurugram", "gurgaon": "Gurugram",
    "bangalore": "Bangalore", "bengaluru": "Bangalore", "hyderabad": "Hyderabad", "chennai": "Chennai",
    "madras": "Chennai", "gwalior": "Gwalior", "indore": "Indore", "sangli": "Sangli",
    "guwahati": "Guwahati", "ગુવાહાટી": "Guwahati", "गुवाहाटी": "Guwahati", "આસામ": "Guwahati", "અસમ": "Guwahati", "असम": "Guwahati",
    "guntur": "Guntur", "faridkot": "Faridkot",
    "sri ganganagar": "Sri Ganganagar", "ganganagar": "Sri Ganganagar", "malda": "Malda"
}

def extract_certified_city_from_text(text_to_search):
    if not text_to_search:
        return None
    import re
    tl = text_to_search.lower().strip()
    
    # 1. Exact or substring match in multilingual map
    for k, standard_name in MULTILINGUAL_CITY_MAP.items():
        if k in text_to_search or (k.isascii() and re.search(r"\b" + re.escape(k) + r"\b", tl)):
            return standard_name
            
    # 2. Check CERTIFIED_CITIES list
    for city in CERTIFIED_CITIES:
        if re.search(r"\b" + re.escape(city) + r"\b", tl, re.IGNORECASE):
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
    doc_list = (CITY_DOCTORS.get(city, []) if city else []) + ALL_CERTIFIED_DOCTORS
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

    # Case 1: Explicit prefix "dr." or "doctor" (e.g. "dr srilakshmi", "dr. ravi", "doctor mohammed")
    m_dr = re.search(r"\b(?:dr\.?|doctor)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)", tl, re.IGNORECASE)
    if m_dr:
        cand = m_dr.group(1).strip().lower()
        doc_list = CITY_DOCTORS.get(city, []) if city else ALL_CERTIFIED_DOCTORS
        if not doc_list:
            doc_list = ALL_CERTIFIED_DOCTORS
        for doc in doc_list:
            doc_clean = re.sub(r"^dr\.?\s*", "", doc, flags=re.IGNORECASE).strip().lower()
            if cand in doc_clean or doc_clean.startswith(cand):
                return doc

    # Case 2: Match doctor by specific first name or distinctive name parts (e.g. "jaanu", "janu", "alap", "srilakshmi")
    tl_clean = re.sub(r"^(?:dr\.?|doctor)\s*", "", tl, flags=re.IGNORECASE).strip()
    doc_list = (CITY_DOCTORS.get(city, []) if city else []) + ALL_CERTIFIED_DOCTORS
    if not doc_list:
        doc_list = ALL_CERTIFIED_DOCTORS

    common_surnames = {"shah", "patel", "sharma", "singh", "patil", "kumar", "gupta", "agarwal", "deshpande", "patel."}
    
    # 2a. Priority pass: Match distinct first names (e.g. "janu", "jaanu", "alap", "ravi", "rakesh")
    for doc in doc_list:
        doc_clean = re.sub(r"^dr\.?\s*", "", doc, flags=re.IGNORECASE).strip().lower()
        parts = [p.lower() for p in doc_clean.split() if len(p) >= 3 and p.lower() not in common_surnames]
        for p in parts:
            if p in tl_clean or re.search(r"\b" + re.escape(p) + r"\b", tl_clean):
                return doc
            # Phonetic double-vowel match (e.g. jaanu -> janu)
            p_simple = re.sub(r"([aeiou])\1+", r"\1", p)
            tl_simple = re.sub(r"([aeiou])\1+", r"\1", tl_clean)
            if p_simple in tl_simple:
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
    "રાકેશ": "Dr. Rakesh Patel", "રાકેશ પટેલ": "Dr. Rakesh Patel", "राकेश": "Dr. Rakesh Patel", "rakesh": "Dr. Rakesh Patel", "rakesh patel": "Dr. Rakesh Patel",
    "જીગર": "Dr. Jigar P. Thakkar", "જીગર ઠક્કર": "Dr. Jigar P. Thakkar", "जिगर": "Dr. Jigar P. Thakkar", "jigar": "Dr. Jigar P. Thakkar", "jigar thakkar": "Dr. Jigar P. Thakkar", "thakkar": "Dr. Jigar P. Thakkar", "ઠક્કર": "Dr. Jigar P. Thakkar", "thakkar bhai": "Dr. Jigar P. Thakkar", "ઠક્કર ભાઈ": "Dr. Jigar P. Thakkar",
    "અંકિત": "Dr. Ankit Mataliya", "અંકિત માતાલિયા": "Dr. Ankit Mataliya", "અંકિત મતાલિયા": "Dr. Ankit Mataliya", "अंकित": "Dr. Ankit Mataliya", "ankit": "Dr. Ankit Mataliya", "ankit mataliya": "Dr. Ankit Mataliya", "mataliya": "Dr. Ankit Mataliya", "માતલિયા": "Dr. Ankit Mataliya", "મતાલિયા": "Dr. Ankit Mataliya",
    "નીરવ": "Dr. Neerav Jhaveri", "નીરવ ઝવેરી": "Dr. Neerav Jhaveri", "નિરવ": "Dr. Neerav Jhaveri", "नीरव": "Dr. Neerav Jhaveri", "neerav": "Dr. Neerav Jhaveri", "neerav jhaveri": "Dr. Neerav Jhaveri", "nirav": "Dr. Neerav Jhaveri", "jhaveri": "Dr. Neerav Jhaveri", "ઝવેરી": "Dr. Neerav Jhaveri",
    "આલાપ": "Dr. Alap D Shah", "આલાપ શાહ": "Dr. Alap D Shah", "आलाप": "Dr. Alap D Shah", "alap": "Dr. Alap D Shah", "alap shah": "Dr. Alap D Shah",
    "અબ્બાસ": "Dr. Abbas Noorani", "અબ્બાસ નૂરાની": "Dr. Abbas Noorani", "अब्बास": "Dr. Abbas Noorani", "abbas": "Dr. Abbas Noorani", "abbas noorani": "Dr. Abbas Noorani", "noorani": "Dr. Abbas Noorani", "નૂરાની": "Dr. Abbas Noorani",
    "પૂર્વેશ": "Dr. Purvesh Chauhan", "પૂર્વેશ ચૌહાણ": "Dr. Purvesh Chauhan", "પુર્વેશ": "Dr. Purvesh Chauhan", "purvesh": "Dr. Purvesh Chauhan", "purvesh chauhan": "Dr. Purvesh Chauhan", "chauhan": "Dr. Purvesh Chauhan", "ચૌહાણ": "Dr. Purvesh Chauhan",
    "રવિ શાહ": "Dr. Ravi Shah", "ravi shah": "Dr. Ravi Shah", "ravi": "Dr. Ravi Shah", "raavi": "Dr. Ravi Shah",
    "જાનુ": "Dr. Janu Shah", "જાનુ શાહ": "Dr. Janu Shah", "જાનું": "Dr. Janu Shah", "જાનું શાહ": "Dr. Janu Shah", "janu": "Dr. Janu Shah", "janu shah": "Dr. Janu Shah", "jaanu": "Dr. Janu Shah", "jaanu shah": "Dr. Janu Shah", "jannu": "Dr. Janu Shah",
    # Surat
    "ભરત પટેલ": "Dr. Bharat R. Patel", "ભરત આર પટેલ": "Dr. Bharat R. Patel", "ભરત": "Dr. Bharat R. Patel", "bharat": "Dr. Bharat R. Patel", "bharat patel": "Dr. Bharat R. Patel", "bharat r patel": "Dr. Bharat R. Patel",
    "પરીતા": "Dr. Parita Shah", "પરીતા શાહ": "Dr. Parita Shah", "પરિતા": "Dr. Parita Shah", "parita": "Dr. Parita Shah", "parita shah": "Dr. Parita Shah",
    "વિરેન": "Dr. Viren K Savani", "વિરેન સાવાની": "Dr. Viren K Savani", "વીરેન": "Dr. Viren K Savani", "viren": "Dr. Viren K Savani", "viren savani": "Dr. Viren K Savani", "savani": "Dr. Viren K Savani", "viren k savani": "Dr. Viren K Savani", "સાવાણી": "Dr. Viren K Savani", "સવાણી": "Dr. Viren K Savani",
    "પૂર્વી": "Dr. Purvi Patel", "પૂર્વી પટેલ": "Dr. Purvi Patel", "પુર્વી": "Dr. Purvi Patel", "purvi": "Dr. Purvi Patel", "purvi patel": "Dr. Purvi Patel",
    "પ્રિયંકા": "Dr. Priyanka Kathiriya", "પ્રિયંકા કથીરિયા": "Dr. Priyanka Kathiriya", "પ્રિયંકા કાઠીરીયા": "Dr. Priyanka Kathiriya", "priyanka": "Dr. Priyanka Kathiriya", "priyanka kathiriya": "Dr. Priyanka Kathiriya", "kathiriya": "Dr. Priyanka Kathiriya", "કથીરિયા": "Dr. Priyanka Kathiriya", "કાઠીરીયા": "Dr. Priyanka Kathiriya",
    "જય પટેલ": "Dr. Jay Patel", "જય": "Dr. Jay Patel", "jay": "Dr. Jay Patel", "jay patel": "Dr. Jay Patel",
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
    "ચેતરિયા": "Dr. D. J. Chetariya", "ચેતરીયા": "Dr. D. J. Chetariya", "chetariya": "Dr. D. J. Chetariya",
    "પ્રસન્ન": "Dr. Prasanna Patel", "પ્રસન્ના": "Dr. Prasanna Patel", "prasanna": "Dr. Prasanna Patel",
    "કાતરમલ": "Dr. Bharat Katarmal", "katarmal": "Dr. Bharat Katarmal", "કાતરમલ": "Dr. Bharat Katarmal",
    # Bharuch, Halvad, Dhrangadhra
    "હફશા": "Dr. Hafsha Saiyed", "hafsha": "Dr. Hafsha Saiyed", "hafsha saiyed": "Dr. Hafsha Saiyed", "saiyed": "Dr. Hafsha Saiyed", "સૈયદ": "Dr. Hafsha Saiyed",
    "પંકજ": "Dr. Pankaj Patel", "pankaj": "Dr. Pankaj Patel", "pankaj patel": "Dr. Pankaj Patel",
    "દિલીપ": "Dr. Dilip J Parejiya", "dilip": "Dr. Dilip J Parejiya", "parejiya": "Dr. Dilip J Parejiya", "પરેજીયા": "Dr. Dilip J Parejiya",
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
    digits = "".join(filter(str.isdigit, str(text_str or "")))
    if len(digits) == 10:
        return digits
    if len(digits) == 11 and digits.startswith("0"):
        return digits[1:]
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    if len(digits) == 13 and digits.startswith("091"):
        return digits[3:]
    return None

def detect_user_language(user_text="", history=None):
    combined = (user_text or "") + " "
    if history and isinstance(history, list):
        for turn in history:
            p = turn.get("parts", [{}])[0].get("text", "")
            combined += p + " "
    
    # 1. Unicode script detection across combined history
    for c in combined:
        code = ord(c)
        if 0x0A80 <= code <= 0x0AFF:
            return "gu" # Gujarati
        if 0x0980 <= code <= 0x09FF:
            return "bn" # Bengali
        if 0x0B80 <= code <= 0x0BFF:
            return "ta" # Tamil
        if 0x0C00 <= code <= 0x0C7F:
            return "te" # Telugu
        if 0x0C80 <= code <= 0x0CFF:
            return "kn" # Kannada
        if 0x0D00 <= code <= 0x0D7F:
            return "ml" # Malayalam
        if 0x0A00 <= code <= 0x0A7F:
            return "pa" # Punjabi
        if 0x0B00 <= code <= 0x0B7F:
            return "or" # Odia
        if 0x0900 <= code <= 0x097F:
            if any(w in combined.lower() for w in ["आहे", "नाही", "करा", "माझे", "तुमचे", "मला", "धन्यवाद", "सांगा", "नाव", "हवी"]):
                return "mr" # Marathi
            return "hi" # Hindi

    # 2. Transliterated / Romanized keyword detection
    tl = combined.lower()
    if any(w in tl for w in ["tamaru", "maaru", "mane", "daant", "chhe", "thik chhe", "kari dyo", "kari do", "bhaley", "chokkas", "nathi", "aavse"]):
        return "gu"
    if any(w in tl for w in ["maze", "tumche", "mala", "dant", "aahe", "nahit", "sangto", "karaycha", "havi"]):
        return "mr"
    if any(w in tl for w in ["amar", "apnar", "achhe", "korun", "bhalo", "hobe", "dante"]):
        return "bn"
    if any(w in tl for w in ["ennudaiya", "ungaludaiya", "pallu", "irukku", "pannunga", "solunga"]):
        return "ta"
    if any(w in tl for w in ["naa", "mee", "pallu", "undi", "cheyandi", "cheppandi"]):
        return "te"
    if any(w in tl for w in ["nanna", "nimma", "hallu", "ide", "madi", "heli"]):
        return "kn"
    if any(w in tl for w in ["ente", "ningalude", "pallu", "undu", "cheyyuka", "parayu"]):
        return "ml"
    if any(w in tl for w in ["tuhada", "dand", "karo", "dasso", "haanji"]):
        return "pa"
    if any(w in tl for w in ["mera", "aapka", "mujhe", "daant", "hai", "kripya", "kar do", "theek hai", "haan", "bataiye"]):
        return "hi"
        
    return "en"

CONFIRMATION_MESSAGES_11 = {
    "gu": "તમારી અપૉઇન્ટમેન્ટ રિક્વેસ્ટ સફળતાપૂર્વક સબમિટ થઈ ગઈ છે! અમારી ટીમ ટૂંક સમયમાં તમારો સંપર્ક કરશે.",
    "hi": "आपकी अपॉइंटमेंट रिक्वेस्ट सफलतापूर्वक सबमिट हो गई है! हमारी टीम जल्द ही आपसे संपर्क करेगी।",
    "mr": "तुमची अपॉइंटमेंट विनंती यशस्वीरीत्या सबमिट झाली आहे! आमची टीम लवकरच तुमच्याशी संपर्क साधेल.",
    "bn": "আপনার অ্যাপয়েন্টমেন্ট সফলভাবে জমা হয়েছে! আমাদের দল শীঘ্রই আপনার সাথে যোগাযোগ করবে।",
    "ta": "உங்கள் அப்பாயின்ட்மென்ட் கோரிக்கை வெற்றிகரமாக சமர்ப்பிக்கப்பட்டது! எங்கள் குழு விரைவில் உங்களைத் தொடர்பு கொள்ளும்.",
    "te": "మీ అపాయింట్‌మెంట్ అభ్యర్థన విజయవంతంగా సమర్పించబడింది! మా బృందం త్వరలోనే మిమ్మల్ని సంప్రదిస్తుంది.",
    "kn": "ನಿಮ್ಮ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ವಿನಂತಿಯನ್ನು ಯಶಸ್ವಿಯಾಗಿ ಸಲ್ಲಿಸಲಾಗಿದೆ! ನಮ್ಮ ತಂಡವು ಶೀಘ್ರದಲ್ಲೇ ನಿಮ್ಮನ್ನು ಸಂಪರ್ಕಿಸುತ್ತದೆ.",
    "ml": "നിങ്ങളുടെ അപ്പോയിന്റ്മെന്റ് അഭ്യർത്ഥന വിജയകരമായി സമർപ്പിച്ചു! ഞങ്ങളുടെ ടീം ഉടൻ നിങ്ങളെ ബന്ധപ്പെടും.",
    "pa": "ਤੁਹਾਡੀ ਮੁਲਾਕਾਤ ਦੀ ਬੇਨਤੀ ਸਫਲਤਾਪੂਰਵਕ ਜਮ੍ਹਾਂ ਹੋ ਗਈ ਹੈ! ਸਾਡੀ ਟੀਮ ਜਲਦੀ ਹੀ ਤੁਹਾਡੇ ਨਾਲ ਸੰਪਰਕ ਕਰੇਗੀ।",
    "or": "ଆପଣଙ୍କ ଆପଏଣ୍ଟମେଣ୍ଟ ଅନୁରୋଧ ସଫଳତାର ସହ ଦାଖଲ ହୋଇଛି! ଆମ ଟିମ୍ ଖୁବ୍ ଶୀଘ୍ର ଆପଣଙ୍କ ସହ ଯୋଗାଯୋଗ କରିବ।",
    "en": "Your appointment request has been successfully submitted! Our team will contact you shortly to confirm your schedule."
}

def get_review_summary_prompt(lang, display_name, ph, ct, cn, dr, is_update=False):
    if is_update:
        prompts = {
            "gu": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Warmly acknowledge the update in ONE short phrase, and THEN YOU ARE STRICTLY REQUIRED TO RE-RECITE THE FULL 5-FIELD REVIEW SUMMARY in Gujarati without omitting any line:\n'કોઈ વાંધો નહીં! મેં વિગત અપડેટ કરી દીધી છે. તમારી અપડેટ કરેલી વિગતો:\n- નામ: {display_name}\n- ફોન: {ph}\n- શહેર: {ct}\n- સમસ્યા: {cn}\n- ડૉક્ટર: {dr}\n\nકૃપા કરીને આ અપડેટ કરેલ અપૉઇન્ટમેન્ટ રિક્વેસ્ટ મોકલવા માટે 'submit' કહો અથવા રદ કરવા માટે 'cancel' કહો.'",
            "hi": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Warmly acknowledge the update in ONE short phrase, and THEN YOU ARE STRICTLY REQUIRED TO RE-RECITE THE FULL 5-FIELD REVIEW SUMMARY in Hindi without omitting any line:\n'कोई बात नहीं! मैंने विवरण अपडेट कर दिया है। आपके अपडेट किए गए विवरण:\n- नाम: {display_name}\n- फ़ोन: {ph}\n- शहर: {ct}\n- समस्या: {cn}\n- डॉक्टर: {dr}\n\nकृपया इस अपडेट किए गए अपॉइंटमेंट अनुरोध को भेजने के लिए 'submit' कहें या रद्द करने के लिए 'cancel' कहें।'",
            "mr": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Marathi:\n'काही हरकत नाही! मी तपशील अपडेट केला आहे. तुमचे अपडेट केलेले तपशील:\n- नाव: {display_name}\n- फोन: {ph}\n- शहर: {ct}\n- समस्या: {cn}\n- डॉक्टर: {dr}\n\nकृपया ही अपॉइंटमेंट विनंती पाठवण्यासाठी 'submit' लिहा किंवा म्हणा.'",
            "bn": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Bengali:\n'কোন সমস্যা নেই! আমি বিবরণ আপডেট করেছি। আপনার আপডেট করা বিবরণ:\n- নাম: {display_name}\n- ফোন: {ph}\n- শহর: {ct}\n- সমস্যা: {cn}\n- ডাক্তার: {dr}\n\nঅনুগ্রহ করে এই অ্যাপয়েন্টমেন্ট পাঠানোর জন্য 'submit' লিখুন বা বলুন।'",
            "ta": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Tamil:\n'பிரச்சனை இல்லை! நான் விவரத்தை புதுப்பித்துள்ளேன். உங்கள் புதுப்பிக்கப்பட்ட விவரங்கள்:\n- பெயர்: {display_name}\n- தொலைபேசி: {ph}\n- நகரம்: {ct}\n- பிரச்சனை: {cn}\n- மருத்துவர்: {dr}\n\nஇந்த அப்பாயின்ட்மென்ட் கோரிக்கையை அனுப்ப தயவுசெய்து 'submit' என எழுதவும் அல்லது சொல்லவும்.'",
            "te": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Telugu:\n'పర్వాలేదు! నేను వివరాలను అప్‌డేట్ చేసాను. మీ అప్‌డేట్ చేసిన వివరాలు:\n- పేరు: {display_name}\n- ఫోన్: {ph}\n- నగరం: {ct}\n- సమస్య: {cn}\n- డాక్టర్: {dr}\n\nదయచేసి ఈ అపాయిಂట్‌మెంట్ అభ్యర్థనను పంపడానికి 'submit' అని రాయండి లేదా చెప్పండి.'",
            "kn": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Kannada:\n'ಪರವಾಗಿಲ್ಲ! ನಾನು ವಿವರವನ್ನು ನವೀಕರಿಸಿದ್ದೇನೆ. ನಿಮ್ಮ ನವೀಕರಿಸಿದ ವಿವರಗಳು:\n- ಹೆಸರು: {display_name}\n- ಫೋನ್: {ph}\n- ನಗರ: {ct}\n- ಸಮಸ್ಯೆ: {cn}\n- ವೈದ್ಯರು: {dr}\n\nದಯವಿಟ್ಟು ಈ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ವಿನಂತಿಯನ್ನು ಕಳುಹಿಸಲು 'submit' ಎಂದು ಬರೆಯಿರಿ ಅಥವಾ ಹೇಳಿ.'",
            "ml": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Malayalam:\n'പ്രശ്നമില്ല! ഞാൻ വിവരങ്ങൾ അപ്ഡേറ്റ് ചെയ്തിട്ടുണ്ട്. നിങ്ങളുടെ അപ്ഡേറ്റ് ചെയ്ത വിവരങ്ങൾ:\n- പേര്: {display_name}\n- ഫോൺ: {ph}\n- നഗരം: {ct}\n- പ്രശ്നം: {cn}\n- ഡോക്ടർ: {dr}\n\nഈ അപ്പോയിന്റ്മെന്റ് അഭ്യർത്ഥന അയയ്ക്കാൻ ദയവായി 'submit' എന്ന് എഴുതുകയോ പറയുകയോ ചെയ്യുക.'",
            "pa": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Punjabi:\n'ਕੋਈ ਗੱਲ ਨਹੀਂ! ਮੈਂ ਵੇਰਵੇ ਅੱਪਡੇਟ ਕਰ ਦਿੱਤੇ ਹਨ। ਤੁਹਾਡੇ ਅੱਪਡੇਟ ਕੀਤੇ ਵੇਰਵੇ:\n- ਨਾਮ: {display_name}\n- ਫ਼ੋਨ: {ph}\n- ਸ਼ਹਿਰ: {ct}\n- ਸਮੱਸਿਆ: {cn}\n- ਡਾਕਟਰ: {dr}\n\nਕਿਰਪਾ ਕਰਕੇ ਇਸ ਮੁਲਾਕਾਤ ਦੀ ਬੇਨਤੀ ਭੇਜਣ ਲਈ 'submit' ਲਿਖੋ ਜਾਂ ਕਹੋ।'",
            "or": f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Present the full 5-field review summary in Odia:\n'କୌଣସି ଅସୁବିଧା ନାହିଁ! ମୁଁ ବିବରଣୀ ଅପଡେଟ୍ କରିଛି। ଆପଣଙ୍କ ଅପଡେଟ୍ ହୋଇଥିବା ବିବରଣୀ:\n- ନାମ: {display_name}\n- ଫୋନ୍: {ph}\n- ସହର: {ct}\n- ସମସ୍ୟା: {cn}\n- ଡାକ୍ତର: {dr}\n\nଦୟାକରି ଏହି ଆପଏଣ୍ଟମେଣ୍ଟ ଅନୁରୋଧ ପଠାଇବା ପାଇଁ 'submit' ଲେଖନ୍ତୁ କିମ୍ବା କୁହନ୍ତୁ।'"
        }
        return prompts.get(lang, f"NEXT STEP (MANDATORY RE-RECITAL OF UPDATED DETAILS): The patient updated their details. Warmly acknowledge the update in ONE short phrase, and THEN YOU ARE STRICTLY REQUIRED TO RE-RECITE THE FULL 5-FIELD REVIEW SUMMARY in full without omitting any line:\n'No problem! I have updated that detail. Here are your complete updated appointment details:\n- Name: {display_name}\n- Phone: {ph}\n- City: {ct}\n- Concern: {cn}\n- Doctor: {dr}\n\nPlease write or say 'submit' to submit this updated appointment request.'")
    else:
        prompts = {
            "gu": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Gujarati and ask the user to write/say 'submit':\n'આભાર! તમારી બધી વિગતો નોંધી લીધી છે:\n- નામ: {display_name}\n- ફોન: {ph}\n- શહેર: {ct}\n- સમસ્યા: {cn}\n- ડૉક્ટર: {dr}\n\nકૃપા કરીને આ અપૉઇન્ટમેન્ટ રિક્વેસ્ટ મોકલવા માટે 'submit' લખો અથવા કહો.'",
            "hi": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Hindi and ask the user to write/say 'submit':\n'धन्यवाद! आपके सभी विवरण दर्ज कर लिए गए हैं:\n- नाम: {display_name}\n- फ़ोन: {ph}\n- शहर: {ct}\n- समस्या: {cn}\n- डॉक्टर: {dr}\n\nकृपया इस अपॉइंटमेंट अनुरोध को भेजने के लिए 'submit' लिखें या कहें।'",
            "mr": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Marathi and ask the user to write/say 'submit':\n'धन्यवाद! तुमचे सर्व तपशील नोंदवले गेले आहेत:\n- नाव: {display_name}\n- फोन: {ph}\n- शहर: {ct}\n- समस्या: {cn}\n- डॉक्टर: {dr}\n\nकृपया ही अपॉइंटमेंट विनंती पाठवण्यासाठी 'submit' लिहा किंवा म्हणा.'",
            "bn": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Bengali and ask the user to write/say 'submit':\n'ধন্যবাদ! আপনার সমস্ত বিবরণ নথিভুক্ত করা হয়েছে:\n- নাম: {display_name}\n- ফোন: {ph}\n- শহর: {ct}\n- সমস্যা: {cn}\n- ডাক্তার: {dr}\n\nঅনুগ্রহ করে এই অ্যাপয়েন্টমেন্ট পাঠানোর জন্য 'submit' লিখুন বা বলুন।'",
            "ta": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Tamil and ask the user to write/say 'submit':\n'நன்றி! உங்கள் அனைத்து விவரங்களும் பதிவு செய்யப்பட்டுள்ளன:\n- பெயர்: {display_name}\n- தொலைபேசி: {ph}\n- நகரம்: {ct}\n- பிரச்சனை: {cn}\n- மருத்துவர்: {dr}\n\nஇந்த அப்பாயின்ட்மென்ட் கோரிக்கையை அனுப்ப தயவுசெய்து 'submit' என எழுதவும் அல்லது சொல்லவும்.'",
            "te": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Telugu and ask the user to write/say 'submit':\n'ధన్యవాదాలు! మీ వివరాలన్నీ నమోదు చేయబడ్డాయి:\n- పేరు: {display_name}\n- ఫోన్: {ph}\n- నగరం: {ct}\n- సమస్య: {cn}\n- డాక్టర్: {dr}\n\nదయచేసి ఈ అపాయింట్‌మెంట్ అభ్యర్థనను పంపడానికి 'submit' అని రాయండి లేదా చెప్పండి.'",
            "kn": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Kannada and ask the user to write/say 'submit':\n'ಧನ್ಯವಾದಗಳು! ನಿಮ್ಮ ಎಲ್ಲಾ ವಿವರಗಳನ್ನು ದಾಖಲಿಸಲಾಗಿದೆ:\n- ಹೆಸರು: {display_name}\n- ಫೋನ್: {ph}\n- ನಗರ: {ct}\n- ಸಮಸ್ಯೆ: {cn}\n- ವೈದ್ಯರು: {dr}\n\nದಯವಿಟ್ಟು ಈ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ವಿನಂತಿಯನ್ನು ಕಳುಹಿಸಲು 'submit' ಎಂದು ಬರೆಯಿರಿ ಅಥವಾ ಹೇಳಿ.'",
            "ml": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Malayalam and ask the user to write/say 'submit':\n'നന്ദി! നിങ്ങളുടെ എല്ലാ വിവരങ്ങളും രേഖപ്പെടുത്തിയിട്ടുണ്ട്:\n- പേര്: {display_name}\n- ഫോൺ: {ph}\n- നഗരം: {ct}\n- പ്രശ്നം: {cn}\n- ഡോക്ടർ: {dr}\n\nഈ അപ്പോയിന്റ്മെന്റ് അഭ്യർത്ഥന അയയ്ക്കാൻ ദയവായി 'submit' എന്ന് എഴുതുകയോ പറയുകയോ ചെയ്യുക.'",
            "pa": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Punjabi and ask the user to write/say 'submit':\n'ਧੰਨਵਾਦ! ਤੁਹਾਡੇ ਸਾਰੇ ਵੇਰਵੇ ਦਰਜ ਕਰ ਲਏ ਗਏ ਹਨ:\n- ਨਾਮ: {display_name}\n- ਫ਼ੋਨ: {ph}\n- ਸ਼ਹਿਰ: {ct}\n- ਸਮੱਸਿਆ: {cn}\n- ਡਾਕਟਰ: {dr}\n\nਕਿਰਪਾ ਕਰਕੇ ਇਸ ਮੁਲਾਕਾਤ ਦੀ ਬੇਨਤੀ ਭੇਜਣ ਲਈ 'submit' ਲਿਖੋ ਜਾਂ ਕਹੋ।'",
            "or": f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary in Odia and ask the user to write/say 'submit':\n'ଧନ୍ୟବାଦ! ଆପଣଙ୍କର ସମସ୍ତ ବିବରଣୀ ରେକର୍ଡ କରାଯାଇଛି:\n- ନାମ: {display_name}\n- ଫୋନ୍: {ph}\n- ସହର: {ct}\n- ସମସ୍ୟା: {cn}\n- ଡାକ୍ତର: {dr}\n\nଦୟାକରି ଏହି ଆପଏଣ୍ଟମେଣ୍ଟ ଅନୁରୋଧ ପଠାଇବା ପାଇଁ 'submit' ଲେଖନ୍ତୁ କିମ୍ବା କୁହନ୍ତୁ।'"
        }
        return prompts.get(lang, f"NEXT STEP: All details are collected! Do NOT re-ask any details. Present the complete all-at-once review summary and ask the user to write/say 'submit':\n'Thank you! Let me review all your details:\n- Name: {display_name}\n- Phone: {ph}\n- City: {ct}\n- Concern: {cn}\n- Doctor: {dr}\n\nPlease write or say 'submit' to submit this appointment request to our clinic team.'")

def get_missing_field_message(lang, missing_type, city=None):
    messages = {
        "name": {
            "gu": "તમારી અપૉઇન્ટમેન્ટ સબમિટ કરતાં પહેલાં, કૃપા કરીને તમારું પૂરું નામ જણાવશો?",
            "hi": "आपकी अपॉइंटमेंट सबमिट करने से पहले, कृपया अपना पूरा नाम बताएं?",
            "mr": "तुमची अपॉइंटमेंट सबमिट करण्यापूर्वी, कृपया तुमचे पूर्ण नाव सांगा?",
            "bn": "আপনার অ্যাপয়েন্টমেন্ট জমা দেওয়ার আগে, দয়া করে আপনার পুরো নাম বলুন?",
            "ta": "உங்கள் அப்பாயின்ட்மென்ட்டை சமர்ப்பிக்கும் முன், தயவுசெய்து உங்கள் முழு பெயரை கூறவும்?",
            "te": "మీ అపాయింట్‌מెంట్‌ను సమర్పించే ముందు, దయచేసి మీ పూర్తి పేరును చెప్పండి?",
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
            "te": "మీ అపాయింట్‌מెంట్‌ను సమర్పించే ముందు, మీరు ఏ నగరంలో ఉన్నారు?",
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
            "te": "మీ అపాయింట్‌מెంట్‌ను సమర్పించే ముందు, మీకు దంతాల సమస్య ఏమిటి?",
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
            "te": f"మీ అపాయింట్‌מెంట్‌ను సమర్పించే ముందు, మీరు {city or 'నగరంలో'} ఏ USD సర్టిఫైడ్ డాక్టర్‌తో సంప్రదించాలనుకుంటున్నారు?",
            "kn": f"ನಿಮ್ಮ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಸಲ್ಲಿಸುವ ಮೊದಲು, ನೀವು {city or 'ನಗರದಲ್ಲಿ'} ಯಾವ USD ಪ್ರಮಾಣೀಕೃತ ವೈದ್ಯರನ್ನು ಸಂಪರ್କಿಸಲು ಬಯಸುತ್ತೀರಿ?",
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
            "te": "మీ అపాయింట్‌מెంట్‌ను సమర్పించే ముందు, దయచేసి మీ 10 అంకెల మొబైల్ నంబర్‌ను ఇవ్వండి?",
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
            "a", "an", "the", "in", "on", "at", "to", "for", "from", "with", "by", "of", "and", "or", "but", "so",
            "planning", "looking", "interested", "trying", "wondering", "suffering", "having", "scared", "worried",
            "afraid", "visiting", "going", "coming", "thinking", "asking", "seeking", "facing", "feeling", "living",
            "staying", "working", "traveling", "searching", "needing", "inquiring", "booking", "consulting", "checking",
            "here", "there", "just", "only", "also", "now", "already", "currently", "actually", "sure", "unsure",
            "ready", "happy", "excited", "trip", "dubai", "india", "patient", "user", "dentist", "doctor",
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
            if any(q in tl for q in [
                "explain", "what is", "what's", "whats", "how does", "how do", "tell me about", "can you tell", "cost of", "price of",
                "su che", "shu chhe", "su chhe", "shu che", "etle su", "etle shu", "matlab", "meaning", "mean", "kya hai", "kaise hota", "samjhao", "samjhavo", "batao", "batana", "detail", "information",
                "janvu", "janna"
            ]):
                return ""

            symptoms = []
            # 1. Pain / Dard / Dukhavo
            if any(w in tl for w in [
                "dukhavo", "dukhaavo", "dukhado", "dukhadho", "dukhavu", "dukhe", "dukh", "dukh se", "dukh che", "dukh chhe", "dard", "pain", "teeth pain", "tooth pain", "dant dard", "daant dard", "daant ma dukhaavo", "dant ma dukhavo", "pida", "peeda",
                "દુખાવો", "દુઃખાવો", "દાંતમાં દુખાવો", "દાંત નો દુખાવો", "દાંતમાં દર્દ", "પીડા", "દુખે છે", "દાંત દુખે છે",
                "दांत में दर्द", "दांत का दर्द", "दांत दर्द", "दांतों में दर्द", "दाढ़ में दर्द", "दांत दुख रहा है", "दर्द होता है", "पीड़ा", "दांत दुखत आहे",
                "dante byatha", "pal vali", "panti noppi", "hallu novu", "pallu vedana", "dand peerh", "danta bindha"
            ]):
                symptoms.append("pain in teeth")

            # 2. Black spots / dark discoloration
            if any(w in tl for w in ["kala", "kaala", "black", "black spot", "black spots", "black teeth", "dhabba", "કાળા", "કાળા ડાઘ", "કાળા દાંત", "काला", "काले दांत", "दांत में काला"]):
                symptoms.append("black spots / dark discoloration")

            # 3. Yellow stains / discoloration
            if any(w in tl for w in ["yellow", "stain", "stains", "discolor", "bleach", "shade", "dull", "pila", "peela", "daag", "dhabba", "પીળા", "ડાઘ", "પીળા દાંત", "पीले दांत", "दांत पीले"]):
                symptoms.append("yellow stains / discoloration")

            # 4. Cavity / decay / kido / sado
            if any(w in tl for w in ["cavity", "decay", "sado", "kido", "keeda", "khado", "khadho", "સડો", "કીડો", "ખાડો", "કેવિટી", "सड़न", "कीड़ा", "कैविटी", "दांत में कीड़ा"]):
                symptoms.append("dental cavity and decay")

            # 5. Crooked / misaligned / irregular teeth
            if any(w in tl for w in ["crooked", "misaligned", "crowded", "overlap", "straighten", "unorganise", "unorganized", "irregular", "uneven", "tedhe", "terhe", "alignment", "વાંકા", "વાંકા દાંત", "टेढ़े दांत", "दांत सीधे"]):
                symptoms.append("irregular and misaligned teeth")

            # 6. Chipped / broken / cracked teeth
            if any(w in tl for w in ["chip", "broken", "crack", "punch", "toot", "bhangi", "broken tooth", "chipped tooth", "તૂટેલા", "તૂટી ગયા", "ટુકડો", "ટૂટી ગયા", "टूट गया", "टूटा दांत", "टूटे दांत", "दांत टूट गया"]):
                symptoms.append("chipped or broken teeth")

            # 7. Missing teeth
            if any(w in tl for w in ["missing teeth", "lost teeth", "lost tooth", "daant nathi", "dant nathi", "teeth missing", "દાંત નથી", "दांत नहीं हैं", "दांत निकल गया"]):
                symptoms.append("missing teeth")

            # 8. Swelling / Masa / Gum inflammation / Pyorrhea
            if any(w in tl for w in [
                "masa", "masaa", "masudo", "masuda", "sujan", "soojan", "sooj", "suj", "swelling", "gum swelling", "swollen", "inflammation",
                "સૂજન", "મસા", "દાંતમાં મસા", "પેઢામાં સોજો", "સોજો", "મસો થયો",
                "मसूड़ों में सूजन", "मसूड़े", "मसूड़ों", "सूजन", "मसा", "दांत में सूजन", "मसूड़े सूज गए"
            ]):
                symptoms.append("gum swelling and inflammation")

            # 9. Bleeding gums
            if any(w in tl for w in ["lohi", "khoon", "bleeding", "gum bleeding", "blood", "લોહી", "દાંતમાંથી લોહી", "પેઢામાંથી લોહી", "खून", "दांत से खून", "मसूड़ों से खून"]):
                symptoms.append("bleeding gums and sensitivity")

            # 10. Gap between teeth / Spacing
            if any(w in tl for w in ["gap", "gaps", "spacing", "space", "vachhe gap", "bich me gap", "jagya", "khali jagya", "ગૅપ", "ગેપ", "જગ્યા", "ગેપ છે", "गैप", "जगह", "दांतों में गैप", "दांतों के बीच गैप"]):
                symptoms.append("gap between teeth")

            # 11. Loose / Mobile teeth
            if any(w in tl for w in ["hale", "hale chhe", "hil", "hil raha", "loose tooth", "loose teeth", "shaking", "હલે છે", "દાંત હલે છે", "हिलना", "दांत हिल रहे हैं"]):
                symptoms.append("loose or mobile teeth")

            # 12. Upcoming wedding / event
            if any(w in tl for w in ["wedding", "marriage", "lagan", "lagna", "shaadi", "લગ્ન", "शादी", "विवाह"]):
                symptoms.append("upcoming wedding preparation")

            # 13. Smile Makeover / Smile Design
            if any(w in tl for w in ["smile makeover", "smile correction", "smile improve", "mari smile sudharvi", "smile badalvi", "smile banavi", "want smile design", "need smile design", "स्माइल सुधारना", "स्माइल मेकओवर", "smile transformation"]):
                symptoms.append("smile makeover and design")

            # 14. Whitening & Brightening
            if any(w in tl for w in ["chamkav", "chamkavva", "chamkavu", "chamkavvu", "chamkana", "whitening", "white", "shining", "white teeth", "teeth shine", "teeth shining", "shine", "sparkle", "brighten", "bright", "ચમકાવવા", "ચમકાવવું", "ચમકાવ", "ચમકતા", "चमकाना", "दांत चमकाना", "દાંત ચમકાવવા", "સફેદ", "सफेद"]):
                symptoms.append("teeth whitening and smile makeover")

            # 15. Sensitivity & Infection / RCT
            if any(w in tl for w in ["rog", "rog se", "bimari", "infection", "rct", "root canal", "sensitivity", "khanva ma", "thandu garam", "thanda garam", "કાનમાં", "ઠંડુ ગરમ", "સેન્સિટિવિટી", "પાયોરિયા", "પાયોરીયા", "pyorrhea", "gingivitis", "ठंडा गरम", "झनझनाहट", "सेंसिटिविटी"]):
                symptoms.append("dental sensitivity and infection")

            # 16. Multilingual Generic Concern / Samasya / Problem / Takleef / Pareshani / Dikkat
            if any(w in tl for w in [
                "samasya", "samasy", "samasyaa", "dikkat", "takleef", "taklif", "pareshaani", "pareshani", "problem", "issue", "trouble", "traas", "shomoshya", "pirachanai", "prashnam", "samasye", "tention", "tension",
                "સમસ્યા", "તકલીફ", "દિક્કત", "પરેશાની", "પ્રોબ્લેમ", "રોગ", "સમસ્યા છે", "તકલીફ છે", "દિક્કત છે",
                "समस्या", "दिक्कत", "परेशानी", "प्रॉब्लम", "तकलीफ", "बीमारी", "रोग", "समस्या है", "दिक्कत है", "तकलीफ है", "त्रास", "त्रास आहे",
                "সমস্যা", "பிரச்சனை", "சமஸ்யா", "సమస్య", "సమస్య ఉంది", "ಸಮಸ್ಯೆ", "ಸಮಸ್ಯೆ ಇದೆ", "പ്രശ്നം", "പ്രശ്നമുണ്ട്", "ਸਮੱਸਿਆ", "ਸਮੱਸਿਆ ਹੈ", "ସମସ୍ୟା"
            ]):
                symptoms.append("dental concern and consultation")

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
                "అవును", "సరే", "తప్పకుండా", "సమర్పించండి", "சబ్మిట్", "సబ్మిట్ చేయండి", "అవును సబ్మిట్ చేయండి",
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
            for turn in reversed(history):
                if turn.get("role") in ["model", "assistant"]:
                    p_txt = get_turn_text(turn)
                    sum_slots_last = extract_slots_from_review_summary(p_txt)
                    if sum_slots_last:
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
            for turn in history:
                role = turn.get("role")
                p = get_turn_text(turn)
                if not p:
                    continue
                if role in ["user", "client"]:
                    # Check city in history
                    c_found = extract_certified_city_from_text(p)
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
                        m_exp = re.search(r"(?:my name is|my full name is|myself|call me|i am|i'm|this is|મારું નામ|મારુ નામ|મારો નામ|મારી નામ|(?:maru|maro|maaru|mari|mera|meri|apna|majhe|amar)\s+(?:naam|nam|name|naav|nav|नाव|નામ|नाम)|maru naam|maro naam|maru nam|maro nam|नाम|मेरा नाम|mera naam|mera nam|नाव|माझे नाव|majhe nav|নাম|আমার নাম|amar naam|பெயர்|என் பெயர்|en peyar|పేరు|నా పేరు|naa peru|ಹೆಸರು|ನನ್ನ ಹೆಸರು|nanna hesaru|പേര്|എന്റെ പേര്|ente peru|ਨਾਮ|ਮੇਰਾ ਨਾਮ|mera naa|ਨਾਮ|ਮੋરા ਨਾਮ|mora nama)\s*[:：\-]?\s*([A-Za-z\u0A80-\u0AFF\u0900-\u097F\u0980-\u09FF\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F\u0A00-\u0A7F\u0B00-\u0B7F\s]{2,60})", p, re.IGNORECASE)
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

        # Enforce Doctor-City consistency only if city is not set
        h_doc = self.session.booking_slots.get("doctor_name")
        if h_doc and not self.session.booking_slots.get("city"):
            doc_h_city = get_city_for_doctor(h_doc)
            if doc_h_city:
                self.session.booking_slots["city"] = doc_h_city

        if user_text:
            text = user_text.strip()
            
            # Detect general update / change intent
            is_update_intent = any(w in text.lower() for w in [
                "change", "update", "correct", "modify", "instead", "edit", "wrong", "mistake",
                "badlo", "badlu", "badlavu", "badlavvu", "sudharo", "sudharvu", "ferfar", "badal",
                "નથી", "ખોટું", "બદલ", "બદલો", "બદલવો", "બદલવી", "બદલવા", "બદલવું", "અપડેટ", "સુધાર", "સુધારો", "સુધારવું", "ફેરફાર", "નંબર બદલો", "નામ બદલો", "શહેર બદલો", "ડૉક્ટર બદલો", "સમસ્યા બદલો",
                "नहीं", "गलत", "बदल", "बदलो", "बदलना", "अपडेट", "सुधार", "सुधारो", "सुधारना", "नंबर बदलो", "नाम बदलो", "शहर बदलो", "डॉक्टर बदलो", "समस्या बदलो"
            ])
            if is_update_intent:
                self.session.booking_slots["is_submitted"] = False
                self.session.slot_just_updated = True

            # Detect specific field edit intent where user has NOT provided the new value yet
            is_phone_edit_req = any(w in text.lower() for w in ["phone", "number", "no", "mobile", "fon", "fone", "ફોન", "નંબર", "મોબાઇલ", "फोन", "नंबर", "मोबाइल"])
            is_city_edit_req = any(w in text.lower() for w in ["city", "shahar", "shaher", "sahar", "nagar", "place", "location", "શહેર", "નગર", "शहर", "नगर"])
            is_doc_edit_req = any(w in text.lower() for w in ["doctor", "dr", "dentist", "daktar", "dakatar", "ડૉક્ટર", "ડોક્ટર", "डॉक्टर"])
            is_name_edit_req = any(w in text.lower() for w in ["name", "naam", "નામ", "नाम", "नाव", "પૂરું નામ", "pura naam", "full name"])
            is_concern_edit_req = any(w in text.lower() for w in ["concern", "problem", "issue", "samasya", "samasy", "takleef", "dard", "સમસ્યા", "તકલીફ", "દર્દ", "समस्या", "तकलीफ", "दर्द"])
            
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

            # Doctor detection in user text
            doc_found = find_doctor_in_text(text, self.session.booking_slots.get("city"))
            if doc_found:
                if self.session.booking_slots.get("doctor_name") != doc_found:
                    self.session.booking_slots["doctor_name"] = doc_found
                    self.session.booking_slots["is_submitted"] = False
                    self.session.slot_just_updated = True
                self.session.pending_doctor_candidate = None
                self.session.last_uncertified_doctor = None
                self.session.asking_for_field = None
                doc_home_city = get_city_for_doctor(doc_found)
                cur_city = self.session.booking_slots.get("city")
                if doc_home_city and (not cur_city or cur_city.lower() != doc_home_city.lower()):
                    self.session.booking_slots["city"] = doc_home_city
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
                    doc_city = get_city_for_doctor(self.session.booking_slots["doctor_name"])
                    if doc_city and not self.session.booking_slots.get("city"):
                        self.session.booking_slots["city"] = doc_city
                elif text.lower().strip() in ["no", "na", "nah", "nope", "nathi", "nahi"]:
                    self.session.pending_doctor_candidate = None
            elif not self.session.booking_slots.get("doctor_name"):
                doc_partial = find_partial_doctor(text, self.session.booking_slots.get("city"))
                if doc_partial:
                    self.session.pending_doctor_candidate = doc_partial
                else:
                    uncert_user = detect_uncertified_doctor(text)
                    if uncert_user:
                        self.session.last_uncertified_doctor = uncert_user
                    else:
                        self.session.last_uncertified_doctor = None

            # City extraction from user text
            c_user = extract_certified_city_from_text(text)
            if c_user:
                old_c = self.session.booking_slots.get("city")
                if old_c != c_user:
                    self.session.booking_slots["city"] = c_user
                    self.session.unsupported_city = None
                    # ALWAYS clear doctor on city change so patient chooses a certified doctor in the new city
                    self.session.booking_slots["doctor_name"] = ""
                    self.session.pending_doctor_candidate = None
                    self.session.booking_slots["is_submitted"] = False
                    self.session.slot_just_updated = True
                    self.session.city_just_changed = True
                    self.session.asking_for_field = "doctor"
            elif is_update_intent and is_city_edit_req:
                # User wants to update city but hasn't provided city yet
                self.session.booking_slots["city"] = ""
                self.session.booking_slots["doctor_name"] = ""
                self.session.booking_slots["is_submitted"] = False
                self.session.slot_just_updated = False
                self.session.asking_for_field = "city"
            else:
                for city in UNSUPPORTED_CITIES:
                    if re.search(r"\b" + re.escape(city) + r"\b", text, re.IGNORECASE):
                        self.session.unsupported_city = city.capitalize()
                        self.session.booking_slots["city"] = ""
                        self.session.booking_slots["doctor_name"] = ""
                        self.session.booking_slots["is_submitted"] = False
                        self.session.slot_just_updated = True
                        break

            # If doctor is set, ensure city is populated
            if self.session.booking_slots.get("doctor_name") and not self.session.booking_slots.get("city"):
                doc_c = get_city_for_doctor(self.session.booking_slots["doctor_name"])
                if doc_c:
                    self.session.booking_slots["city"] = doc_c

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
                # Bare name detection: ALWAYS allowed if user provides a 1 or 2 word valid name, or supplies their surname
                bare_name_pat = r"^([A-Za-z\u0A80-\u0AFF\u0900-\u097F\u0980-\u09FF\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F\u0A00-\u0A7F\u0B00-\u0B7F]{2,20})(?:\s+([A-Za-z\u0A80-\u0AFF\u0900-\u097F\u0980-\u09FF\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F\u0A00-\u0A7F\u0B00-\u0B7F]{2,20}))?$"
                m_bare = re.search(bare_name_pat, text.strip(), re.IGNORECASE)
                if m_bare:
                    raw_fn = m_bare.group(1).strip()
                    raw_ln = m_bare.group(2).strip() if m_bare.group(2) else ""
                    f_name = transliterate_to_english(raw_fn).strip().capitalize() if any(ord(c) > 127 for c in raw_fn) else raw_fn.capitalize()
                    l_name = transliterate_to_english(raw_ln).strip().capitalize() if (raw_ln and any(ord(c) > 127 for c in raw_ln)) else (raw_ln.capitalize() if raw_ln else "")

                    # If user gave only surname (e.g. "Parmar") while first name is already known (e.g. "Bhavin")
                    if f_name and not l_name:
                        cur_fn = self.session.booking_slots.get("first_name")
                        if cur_fn and cur_fn.lower() != f_name.lower():
                            l_name = f_name
                            f_name = cur_fn

                    if is_valid_name(f_name, l_name or "-"):
                        self.session.user_name = f"{f_name} {l_name}".strip() if (l_name and l_name != "-") else f_name
                        self.session.booking_slots["first_name"] = f_name
                        self.session.booking_slots["last_name"] = l_name if l_name else "-"
                        self.session.booking_slots["is_submitted"] = False
                        self.session.asking_for_field = None

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
        
        active_memory = ""
        if self.session.user_name:
            ln_disp = self.session.booking_slots.get('last_name') or '-'
            active_memory += f"\n- CURRENT CONFIRMED PATIENT NAME: {self.session.user_name} (First Name: {self.session.booking_slots.get('first_name')}, Last Name: {ln_disp})"
        else:
            active_memory += "\n- CURRENT PATIENT NAME: Unknown (User has not provided their name yet. Never guess or hallucinate a name. Ask for their name if needed)."

        patient_city = self.session.booking_slots.get("city")
        if patient_city:
            active_memory += f"\n- CURRENT CONFIRMED PATIENT CITY: {patient_city}"
        else:
            active_memory += "\n- CURRENT PATIENT CITY: Unknown (User has not provided their city yet. Never assume Surat, Mumbai, or any city. Ask for their city if needed)."

        patient_phone = self.session.booking_slots.get("phone")
        if patient_phone:
            active_memory += f"\n- CURRENT CONFIRMED 10-DIGIT PHONE: {patient_phone} (Valid 10-digit mobile number confirmed. Do NOT re-ask or question phone; proceed directly to ask for preferred Doctor selection in {patient_city or 'their city'})."
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
            doc = mismatch_info['doctor']
            d_city = mismatch_info['doctor_city']
            u_city = mismatch_info['user_city']
            u_docs = ", ".join(CITY_DOCTORS.get(u_city, []))
            active_memory += (
                f"\n- 🚨 CRITICAL DOCTOR-CITY MISMATCH:\n"
                f"The patient is in '{u_city}', but asked about/requested '{doc}'.\n"
                f"FACT: '{doc}' is located in '{d_city}', NOT in '{u_city}'!\n"
                f"MANDATORY ACTION: Inform the patient that {doc} is located in {d_city}, not in {u_city}.\n"
                f"Offer our certified smile designers in {u_city} ({u_docs}), or ask if they would like to visit {d_city} for {doc}!"
            )
        else:
            active_memory += f"\n- CURRENT PREFERRED DOCTOR: Unknown (Ask which USD Certified Smile Designer in {patient_city or 'their city'} they would like to consult)."

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

        # Detect user's current/recent active language from the 11 supported Indian languages
        user_lang = detect_user_language(user_text, history)

        asking_field = getattr(self.session, 'asking_for_field', None)

        if slots.get("is_submitted") and not asking_field:
            next_step_instruction = (
                f"🚨 MANDATORY POST-SUBMISSION PERMANENT LOCK (CRITICAL OVERRIDE):\n"
                f"The consultation appointment for {self.session.user_name or fn or 'the patient'} (Phone: {ph}, City: {ct}, Doctor: {dr}, Concern: {cn}) has ALREADY BEEN SUCCESSFULLY SUBMITTED to our clinic team!\n"
                f"RULES:\n"
                f"1. NEVER ask 'Shall I book your appointment?', 'Shall I submit your appointment?', 'Should I book your consultation?', 'તમારી અપૉઇન્ટમેન્ટ બુક કરી નાખું?', 'आपकी अपॉइंटमेंट बुक कर दूं?' or offer booking again.\n"
                f"2. UNLESS the user explicitly requests: 'I want to change my appointment', 'modify details', or 'book another appointment', you must NEVER prompt for booking or confirmation.\n"
                f"3. For all other questions regarding veneers, costs, procedures, warranty, and dental care, answer warmly, helpfully, and authoritatively within our dental scope without mentioning booking an appointment. Remember: Strict absolute domain lock applies to all off-topic subjects."
            )
        elif not fn and not self.session.user_name:
            next_step_instruction = "STEP 1 (NAME): Ask for the patient's full name in their language: 'Let's start with your beautiful name, what is your name?'"
        elif asking_field == "name":
            next_step_instruction = f"STEP 1 (NAME UPDATE): The patient wants to update their name. Do NOT present the review summary yet. Ask for their correct full name in {user_lang}: 'Sure! What is your correct full name?' ('ચોક્કસ! તમારું સાચું પૂરું નામ શું છે?')."
        elif not ct or asking_field == "city":
            display_name = f"{fn} {ln}".strip() if (ln and ln != "-" and ln.lower() != fn.lower()) else (self.session.user_name or fn or "Patient")
            next_step_instruction = (
                f"STEP 2 (CITY): The patient's name is '{display_name}'. "
                f"Ask which city they are located in {user_lang}: 'Which city are you located in so I can check for our closest USD Certified Smile Designer?' ('ચોક્કસ! તમે કયા શહેરમાં રહો છો?')."
            )
        elif not cn or asking_field == "concern":
            next_step_instruction = f"STEP 3 (CONCERN): Ask for their dental concern or smile goal in {user_lang}: 'What dental concern or smile improvement would you like to discuss in {ct}?' ('તમારી દાંતની સમસ્યા અથવા સ્માઇલ ગોલ વિશે જણાવશો?')."
        elif not dr or asking_field == "doctor":
            city_docs = CITY_DOCTORS.get(ct, [])
            docs_str = ", ".join(city_docs) if city_docs else "our USD Certified Smile Designers"
            if getattr(self.session, 'city_just_changed', False):
                self.session.city_just_changed = False
                next_step_instruction = (
                    f"STEP 4 (DOCTOR SELECTION FOR NEW CITY {ct}): The patient changed their city to {ct}. "
                    f"Their previous doctor was voided. In {ct}, our certified smile designers are: {docs_str}. "
                    f"Inform the patient in {user_lang} of these available certified doctors in {ct} and ask which doctor they would like to consult with: "
                    f"'You selected {ct}. In {ct}, our certified doctors are {docs_str}. Which doctor would you like to consult with?' "
                    f"('તમે {ct} પસંદ કર્યું છે. {ct}માં આપણા સર્ટિફાઇડ ડૉક્ટર્સ {docs_str} છે. તમે કયા ડૉક્ટર સાથે કન્સલ્ટ કરવા માંગો છો?'). "
                    f"(CRITICAL: NEVER auto-assign a doctor and NEVER skip this step!)."
                )
            elif pending_doc:
                next_step_instruction = f"STEP 4 (DOCTOR CONFIRMATION): The user mentioned doctor candidate {pending_doc}. Confirm the doctor in {user_lang}: 'Are you talking about {pending_doc} in {ct}?'"
            else:
                next_step_instruction = (
                    f"STEP 4 (DOCTOR SELECTION): In {ct}, our certified smile designers are: {docs_str}. "
                    f"Ask the patient which doctor they want to consult with in {ct}: 'In {ct}, we have {docs_str}. Which doctor would you like to consult with?' "
                    f"(CRITICAL: NEVER auto-assign a doctor and NEVER skip this step!)."
                )
        elif not ph or asking_field == "phone":
            next_step_instruction = (
                f"STEP 5 (MOBILE NUMBER): Doctor {dr} in {ct} is selected. Ask for their 10-digit mobile phone number in {user_lang}: "
                f"'Sure! Could you please provide your 10-digit mobile phone number?' ('ચોક્કસ! તમારો નવો 10 અંકનો મોબાઇલ નંબર કયો છે?'). "
                f"Do NOT re-recite the review summary until they provide the 10 digits."
            )
        else:
            display_name = f"{fn} {ln}".strip() if (ln and ln != "-" and ln.lower() != fn.lower()) else (self.session.user_name or fn or "Patient")
            is_update_prompt = getattr(self.session, 'slot_just_updated', False)
            self.session.slot_just_updated = False
            self.session.asking_for_field = None
            next_step_instruction = get_review_summary_prompt(user_lang, display_name, ph, ct, cn, dr, is_update=is_update_prompt)

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
            tl = text.lower().strip()
            tl = re.sub(r"[\s.,!?\\/]+$", "", tl)
            user_update_intent = any(w in tl for w in [
                "change", "update", "correct", "modify", "instead", "edit", "wrong", "mistake",
                "badlo", "badlu", "badlavu", "badlavvu", "sudharo", "sudharvu", "ferfar", "badal",
                "નથી", "ખોટું", "બદલ", "બદલો", "બદલવો", "બદલવી", "બદલવા", "બદલવું", "અપડેટ", "સુધાર", "સુધારો", "સુધારવું", "ફેરફાર", "નંબર બદલો", "નામ બદલો", "શહેર બદલો", "ડૉક્ટર બદલો", "સમસ્યા બદલો",
                "नहीं", "गलत", "बदल", "बदलो", "बदलना", "अपडेट", "सुधार", "सुधारो", "सुधारना", "नंबर बदलो", "नाम बदलो", "शहर बदलो", "डॉक्टर बदलो", "समस्या बदलो"
            ])
            # If user is asking to update or change something, it is NEVER a cancellation!
            if user_update_intent or getattr(self.session, 'slot_just_updated', False) or getattr(self.session, 'asking_for_field', None):
                return False
            # Standalone explicit cancel only
            if tl in [
                "cancel", "stop", "abort",
                "કેન્સલ", "રદ કરો", "કેન્સલ કરો",
                "कैंसिल", "रद्द કરો", "रद्द करो", "कैंसिल करो", "रद्द"
            ]:
                return True
            cancel_phrases = [
                "cancel booking", "cancel appointment", "cancel request", "cancel my booking", "cancel my appointment",
                "booking cancel", "appointment cancel", "request cancel",
                "મારી અપૉઇન્ટમેન્ટ કેન્સલ", "બુકિંગ કેન્સલ", "અપોઇન્ટમેન્ટ કેન્સલ", "રદ કરો",
                "बुकिंग कैंसिल", "अपॉइंटमेंट कैंसिल", "रद्द करें", "बुकिंग रद्द"
            ]
            if any(p in tl for p in cancel_phrases):
                if not any(neg in tl for neg in ["don't", "dont", "not", "nathi", "nahi", "nahin", "નથી", "નહીં", "नहीं", "मत"]):
                    return True
            return False

        user_txt_l = user_text.lower().strip()
        is_affirmative = is_affirmative_submit(user_text)
        is_cancel = is_cancel_submit(user_text)

        # ⚡ CRITICAL: When user says "submit" or confirms, ALWAYS extract all details directly from the last confirmation message ⚡
        confirmed_review_slots = dict(getattr(self.session, "last_review_summary_slots", {}) or {})
        last_rev_txt = getattr(self.session, "last_review_summary_text", "")
        if last_rev_txt:
            rev_s = extract_slots_from_review_summary(last_rev_txt)
            if rev_s:
                confirmed_review_slots.update(rev_s)

        if history and isinstance(history, list):
            for turn in reversed(history):
                if turn.get("role") in ["model", "assistant"]:
                    p_last = get_turn_text(turn)
                    if p_last:
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
                if matched:
                    self.session.booking_slots["doctor_name"] = matched
            except Exception:
                pass

        slots = self.session.booking_slots
        has_fn = bool(slots.get("first_name") and slots["first_name"].strip() and slots["first_name"].lower() not in ["", "none", "null", "patient", "user"])
        has_city = bool(slots.get("city") and any(c.lower() == str(slots["city"]).strip().lower() for c in CERTIFIED_CITIES))
        has_doc = bool(slots.get("doctor_name") and slots["doctor_name"].strip() and slots["doctor_name"].lower() not in ["", "none", "null", "usd certified smile designer", "doctor", "dentist", "any"])
        has_concern = bool(slots.get("message") and len(slots["message"].strip()) >= 3 and slots["message"].lower() not in ["none", "null", "dental consultation appointment request"])
        has_phone = bool(slots.get("phone") and len("".join(filter(str.isdigit, str(slots["phone"])))) == 10)

        all_slots_complete = has_fn and has_city and has_doc and has_concern and has_phone

        # If user affirms or requests submit but ANY field is missing -> NEVER submit, ask for missing field!
        if (is_affirmative or is_cancel) and not all_slots_complete and not confirmed_review_slots:
            if not has_fn:
                missing_msg = get_missing_field_message(user_lang, "name")
            elif not has_city:
                missing_msg = get_missing_field_message(user_lang, "city")
            elif not has_concern:
                missing_msg = get_missing_field_message(user_lang, "concern")
            elif not has_doc:
                missing_msg = get_missing_field_message(user_lang, "doctor", city=ct)
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

        is_user_confirming_submit = (is_affirmative or is_cancel) and (all_slots_complete or bool(confirmed_review_slots))
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
            submit_args["submission_id"] = self.session.booking_slots.get("submission_id")
            
            res = await submit_consultation_appointment(submit_args)
            if res.get("status") == "success":
                self.session.booking_slots["is_submitted"] = True
                if "details" in res and "data" in res["details"] and "id" in res["details"]["data"]:
                    if not self.session.booking_slots.get("submission_id"):
                        self.session.booking_slots["submission_id"] = res["details"]["data"]["id"]
                
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
        if getattr(self.session, 'unsupported_city', None):
            full_system_prompt += f"\n\n=========================================\nUNSUPPORTED CITY ALERT:\nThe patient mentioned being in '{self.session.unsupported_city}'. USD does NOT have Certified Smile Designers in '{self.session.unsupported_city}'. Politely inform them that we do not have a clinic there, and offer our nearest certified locations (e.g. Rajkot, Surat, Ahmedabad, Mumbai, Pune, Delhi, Bangalore) to let the patient choose!\n========================================="

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
        for key in api_keys:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:streamGenerateContent?alt=sse&key={key}"
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
                                                if is_user_confirming_submit and not self.session.booking_slots.get("is_submitted"):
                                                    submit_args = dict(self.session.booking_slots)
                                                    submit_args["is_cancel"] = is_cancel
                                                    submit_args["submission_id"] = self.session.booking_slots.get("submission_id")
                                                    res = await submit_consultation_appointment(submit_args)
                                                    if res.get("status") == "success":
                                                        self.session.booking_slots["is_submitted"] = True
                                                        if "details" in res and "data" in res["details"] and "id" in res["details"]["data"]:
                                                            if not self.session.booking_slots.get("submission_id"):
                                                                self.session.booking_slots["submission_id"] = res["details"]["data"]["id"]
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
                        print(f"[WARN] Chat stream API status {resp.status_code} with key ...{key[-6:]}, trying fallback...")
            except Exception as e:
                print(f"[WARN] Chat stream error with key ...{key[-6:]}: {e}")
            
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
        summary_slots = extract_slots_from_review_summary(clean_text or full_text)
        if summary_slots:
            print(f"[INFO] Synchronizing slots from Riya's review summary: {summary_slots}")
            self.session.last_review_summary_slots = dict(summary_slots)
            self.session.last_review_summary_text = clean_text or full_text
            for k, v in summary_slots.items():
                if v and str(v).lower() not in ["none", "null", "-", "--"]:
                    self.session.booking_slots[k] = v
            if summary_slots.get("user_name"):
                self.session.user_name = summary_slots["user_name"]
                u_p = summary_slots["user_name"].split()
                self.session.booking_slots["first_name"] = u_p[0]
                self.session.booking_slots["last_name"] = " ".join(u_p[1:]) if len(u_p) > 1 else "-"
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

                    if active_mem_lines and "SYSTEM INSTRUCTION" in user_text:
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
