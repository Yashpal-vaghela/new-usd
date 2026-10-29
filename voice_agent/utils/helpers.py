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
    # Regional residence cities (e.g. Surendranagar, Bhavnagar, Morbi, Anand, etc.)
    "સુરેન્દ્રનગર": "Surendranagar", "surendranagar": "Surendranagar", "सुरेंद्रनगर": "Surendranagar",
    "ભાવનગર": "Bhavnagar", "bhavnagar": "Bhavnagar", "भावनगर": "Bhavnagar",
    "મોરબી": "Morbi", "morbi": "Morbi", "मोरबी": "Morbi",
    "આણંદ": "Anand", "anand": "Anand", "आनंद": "Anand",
    "નડિયાદ": "Nadiad", "nadiad": "Nadiad", "नडियाद": "Nadiad",
    "મહેસાણા": "Mehsana", "mehsana": "Mehsana", "मेहसाणा": "Mehsana",
    "ગાંધીનગર": "Gandhinagar", "gandhinagar": "Gandhinagar", "गांधीनगर": "Gandhinagar",
    "નવસારી": "Navsari", "navsari": "Navsari", "नवसारी": "Navsari",
    "વલસાડ": "Valsad", "valsad": "Valsad", "वलसाड": "Valsad",
    "જૂનાગઢ": "Junagadh", "junagadh": "Junagadh", "जूनागढ़": "Junagadh",
    "પોરબંદર": "Porbandar", "porbandar": "Porbandar", "पोरबंदर": "Porbandar",
    "ભુજ": "Bhuj", "bhuj": "Bhuj", "भुज": "Bhuj",
    "ગાંધીધામ": "Gandhidham", "gandhidham": "Gandhidham", "गांधीधाम": "Gandhidham",
    "પાટણ": "Patan", "patan": "Patan", "पाटन": "Patan",
    "પાલનપુર": "Palanpur", "palanpur": "Palanpur", "पालनपुर": "Palanpur",
    "ગોધરા": "Godhra", "godhra": "Godhra", "गोधरा": "Godhra",
    "દાહોદ": "Dahod", "dahod": "Dahod", "दाहोद": "Dahod",
    "વાપી": "Vapi", "vapi": "Vapi", "वापी": "Vapi",
    "અંકલેશ્વર": "Ankleshwar", "ankleshwar": "Ankleshwar", "अंकलेश्वर": "Ankleshwar",
    "બોટાદ": "Botad", "botad": "Botad", "बोटाद": "Botad",
    "અમરેલી": "Amreli", "amreli": "Amreli", "अमरेली": "Amreli",
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
    "malda": "Malda", "मालदा": "Malda", "মালদা": "Malda",
    "jaipur": "Jaipur", "जयपुर": "Jaipur", "જયપુર": "Jaipur",
    "lucknow": "Lucknow", "लखनऊ": "Lucknow", "લખનૌ": "Lucknow",
    "kanpur": "Kanpur", "कानपुर": "Kanpur", "કાનપુર": "Kanpur",
    "nagpur": "Nagpur", "नागपुर": "Nagpur", "નાગપુર": "Nagpur",
    "nashik": "Nashik", "नासिक": "Nashik", "નાશિક": "Nashik",
    "bhopal": "Bhopal", "भोपाल": "Bhopal", "ભોપાલ": "Bhopal",
    "patna": "Patna", "पटना": "Patna", "પટના": "Patna",
    "ranchi": "Ranchi", "राँची": "Ranchi", "રાંચી": "Ranchi",
    "chandigarh": "Chandigarh", "चंडीगढ़": "Chandigarh", "ચંદીગઢ": "Chandigarh",
    "amritsar": "Amritsar", "अमृतसर": "Amritsar", "અમૃતસર": "Amritsar",
    "ludhiana": "Ludhiana", "लुधियाना": "Ludhiana", "લુધિયાણા": "Ludhiana",
    "jodhpur": "Jodhpur", "जोधपुर": "Jodhpur", "જોધપુર": "Jodhpur",
    "udaipur": "Udaipur", "उदयपुर": "Udaipur", "ઉદયપુર": "Udaipur",
    "kolkata": "Kolkata", "calcutta": "Kolkata", "कोलकाता": "Kolkata", "કોલકાતા": "Kolkata", "কলকাতা": "Kolkata"
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

PLACEHOLDER_PHONES = {"9876543210", "1234567890", "0123456789", "9999999999", "9000000000"}

def is_valid_indian_mobile(value) -> bool:
    """Exactly 10 digits starting with 6-9 (Indian mobile numbering) and not a prompt/example placeholder."""
    digits = "".join(filter(str.isdigit, str(value or "")))
    return len(digits) == 10 and digits[0] in "6789" and digits not in PLACEHOLDER_PHONES

def get_review_summary_problem(slots: dict):
    """Returns the first field that makes a review summary unsubmittable, or None when every required field is valid."""
    slots = slots or {}
    phone_digits = "".join(filter(str.isdigit, str(slots.get("phone") or "")))
    if not phone_digits:
        return "phone_missing"
    if not is_valid_indian_mobile(phone_digits):
        return "phone_invalid"
    name = str(slots.get("user_name") or slots.get("first_name") or "").strip()
    if len(name) < 2 or name.lower() in ["none", "null", "patient", "user", "-"]:
        return "name"
    if len("".join(filter(str.isdigit, str(slots.get("pincode") or "")))) != 6:
        return "pincode"
    city = str(slots.get("city") or "").strip()
    if len(city) < 2 or city.lower() in ["none", "null", "india", "-"]:
        return "city"
    concern = str(slots.get("user_concern") or slots.get("message") or "").strip()
    if len(concern) < 2 or concern.lower() in ["none", "null", "-"]:
        return "concern"
    return None

def is_submit_review_summary(text: str) -> bool:
    if not text:
        return False
    t_lower = text.lower()
    has_submit_or_cancel = any(w in t_lower for w in [
        'submit', 'cancel', 'સબમિટ', 'सबमिट', 'કેન્સલ', 'રદ', 'રદ્દ', 'रद्द', 'कॅन्सल', 'বাতিল',
        'ரத்து', 'రద్దు', 'ರದ್ದು', 'റദ്ദാക്കുക', 'ਰੱਦ', 'ବାତିଲ'
    ])
    has_review_labels = bool(re.search(r'(?:નામ|नाम|नाव|নাম|பெயர்|పేరు|ಹೆಸರು|പേര്|ਨਾਮ|name|શહેર|शहर|नगर|நகரம்|നഗരം|city|સમસ્યા|समस्या|प्रச்சனை|సమస్య|പ്രശ്നം|ਸਮੱਸਿਆ|ସମସ୍ୟା|problem|concern|ફોન|फोन|फ़ोन|தொலைபேசி|ఫోన్|ಫೋನ್|ഫോൺ|ਫ਼ੋਨ|ଫୋନ୍|phone|ડૉક્ટર|ડોક્ટર|डॉक्टर|மருத்துவர்|డాక్టర్|ವೈದ್ಯರು|ഡോക്ടർ|ਡਾਕਟਰ|ଡାକ୍ତର|doctor)\s*:', text, re.IGNORECASE))
    if not (has_submit_or_cancel and has_review_labels):
        return False
    return True

def sanitize_doctor_names_outside_submit(text: str) -> str:
    """Preserves doctor names so spoken names are never masked or cut from transcription."""
    return text

def clean_assistant_text(input_text=""):
    text = str(input_text or "")
    text = re.sub(r"\[(hi|bn|ta|te|mr|gu|kn|ml|pa|or|en)-IN\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<!--[\s\S]*?-->", "", text)
    text = re.sub(r"\d{1,2}:\d{2}(:\d{2})?(\.\d+)?\s*-->\s*\d{1,2}:\d{2}(:\d{2})?", "", text)
    text = re.sub(r"\b\d{1,2}:\d{2}(:\d{2})?\b", "", text)

    # 🚨 STRICT MEDICAL DISCLAIMER SCRUBBER (Gujarati, Hindi, English)
    disclaimer_patterns = [
        # Gujarati
        r"(?:અમે|હું)\s+તમને\s+કોઈ\s*(?:પણ\s*)?તબીબી\s+સલાહ\s+કે\s+નિદાન\s+આપતા\s+નથી\s*[.,!।]*(?:\s*કૃપા\s+કરીને\s+કોઈ\s+મદદ\s+માટે\s+ડૉક્ટરને\s+મળો\s*[.,!।]*)?",
        r"કૃપા\s+કરીને\s+કોઈ\s+મદદ\s+માટે\s+ડૉક્ટરને\s+મળો\s*[.,!।]?",
        r"[^.,!?।\n]*તબીબી\s+સલાહ[^.,!?।\n]*[.,!?।]*",
        r"[^.,!?।\n]*તબીબી\s+નિદાન[^.,!?।\n]*[.,!?।]*",
        # Hindi
        r"(?:हम|मैं)\s+(?:आपको\s+)?कोई\s*(?:भी\s*)?(?:चिकित્सीय|चिकित्सीय|मेडिकल)\s+सलाह\s+या\s+निदान\s+नहीं\s+(?:देते|दे\s+रहे\s+हैं|दे\s+रहे\s+हैં)\s*[.,!।]*(?:\s*कृपया\s+(?:किसी\s+सहायता\s+के\s+लिए\s+)?डॉक्टर\s+से\s+(?:मिलें|संपर्क\s+करें)\s*[.,!।]*)?",
        r"[^.,!?।\n]*(?:चिकित્सीय|चिकित्सीय|मेडिकल|डॉक्टरी)\s+सलाह[^.,!?।\n]*[.,!?।]*",
        r"[^.,!?।\n]*कृपया\s+(?:किसी\s+सहायता\s+के\s+लिए\s+)?डॉक्टर\s+से\s+(?:मिलें|संपर्क\s+करें)[^.,!?।\n]*[.,!?।]*",
        # English
        r"(?:We|I)\s+(?:do\s+not|don't)\s+provide\s+(?:any\s+)?medical\s+advice\s+or\s+diagnosis\s*[.,!]*(?:\s*Please\s+consult\s+a\s+(?:qualified\s+)?(?:doctor|dentist)\s*(?:for\s+diagnosis)?[.,!]*)?",
        r"[^.!?\n]*(?:not\s+provide|do\s+not\s+give)\s+(?:any\s+)?medical\s+advice[^.!?\n]*[.!?]*",
        r"[^.!?\n]*Please\s+consult\s+a\s+(?:qualified\s+)?(?:doctor|dentist)\s+(?:for\s+(?:any\s+)?medical\s+advice|for\s+diagnosis)[^.!?\n]*[.!?]*"
    ]
    for pat in disclaimer_patterns:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)

    # 🚨 FIXED ENGLISH TERMINOLOGY ENFORCEMENT:
    # 1. Laboratory: Replace 'prayogshala' (પ્રયોગશાળા / प्रयोगशाला) with 'Laboratory'
    text = re.sub(r'(?<![a-zA-Z0-9])(?:પ્રયોગશાળા|प्रयोगशाला)(?![a-zA-Z0-9])', 'Laboratory', text)
    # 2. Smile: Replace 'smit' (સ્મિત) or 'muskaan' (મુસ્કાન / मुस्कान) with 'Smile' (preserving when part of name key)
    def _rep_smile_term(m):
        prefix = m.group(1) or ""
        if any(p in prefix.lower() for p in ["નામ", "नाम", "name", "naam"]):
            return m.group(0)
        return prefix + "Smile"
    text = re.sub(r'(?:((?:નામ|नाम|Name|Naam)\s*:\s*))?\b(?:સ્મિત|મુસ્કાન|मुस्कान)\b', _rep_smile_term, text)

    text = re.sub(r"\s+", " ", text)
    text = sanitize_doctor_names_outside_submit(text)
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
    key_patterns = r"(?:નામ|नाम|नाव|নাম|பெயர்|పేరు|ಹೆಸರು|പേര്|ਨਾਮ|name|full name|ફોન|फ़ोन|फोन|फोन नंबर|phone|mobile|શહેર|शहर|நகரம்|city|location|પિનકોડ|पिनकोड|पिन कोड|pincode|pin code|pin|postal code|zip|સમસ્યા|સમસ્યાં|समस्या|பிரச்சனை|concern|issue|problem|ડૉક્ટર|ડોક્ટર|डॉक्टर|மருத்துவர்|doctor|dentist)\s*:"
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

        # A1. PINCODE (Pincode key or 6-digit postal code)
        if any(w in k_clean or w in k_trans for w in ["pincode", "pinkod", "pinkode", "pin code", "pin", "postal", "zip", "પિનકોડ", "પિન", "पिनकोड", "पिन"]):
            pin_digits = "".join(filter(str.isdigit, raw_v))
            if len(pin_digits) == 6:
                extracted["pincode"] = pin_digits
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

            # Explicitly reject placeholder phrases and ceramist mentions
            placeholder_doc_phrases = [
                "हमारे डॉक्टर", "અમારા ડૉક્ટર", "our doctor", "doctor in", "ડોક્ટર છે", "डॉक्टर हैं",
                "select doctor", "choose doctor", "કોઈ પણ", "कोई भी", "not selected", "pending",
                "ceramist", "सिरामिस्ट", "સેરેમિસ્ટ", "haresh savani", "हरेश सवाणी", "હરેશ સવાણી",
                "પસંદ કરેલ નથી", "અમારી ટીમ માર્ગદર્શન આપશે", "ચયનિત નહીં", "चयनित नहीं", "मार्गदर्शन करेगी",
                "our team will guide you", "guide you", "not chosen", "unassigned"
            ]
            raw_v_lower = raw_v.lower()
            is_placeholder = any(p in raw_v_lower for p in placeholder_doc_phrases)

            if doc_found and not is_placeholder:
                extracted["doctor_name"] = doc_found
            elif is_placeholder:
                extracted["doctor_name"] = ""
            elif len(raw_v) >= 3 and raw_v.lower() not in ["none", "null", "-", "--"]:
                # Only accept if it actually matches a known doctor in ALL_CERTIFIED_DOCTORS_LIST
                matched = None
                for d in ALL_CERTIFIED_DOCTORS_LIST:
                    if d.lower() in raw_v_lower or raw_v_lower in d.lower():
                        matched = d
                        break
                if matched:
                    extracted["doctor_name"] = matched
                else:
                    extracted["doctor_name"] = ""
            else:
                extracted["doctor_name"] = ""
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

    if not extracted.get("pincode"):
        m_pin = re.search(r"\b([1-9]\d{5})\b", text)
        if m_pin and m_pin.group(1) != extracted.get("phone", "")[:6] and m_pin.group(1) != extracted.get("phone", "")[-6:]:
            extracted["pincode"] = m_pin.group(1)

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

    # Enforce Doctor-City consistency & validity (preserve certified doctors for travel bookings):
    if extracted.get("doctor_name"):
        if extracted["doctor_name"] not in ALL_CERTIFIED_DOCTORS_LIST and extracted["doctor_name"] not in DOCTOR_HOME_CITIES:
            extracted.pop("doctor_name", None)
        elif extracted.get("city") and extracted["doctor_name"] in DOCTOR_HOME_CITIES:
            doc_city = DOCTOR_HOME_CITIES.get(extracted["doctor_name"])
            if doc_city and doc_city.lower() != extracted["city"].lower():
                # Travel booking: doctor's home city is clinic_city
                extracted["clinic_city"] = doc_city

    return extracted


def _levenshtein_distance(s1: str, s2: str) -> int:
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    return dp[m][n]


def is_cancel_submit(text: str, session=None) -> bool:
    """Ultra-robust typo-tolerant and multilingual cancellation detector for chat and voice mode."""
    if not text:
        return False

    tl = text.lower().strip()
    tl = re.sub(r"[\s.,!?\\/]+$", "", tl)

    # If user is actively typing an edit request without saying cancel, skip
    update_words = ["change", "update", "badal", "badlo", "sudharo", "ferfar", "બદલો", "સુધારો", "અપડેટ", "ફેરફાર", "बदलो", "अपडेट", "सुधारो"]
    # Only treat as update if cancel is not also explicitly mentioned
    has_explicit_cancel_word = any(cw in tl for cw in ["cancel", "cancle", "cansal", "કેન્સલ", "રદ", "રદ્દ", "कैंसिल", "कैंसल", "रद्द"])
    if not has_explicit_cancel_word and any(w in tl for w in update_words):
        return False

    # Check if negated (e.g. "don't cancel", "cancel nathi", "cancel nahi")
    negation_patterns = [
        r"\bdon'?t\s+cancel\b", r"\bdont\s+cancel\b", r"\bnot\s+cancel\b", r"\bno\s+cancel\b",
        r"\bcancel\s+nathi\b", r"\bcancel\s+nahi\b", r"\bcancel\s+nahin\b", r"\bcancel\s+mat\b",
        r"\bcancle\s+mat\b", r"\bcancsal\s+mat\b", r"\bcencil\s+mat\b",
        r"કેન્સલ\s+નથી", r"કેન્સલ\s+નહીં", r"રદ\s+નથી", r"રદ્દ\s+નથી",
        r"कैंसिल\s+नहीं", r"कैंसिल\s+मत", r"रद्द\s+नहीं", r"रद्द\s+मत", r"कैंसल\s+नहीं", r"कैंसल\s+मत"
    ]
    if any(re.search(pat, tl) for pat in negation_patterns):
        return False

    # Comprehensive cancellation keywords and typos
    cancel_keywords = [
        # English exact & common typos
        "cancel", "abort", "stop booking", "stop appointment", "drop booking", "cancel booking", "cancel appointment", "drop appointment",
        "cancsal", "cencil", "cancle", "cansal", "cansel", "cancl", "cancil", "cencel", "cencle", "cencal",
        "kancel", "kancle", "kansal", "kansel", "kencil", "cacel", "cncel", "cncil", "cncl", "canel",
        "cancal", "camcel", "cnacel", "cancelling", "canceld", "cancled", "cancelled", "cancelation",
        "cancellation", "censal", "censel", "cancell", "cencill", "cancsl", "cancsel", "cancles",
        "cancels", "cancele", "canclled", "cancield", "cancellled", "kensil", "kensal", "kencl",
        "kensel", "kancil", "kencle", "kencal", "cancul", "cencul", "cansul", "kensul", "cance",
        "casel", "canxcel", "canxel", "cenceld", "kanseld", "cencild", "kancelled", "cancledd", "cancelld",
        # Gujarati
        "કેન્સલ", "રદ", "રદ્દ", "રદ્દ્", "કેન્સલ કરો", "રદ કરો", "રદ્દ કરો", "કેન્સલ કરવી", "કેન્સલ કરવું",
        "રદ કરવી", "રદ કરવું", "કેન્સલ કરી દો", "કેન્સલ કરી દ્યો", "કેન્સલ કરી નાખો", "કેન્સલ કરજો",
        "નથી કરવું", "નથી જોઈતી", "નથી જોતી", "નથી જોઈતું", "ના કરો", "ના કરશો",
        # Hindi
        "कैंसिल", "कैंसल", "रद्द", "रद", "कैंसिल करो", "कैंसल करो", "रद्द करो", "रद करो",
        "कैंसिल कर दो", "कैंसल कर दो", "रद्द कर दीजिए", "कैंसल कर दीजिए", "कैंसिल करना", "कैंसल करना", "रद्द करना",
        "कैंसिल करना है", "कैंसल करना है", "रद्द करना है", "रद करना है", "कैंसिल कीजिये", "कैंसल कीजिये", "रद्द कीजिये",
        "नहीं करना", "नहीं चाहिए", "मत करो",
        # Marathi
        "रद्द करा", "कॅन्सल करा", "कॅन्सल", "नको",
        # Bengali
        "বাতিল করুন", "বাতিল", "বাতিল করো", "বাতিল করে দিন",
        # Tamil
        "ரத்து செய்", "ரத்து செய்யவும்", "ரத்து",
        # Telugu
        "రద్దు చేయండి", "రద్దు",
        # Kannada
        "ರದ್ದುಮಾಡಿ", "ರದ್ದು",
        # Malayalam
        "റദ്ദാക്കുക", "റദ്ദാക്കൂ",
        # Punjabi
        "ਰੱਦ ਕਰੋ", "ਰੱਦ",
        # Odia
        "ବାତିଲ କରନ୍ତୁ", "ବାତିଲ",
        # Hinglish & Gujarati phonetic combos
        "cancel karvi", "cancel karvu", "cancel karo", "cancel kar do", "cancel kardo", "cancel karna",
        "cancle karvi", "cancle karvu", "cancle karo", "cancle kar do", "cancle kardo", "cancle karna",
        "cansal karvi", "cansal karvu", "cansal karo", "cansal kar do", "cansal kardo", "cansal karna",
        "cancsal karvi", "cancsal karvu", "cancsal karo", "cancsal kar do", "cancsal kardo", "cancsal karna",
        "cencil karvi", "cencil karvu", "cencil karo", "cencil kar do", "cencil kardo", "cencil karna",
        "kancel karvi", "kancel karvu", "kancel karo", "kancel kar do", "kancel kardo", "kancel karna",
        "cancil karvi", "cancil karvu", "cancil karo", "cancil kar do", "cancil kardo", "cancil karna",
        "cencel karvi", "cencel karvu", "cencel karo", "cencel kar do", "cencel kardo", "cencel karna",
         "cancel kari nakho", "cancel kari dyo", "cancel kari do",
        "cancel kri naakho", "cancel kri nakho", "cancel kri dyo", "cancel kri do",
        "cancsal kari nakho", "cancsal kari dyo", "cancsal kari do",
        "cencil kari nakho", "cencil kari dyo", "cencil kari do",
        "cancle kari nakho", "cancle kari dyo", "cancle kari do",
        "cancle kri naakho", "cancle kri nakho", "cansal kri naakho", "cancsal kri naakho",
        "appointment cancel kri naakho", "appointment cancel kari naakho",
        "nathi karvu", "nahi karvana", "nahi karwana", "drop karo", "drop kar do", "drop kardo",
        "please cancel", "cancel please", "cancel appointment", "cancel booking", "cancel request",
        "cancsal booking", "cencil booking", "cancle booking", "cancsal appointment", "cencil appointment"
    ]

    if any(kw in tl for kw in cancel_keywords):
        return True

    # Fuzzy word match for English typos of cancel (e.g. edit distance <= 2)
    words = re.findall(r"[a-z]+", tl)
    for w in words:
        if 4 <= len(w) <= 10:
            if (w.startswith("c") or w.startswith("k") or w.startswith("s")):
                if (
                    _levenshtein_distance(w, "cancel") <= 2
                    or _levenshtein_distance(w, "cancle") <= 2
                    or _levenshtein_distance(w, "cancsal") <= 2
                    or _levenshtein_distance(w, "cencil") <= 2
                    or _levenshtein_distance(w, "cansal") <= 2
                ):
                    return True

    # Contextual decline detection: if consultation/booking is in progress and user says 'no', 'nahi', 'nathi', 'reva do'
    if session:
        slots = getattr(session, "booking_slots", {}) or {}
        asking_f = getattr(session, "asking_for_field", None)
        is_flow_active = bool(
            slots.get("pincode") or slots.get("city") or slots.get("doctor_name") or
            asking_f in ["doctor_selection", "doctor", "phone", "review_summary", "city_confirmation"] or
            getattr(session, "recommended_dentists_spoken", False) or
            getattr(session, "doctor_guidance_asked", False) or
            getattr(session, "consultation_agreed", False)
        )
        if is_flow_active:
            # Check if user is merely doing a city correction ("no, I live in Mumbai")
            has_city_correction = asking_f == "city_confirmation" and any(
                c.lower() in tl for c in ["ahmedabad", "surat", "vadodara", "rajkot", "mumbai", "pune", "delhi", "bhavnagar"]
            )
            if not has_city_correction:
                decline_terms = [
                    "no", "nah", "nope", "na", "naa", "nahi", "nahin", "nathi",
                    "nahi chahiye", "nathi joie", "nathi joitu", "nathi karvu", "nahi karna",
                    "reva do", "rehvado", "reva dyo", "chhod do", "rehva do", "mat karo", "na karsho",
                    "no thanks", "no thank you", "not interested", "dont want", "don't want",
                    "dont book", "don't book", "no appointment", "stop booking", "reva de"
                ]
                if tl in decline_terms or any(tl == dt or tl.startswith(dt + " ") or tl.endswith(" " + dt) for dt in decline_terms):
                    return True

    return False


def is_explicit_submit_command(text: str) -> bool:
    """Ultra-robust typo-tolerant explicit submission command detector."""
    if not text:
        return False
    tl = text.lower().strip()
    tl = re.sub(r"[\s.,!?\\/]+$", "", tl)
    
    explicit_submit_words = [
        # English exact & typos
        "submit", "summit", "submitt", "samit", "sabmit", "sbmit", "submet", "submti", "submiit", "submeet", "submite", "sommeil", "sommet", "soit", "somet", "sammit", "somite", "submarino",
        "confirm", "cnfirm", "confrm", "conferm", "kanfirm", "comfirm", "confiram", "proceed", "proseed", "proced",
        # Gujarati
        "સબમિટ", "સબમિટ કરો", "સબમિટ કરી દો", "સબમિટ કરી દ્યો", "સબમિટ કરજો", "કન્ફર્મ", "કન્ફર્મ કરો", "કરી દો", "કરી દ્યો", "હા કરી દો", "હા કરી દ્યો",
        # Hindi
        "सबमिट", "सबमिट करो", "सबमिट कर दीजिए", "सबमिट कर दो", "कन्फर्म", "कन्फर्म करो", "सबमिट करा", "हो सबमिट करा", "कर दो", "कर दीजिए", "हाँ कर दो", "हाँ कर दीजिए",
        # Bengali, Tamil, Telugu, Kannada, Malayalam, Punjabi, Odia
        "সাবমিট", "সাবমিট করুন", "சமர்ப்பிக்கவும்", "சப்மிட்",
        "సమర్పించండి", "సబ్మిట్", "ಸಲ್ಲಿಸಿ", "ಸಬ್ಮಿಟ್", "സമർപ്പിക്കുക", "സബ്മിറ്റ്",
        "ਦਰਜ ਕਰੋ", "ਸਬਮਿਟ", "ଦାଖଲ କରନ୍ତୁ", "ସବମିଟ୍",
        # Hinglish combos
        "submit karo", "submit kar do", "submit kardo", "submit kari dyo", "submit kari do", "submit madi",
        "submit pannunga", "submit cheyandi", "submit koro", "submit karantu",
        "submitt karo", "submitt kar do", "summit karo", "summit kar do", "samit karo",
        "confirm karo", "confirm kar do", "confirm kardo", "confirm kari do", "confirm kari dyo",
        "book my appointment", "mari booking submit", "meri booking submit", "submit my appointment"
    ]
    if tl in explicit_submit_words:
        return True
    for phrase in explicit_submit_words:
        if phrase in tl:
            return True

    # Fuzzy check
    words = re.findall(r"[a-z]+", tl)
    for w in words:
        if 4 <= len(w) <= 8 and _levenshtein_distance(w, "submit") <= 2:
            return True
        if 5 <= len(w) <= 9 and _levenshtein_distance(w, "confirm") <= 2:
            return True

    return False


def is_affirmative_submit(text: str) -> bool:
    """Detects affirmative agreement to submit details across 11 languages."""
    if not text:
        return False
    tl = text.lower().strip()
    tl = re.sub(r"[\s.,!?\\/]+$", "", tl)
    if is_explicit_submit_command(text):
        return True
    affirmative_list = [
        "yes", "yea", "yep", "yeah", "ok", "okay", "sure", "done", "please do", "confirm", "proceed",
        "હા", "હા કરી દો", "હા કરી દ્યો", "ચોક્કસ", "ભલે", "ઠીક છે", "હાજી", "કરી દ્યો", "કરી દો", "સબમિટ", "હા સબમિટ", "સબમિટ કરો", "સબમિટ કરી દો", "સબમિટ કરી દ્યો",
        "हाँ", "हाँ कर दो", "कर दो", "अवश्य", "ज़रूर", "सबमिट", "हाँ सबमिट", "सबमिट करो", "सबमिट कर दीजिए", "सबमिट कर दो", "हाँजी",
        "हो", "हो करा", "करा", "नक्की", "चालेल", "सबमिट", "सबमिट करा", "हो सबमिट करा",
        "হ্যাঁ", "হ্যাঁ করুন", "করুন", "অবশ্যই", "সাবমিট", "সাবমিট করুন", "হ্যাঁ সাবমিট করুন",
        "ஆம்", "சரி", "கண்டிப்பாக", "சமர்ப்பிக்கவும்", "சப்மிட்", "சப்மிட் பண்ணுங்க", "ஆம் சப்மிட் பண்ணுங்க",
        "అవును", "సరే", "తప్పకుండా", "సమర్పించండి", "సబ్మిట్", "సబ్మిట్ చేయండి", "అవును సబ్మిట్ చేయండి",
        "ಹೌದು", "ಸರಿ", "ಖಂಡಿತ", "ಸಲ್ಲಿಸಿ", "ಸಬ್ಮಿಟ್", "ಸಬ್ಮಿಟ್ ಮಾಡಿ", "ಹೌದು ಸಬ್ಮಿಟ್ ಮಾಡಿ",
        "അതെ", "ശരി", "തീർച്ചയായും", "സമർപ്പിക്കുക", "സബ്മിറ്റ്", "സബ്മിറ്റ് ചെയ്യുക", "അതെ സബ്മിറ്റ് ചെയ്യുക",
        "ਹਾਂ", "ਹਾਂਜੀ", "ਜ਼ਰੂਰ", "ਦਰਜ ਕਰੋ", "ਸਬਮਿਟ", "ਸਬਮਿਟ ਕਰੋ", "ਹਾਂ ਸਬਮਿਟ ਕਰੋ",
        "ହଁ", "ହଁ କରନ୍ତୁ", "ନିଶ୍ଚୟ", "ଦାଖଲ କରନ୍ତୁ", "ସବମିଟ୍", "ସବମିଟ୍ କରନ୍ତୁ", "ହଁ ସବମିଟ୍ କରନ୍ତୁ",
        "haan", "ha", "haa", "ha ji", "haan ji", "kar do", "kardo", "kari do", "kari dyo", "kar dyo", "haa kari dyo",
        "yes submit", "chalega", "thik chhe", "theek hai", "bhaley", "chokkas", "zarur", "zaroor", "sommeil", "sommet", "soit", "somet", "sammit", "submarino"
    ]
    edit_words = [
        "change", "update", "edit", "instead", "no my", "no, my", "spelling", "mistake", "wrong", "incorrect",
        "ખોટું", "ખોટો", "ખોટી", "ખોટા", "ખોટો છે", "ખોટી છે", "ખોટું છે", "બદલ", "બદલો", "બદલવો", "બદલવી", "બદલવું", "બદલવા",
        "સુધાર", "સુધારો", "સુધારવો", "સુધારવી", "સુધારવું", "ફેરફાર", "ચેન્જ", "ચેંજ", "ચેંન્જ", "અપડેટ",
        "गलत", "बदल", "बदलो", "बदलना", "बदल दीजिए", "बदल दो", "सुधार", "सुधारो", "सुधारना", "खो तो", "खोटो", "खोता", "खोती", "अपडेट",
        "badlo", "badlav", "sudharo", "badal", "galat", "khoto", "khotu", "ferfar", "change karo", "update karo", "badli do", "badli dyo"
    ]
    if any(ew in tl for ew in edit_words):
        return False

    if tl in affirmative_list:
        return True
    for phrase in [
        "submit", "confirm", "book", "kari dyo", "kari do", "kar do", "kardo", "submitt",
        "કરી દ્યો", "કરી દો", "સબમિટ", "કર દો", "कर दो", "सबमिट", "करा", "করুন", "சமர்ப்பிக்கவும்", "సమర్పించండి", "ಸಲ್ಲಿಸಿ", "സമർപ്പിക്കുക", "ਦਰਜ ਕਰੋ", "ଦାଖଲ କରନ୍ତୁ",
        "mari booking", "મારી બુકિંગ", "મારી અપૉઇન્ટમેન્ટ", "मेरी बुकिंग"
    ]:
        if phrase in tl:
            return True
    return False


def is_cancel_response_text(text: str) -> bool:
    """Checks if a generated response from Gemini indicates appointment cancellation."""
    if not text:
        return False
    tl = text.lower()
    cancel_response_phrases = [
        # English
        "appointment request has been cancelled", "appointment has been cancelled",
        "appointment request has been canceled", "appointment has been canceled",
        "appointment request is cancelled", "appointment request is canceled",
        "booking has been cancelled", "booking has been canceled",
        "has been cancelled", "has been canceled", "is cancelled", "is canceled",
        "cancelled successfully", "canceled successfully", "successfully cancelled", "successfully canceled",
        # Gujarati
        "કેન્સલ કરી દેવામાં આવી છે", "કેન્સલ કરી દેવામાં આવી", "કેન્સલ કરી દેવાઈ છે", "કેન્સલ કરી દેવાઇ છે",
        "કેન્સલ કરવામાં આવી છે", "કેન્સલ કરવામાં આવી", "કેન્સલ થઈ ગઈ છે", "કેન્સલ થઈ ગયું છે",
        "કેન્સલ કરી દીધી છે", "કેન્સલ કરી દીધું છે", "સફળતાપૂર્વક કેન્સલ",
        "રદ કરી દેવામાં આવી છે", "રદ કરી દેવામાં આવી", "રદ કરી દેવાઈ છે", "રદ કરવામાં આવી છે", "રદ કરવામાં આવી",
        "રદ થઈ ગઈ છે", "રદ થઈ ગયું છે", "રદ કરી દીધી છે", "સફળતાપૂર્વક રદ",
        "રદ્દ કરી દેવામાં આવી છે", "રદ્દ કરી દેવામાં આવી", "રદ્દ કરી દેવાઈ છે", "રદ્દ કરવામાં આવી છે", "રદ્દ કરવામાં આવી",
        "રદ્દ થઈ ગઈ છે", "રદ્દ થઈ ગયું છે", "રદ્દ કરી દીધી છે", "સફળતાપૂર્વક રદ્દ",
        "તમારી અપૉઇન્ટમેન્ટ રિક્વેસ્ટ કેન્સલ", "અપૉઇન્ટમેન્ટ રિક્વેસ્ટ કેન્સલ", "અપૉઇન્ટમેન્ટ કેન્સલ",
        # Hindi
        "आपका अपॉइंटमेंट अनुरोध रद्द कर दिया गया है", "अपॉइंटमेंट अनुरोध रद्द कर दिया गया है",
        "अपॉइंटमेंट रद्द कर दिया गया", "अपॉइंटमेंट रद्द कर दी गई", "रद्द कर दिया गया है", "रद्द कर दी गई है",
        "रद्द कर दिया गया", "रद्द कर दी गई", "रद्द हो गया है", "रद्द हो गई है",
        "कैंसिल कर दिया गया है", "कैंसिल कर दी गई है", "कैंसिल कर दिया गया", "कैंसिल कर दी गई",
        "कैंसल कर दिया गया है", "कैंसल कर दी गई है", "कैंसल कर दिया गया", "कैंसल कर दी गई",
        "कैंसिल हो गई है", "कैंसल हो गई है", "सफलतापूर्वक कैंसिल", "सफलतापूर्वक रद्द",
        # Marathi
        "तुमची अपॉइंटमेंट विनंती रद्द करण्यात आली आहे", "रद्द करण्यात आले आहे", "कॅन्सल करण्यात आले आहे",
        "कॅन्सल करण्यात आली आहे", "रद्द करण्यात आली आहे",
        # Bengali
        "আপনার অ্যাপয়েন্টমেন্টের অনুরোধ বাতিল করা হয়েছে", "বাতিল করা হয়েছে", "সফলভাবে বাতিল",
        # Tamil
        "உங்கள் அப்பாயின்ட்மென்ட் கோரிக்கை ரத்து செய்யப்பட்டுள்ளது", "ரத்து செய்யப்பட்டுள்ளது",
        # Telugu
        "మీ అపాయింట్‌మెంట్ అభ్యర్థన రద్దు చేయబడింది", "రద్దు చేయబడింది",
        # Kannada
        "ನಿಮ್ಮ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ವಿನಂತಿಯನ್ನು ರದ್ದುಗೊಳಿಸಲಾಗಿದೆ", "ರದ್ದುಗೊಳಿಸಲಾಗಿದೆ",
        # Malayalam
        "നിങ്ങളുടെ അപ്പോയിന്റ്മെന്റ് അഭ്യർത്ഥന റദ്ദാക്കപ്പെട്ടു", "റദ്ദാക്കപ്പെട്ടു",
        # Punjabi
        "ਤੁਹਾਡੀ ਮੁਲਾਕਾਤ ਦੀ ਬੇਨਤੀ ਰੱਦ ਕਰ ਦਿੱਤੀ ਗਈ ਹੈ", "ਰੱਦ ਕਰ ਦਿੱਤੀ ਗਈ ਹੈ", "ਰੱਦ ਕਰ ਦਿੱਤਾ ਗਿਆ ਹੈ",
        # Odia
        "ଆପଣଙ୍କର ଆପଏଣ୍ଟମେଣ୍ଟ ଅନୁରୋଧ ବାତିଲ କରାଯାଇଛି", "ବାତିଲ କରାଯାଇଛି"
    ]
    return any(p in tl for p in cancel_response_phrases)


def is_submit_response_text(text: str) -> bool:
    """Checks if a generated response from Gemini indicates appointment submission."""
    if not text:
        return False
    tl = text.lower()
    submit_response_phrases = [
        "appointment request submitted successfully", "appointment request has been submitted",
        "appointment has been submitted", "successfully submitted",
        "સફળતાપૂર્વક સબમિટ", "સબમિટ થઈ ગઈ છે", "સબમિટ કરવામાં આવી",
        "सफलतापूर्वक सबमिट", "सबमिट हो गई", "सबमिट कर दिया गया",
        "यशस्वीरित्या सबमिट", "সফলভাবে সাবমিট", "வெற்றிகரமாக சமர்ப்பிக்கப்பட்டது",
        "విజయవంతంగా సమర్పించబడింది", "ಯಶಸ್ವಿಯಾಗಿ ಸಲ್ಲಿಸಲಾಗಿದೆ",
        "വിജയകരമായി സമർപ്പിച്ചു", "ਸਫਲਤਾਪੂਰਵਕ ਦਰਜ", "ସଫଳତାର ସହିତ ଦାଖଲ"
    ]
    return any(p in tl for p in submit_response_phrases)
