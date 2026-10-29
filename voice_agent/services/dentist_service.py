import re
import time
import requests
import asyncio
from typing import List, Dict, Optional, Tuple

_PINCODE_DENTISTS_CACHE: Dict[str, Tuple[float, List[Dict]]] = {}
CACHE_TTL = 300  # 5 minutes cache

PINCODE_API_URL = "https://ultimatesmiledesign.com/api/dentists-list/pincode/"

def fetch_dentists_by_pincode_sync(pincode: str) -> List[Dict]:
    """
    Fetches dentists from API sorted by proximity to the provided pincode.
    Uses in-memory caching for performance and minimal latency.
    """
    clean_pin = re.sub(r"\D", "", str(pincode or "")).strip()
    now = time.time()

    if clean_pin in _PINCODE_DENTISTS_CACHE:
        cached_time, cached_data = _PINCODE_DENTISTS_CACHE[clean_pin]
        if now - cached_time < CACHE_TTL:
            print(f"[API-CACHE] ⚡ Serving {len(cached_data)} dentists near pincode '{clean_pin}' from cache: {[d.get('name') for d in cached_data[:3]]}")
            return cached_data

    params = {"pincode": clean_pin} if (clean_pin and len(clean_pin) == 6) else {}
    print(f"[API-FETCH] 🌐 Fetching dentists from API: {PINCODE_API_URL}?pincode={clean_pin}")
    try:
        resp = requests.get(PINCODE_API_URL, params=params, timeout=5.0)
        if resp.status_code == 200:
            data_json = resp.json()
            dentists = data_json.get("data", [])
            if isinstance(dentists, list) and dentists:
                print(f"[API-SUCCESS] ✅ Successfully fetched {len(dentists)} dentists near pincode '{clean_pin}': {[d.get('name') for d in dentists[:3]]}")
                _PINCODE_DENTISTS_CACHE[clean_pin] = (now, dentists)
                return dentists
    except Exception as e:
        print(f"[WARN] Error fetching dentists from API for pincode '{clean_pin}': {e}")

    # Fallback to cached data if available
    if clean_pin in _PINCODE_DENTISTS_CACHE:
        return _PINCODE_DENTISTS_CACHE[clean_pin][1]

    if "" in _PINCODE_DENTISTS_CACHE:
        return _PINCODE_DENTISTS_CACHE[""][1]

    # Robust offline fallback to prevent bot silence or empty recommendation
    try:
        from voice_agent.utils.helpers import ALL_CERTIFIED_DOCTORS_LIST, DOCTOR_HOME_CITIES
        p_prefix = clean_pin[:2] if clean_pin else ""
        east_prioritized = ["Dr. A K Saha", "Dr. Adil Lyngdoh", "Dr. Reuben Joseph"]
        if p_prefix in ["70", "71", "72", "73", "74", "75", "76", "77", "78", "79"]:
            doc_order = east_prioritized + [d for d in ALL_CERTIFIED_DOCTORS_LIST if d not in east_prioritized]
        else:
            doc_order = ALL_CERTIFIED_DOCTORS_LIST

        fallback_dentists = []
        for doc_name in doc_order:
            home_c = DOCTOR_HOME_CITIES.get(doc_name, "")
            fallback_dentists.append({
                "name": doc_name,
                "clinic_name": f"{home_c} Smile Center" if home_c else "USD Certified Clinic",
                "address": home_c or "India",
                "pincode": clean_pin or "380001",
                "bio": f"USD Certified Smile Designer in {home_c}" if home_c else "USD Certified Smile Designer"
            })
        return fallback_dentists
    except Exception as e:
        print(f"[WARN] Error constructing fallback dentists: {e}")
        return []


async def fetch_dentists_by_pincode_async(pincode: str) -> List[Dict]:
    """Async wrapper around sync fetcher to run non-blocking in event loop."""
    return await asyncio.to_thread(fetch_dentists_by_pincode_sync, pincode)


def get_nearest_dentists(pincode: str, offset: int = 0, limit: int = 3) -> Tuple[List[Dict], int, int]:
    """
    Returns (dentist_slice, total_count, next_offset).
    Always returns up to `limit` dentists starting at `offset`.
    Ensures that if a patient's city has fewer than `limit` dentists (e.g. Vadodara has only 2:
    Dr. Khushbu Patel and Dr. Kaveena Parikh), the remaining dentists are fetched from the nearest
    adjacent certified hub city (e.g. Ahmedabad along the arrival route from patient's pincode).
    """
    clean_pin = re.sub(r"\D", "", str(pincode or "")).strip()
    all_dentists = fetch_dentists_by_pincode_sync(pincode)
    total = len(all_dentists)
    if total == 0:
        return [], 0, 0

    # ⚡ Check if pincode belongs to Vadodara (390xxx / 391xxx) or city with < limit dentists
    is_vadodara = bool(clean_pin.startswith("390") or clean_pin.startswith("391"))
    if not is_vadodara and clean_pin:
        try:
            from voice_agent.services.dentist_service import get_pincode_city_info
            c_info = get_pincode_city_info(clean_pin)
            if c_info and "vadodara" in (c_info.get("canonical_city") or "").lower():
                is_vadodara = True
        except Exception:
            pass

    if is_vadodara:
        # Vadodara has 2 certified dentists: Dr. Khushbu Patel and Dr. Kaveena Parikh
        # Order them by proximity to the specific Vadodara pincode
        vad_docs = [d for d in all_dentists if get_doctor_city(d) == "Vadodara"]
        known_vad_names = [d.get("name") for d in vad_docs]
        if "Dr. Khushbu Patel" not in known_vad_names:
            vad_docs.append({
                "name": "Dr. Khushbu Patel",
                "clinic_name": "Advanced Dentistry",
                "address": "114-D, Ananta Trendz, Gotri - Laxmipura Rd, near Narayan Garden Road, Laxmipura, Gotri, Vadodara, Gujarat 390023",
                "pincode": "390023",
                "city": "Vadodara",
                "bio": "USD Certified Smile Designer in Vadodara"
            })
        if "Dr. Kaveena Parikh" not in known_vad_names:
            vad_docs.append({
                "name": "Dr. Kaveena Parikh",
                "clinic_name": "Xperteeth dental",
                "address": "Aasopalav one west, 220, Sevasi, Vadodara, Gujarat 391101",
                "pincode": "391101",
                "city": "Vadodara",
                "bio": "USD Certified Smile Designer in Vadodara"
            })

        # 3rd doctor MUST be fetched from the nearest city which is Ahmedabad,
        # closest to the patient's entry route into Ahmedabad from Vadodara (Expressway NE-1 -> CTM / 382481 / 382350)
        ahmd_dentists = fetch_dentists_by_pincode_sync("382481")
        ahmd_docs = [d for d in ahmd_dentists if get_doctor_city(d) == "Ahmedabad"]
        if not ahmd_docs:
            ahmd_docs = [
                {
                    "name": "Dr. Jigar P. Thakkar",
                    "clinic_name": "Dantam Microscopic Dental Clinic",
                    "address": "2nd Floor, Silver harmony 2, 233-A, opp. ICB FLORA, Gota, Ahmedabad, Gujarat 382481",
                    "pincode": "382481",
                    "city": "Ahmedabad",
                    "bio": "USD Certified Smile Designer in Ahmedabad"
                },
                {
                    "name": "Dr. Rakesh Patel",
                    "clinic_name": "Magic Smile Dental Clinic",
                    "address": "1, VAIBHAV PARK, nr. Uma School Road, Nikol - Naroda Rd, Ahmedabad, Gujarat 382350",
                    "pincode": "382350",
                    "city": "Ahmedabad",
                    "bio": "USD Certified Smile Designer in Ahmedabad"
                }
            ]

        # Combine: Vadodara doctors first, then Ahmedabad entry-route doctors, then other nearby
        seen_names = set()
        prioritized = []
        for d in vad_docs + ahmd_docs + all_dentists:
            nm = d.get("name")
            if nm and nm not in seen_names:
                seen_names.add(nm)
                prioritized.append(d)
        all_dentists = prioritized
        total = len(all_dentists)

    # Ensure offset is valid
    start = offset % total if offset >= total else offset
    end = start + limit
    dentists_slice = all_dentists[start:end]

    # If we reached the end, next offset wraps around
    next_offset = end if end < total else 0
    return dentists_slice, total, next_offset


async def get_nearest_dentists_async(pincode: str, offset: int = 0, limit: int = 3) -> Tuple[List[Dict], int, int]:
    """Async wrapper for get_nearest_dentists."""
    return await asyncio.to_thread(get_nearest_dentists, pincode, offset, limit)


def format_dentist_recommendation_prompt(dentists: List[Dict], pincode: str, offset: int = 0) -> str:
    """
    Formats the list of 3 nearest dentists for injection into Gemini Live session memory.
    """
    if not dentists:
        return f"- Pincode {pincode}: No specific dentists fetched yet."

    lines = [f"[NEAREST USD CERTIFIED SMILE DESIGNERS FOR PINCODE {pincode} (Batch starting at #{offset + 1})]:"]
    for i, d in enumerate(dentists, start=offset + 1):
        name = d.get("name", "Dr. USD Specialist")
        clinic = d.get("clinic_name", "USD Certified Smile Center")
        pin = d.get("pincode", "")
        doc_c = get_doctor_city(d) or d.get("city", "")
        city_info = f", Clinic City: {doc_c}" if doc_c else ""
        lines.append(f"  {i}. {name} ({clinic}{city_info}, Area Pincode: {pin})")

    lines.append(
        "INSTRUCTION: Speak ALL 3 nearest doctor names aloud to the patient! "
        "CRITICAL: If the patient's city has fewer than 3 doctors (e.g. Vadodara has 2 doctors: Dr. Khushbu Patel and Dr. Kaveena Parikh), the 3rd doctor is from nearby adjacent city (e.g. Dr. Jigar P. Thakkar or Dr. Rakesh Patel in nearby Ahmedabad). "
        "You MUST speak ALL 3 doctor names aloud! E.g. in Vadodara Dr. Khushbu Patel and Dr. Kaveena Parikh, and in nearby Ahmedabad Dr. Jigar P. Thakkar. "
        "NEVER speak only 2 doctor names! ALWAYS present all 3 doctor names to the patient! "
        "Ask if they would like to select one of these doctors, or should our team guide them."
    )
    return "\n".join(lines)


def infer_city_from_dentists(dentists: List[Dict]) -> Optional[str]:
    """
    Detects the city from the nearest dentists' addresses or bios.
    """
    from voice_agent.services.appointment_service import CERTIFIED_CITIES
    for d in (dentists or []):
        text_block = f"{d.get('address', '')} {d.get('bio', '')} {d.get('clinic_name', '')}"
        for c in CERTIFIED_CITIES:
            if re.search(r'\b' + re.escape(c) + r'\b', text_block, re.IGNORECASE):
                return c
    return None


def get_doctor_city(doctor_dict_or_name: any) -> str:
    """
    Returns the home/clinic city of the certified doctor.
    Checks DOCTOR_HOME_CITIES first, then falls back to clinic address.
    """
    try:
        from voice_agent.utils.helpers import DOCTOR_HOME_CITIES
        from voice_agent.services.appointment_service import CERTIFIED_CITIES
    except Exception:
        DOCTOR_HOME_CITIES = {}
        CERTIFIED_CITIES = []

    if isinstance(doctor_dict_or_name, dict):
        name = doctor_dict_or_name.get("name", "")
        addr = f"{doctor_dict_or_name.get('address', '')} {doctor_dict_or_name.get('clinic_name', '')}"
    else:
        name = str(doctor_dict_or_name or "")
        addr = ""

    clean_n = re.sub(r"^dr\.?\s*", "", name, flags=re.IGNORECASE).strip().lower()
    for doc_k, city in DOCTOR_HOME_CITIES.items():
        doc_clean = re.sub(r"^dr\.?\s*", "", doc_k, flags=re.IGNORECASE).strip().lower()
        if doc_clean == clean_n or doc_clean in clean_n or clean_n in doc_clean:
            return city

    if addr:
        for c in CERTIFIED_CITIES:
            if re.search(r'\b' + re.escape(c) + r'\b', addr, re.IGNORECASE):
                return c
    return ""


def format_dentists_speech_text(
    dentists: List[Dict], 
    pincode: str, 
    lang: str = "en", 
    is_more: bool = False, 
    is_update: bool = False,
    user_city: Optional[str] = None
) -> str:
    """
    Creates a natural conversational string listing the 3 dentists in the requested language.
    Supports is_update=True when the patient changed their pincode.
    Explicitly mentions the doctor's city if nearest doctors are located in a different city.
    """
    if not dentists:
        return ""

    doc_names = [d.get("name", "").strip() for d in dentists if d.get("name")]
    if not doc_names:
        return ""

    lang = (lang or "en").lower()

    # Determine doctor cities and check if any doctor is outside user's city
    doc_cities = [get_doctor_city(d) for d in dentists]
    u_city_norm = (user_city or "").strip().lower()

    # Special natural formatting if user's city has 2 doctors and 1 is from nearby hub city (e.g. Vadodara + Ahmedabad)
    if u_city_norm and not is_more:
        local_docs = [d for d in dentists if (get_doctor_city(d) or "").lower() == u_city_norm]
        other_docs = [d for d in dentists if (get_doctor_city(d) or "").lower() != u_city_norm]
        if len(local_docs) == 2 and len(other_docs) == 1:
            doc1 = local_docs[0].get("name", "").strip()
            doc2 = local_docs[1].get("name", "").strip()
            doc3 = other_docs[0].get("name", "").strip()
            other_c = get_doctor_city(other_docs[0]) or other_docs[0].get("city", "Ahmedabad")
            u_c_disp = user_city.title() if user_city else "Vadodara"
            lk_pref = (lang[:2] if lang else "en").lower()
            if lk_pref == "gu":
                prefix = f"તમારા અપડેટ કરેલા પિનકોડ {pincode} મુજબ" if is_update else f"તમારા પિનકોડ {pincode} મુજબ"
                return (
                    f"{prefix}, {u_c_disp}માં અમારા સૌથી નજીકના USD સર્ટિફાઇડ સ્માઇલ ડિઝાઇનર્સ છે {doc1} અને {doc2}, "
                    f"તેમજ નજીકના {other_c}માં {doc3}. "
                    f"શું તમે આમાંથી કોઈ ડૉક્ટર પસંદ કરવા માંગો છો, કે પછી અમારી ટીમ માર્ગદર્શન આપે?"
                )
            elif lk_pref == "hi":
                prefix = f"आपके अपडेट किए गए पिनकोड {pincode} के अनुसार" if is_update else f"आपके पिनकोड {pincode} के अनुसार"
                return (
                    f"{prefix}, {u_c_disp} में हमारे सबसे नजदीकी USD सर्टिफाइड स्માઈલ डिज़ाइनर हैं {doc1} और {doc2}, "
                    f"तथा नजदीकी {other_c} में {doc3}। "
                    f"क्या आप इनमें से किसी डॉक्टर का चयन करना चाहेंगे, या हमारी टीम मार्गदर्शन करे?"
                )
            else:
                prefix = f"Based on your updated pincode {pincode}" if is_update else f"Based on your pincode {pincode}"
                return (
                    f"{prefix}, our nearest USD Certified Smile Designers in {u_c_disp} are {doc1} and {doc2}, "
                    f"and in nearby {other_c} is {doc3}. "
                    f"Would you like to select one of these doctors, or should our team guide you?"
                )

    # Are all doctors in user's city?
    all_in_user_city = bool(u_city_norm and all(c.lower() == u_city_norm for c in doc_cities if c))

    # If doctors are outside user's city or in different cities, format doctor with their city
    include_cities = not all_in_user_city
    unique_cities = list(dict.fromkeys(c for c in doc_cities if c))
    single_nearby_city = unique_cities[0] if len(unique_cities) == 1 else None

    if include_cities and single_nearby_city:
        # All doctors belong to the same nearby hub city (e.g. Rajkot when user is in Bhavnagar)
        # Mention the city upfront in the near phrase rather than repeating per doctor
        doc_pairs_en = doc_names
        doc_pairs_gu = doc_names
        doc_pairs_hi = doc_names
    elif include_cities:
        doc_pairs_en = [f"{d.get('name', '').strip()}" + (f" in {get_doctor_city(d)}" if get_doctor_city(d) else "") for d in dentists]
        doc_pairs_gu = [(f"{get_doctor_city(d)}માં " if get_doctor_city(d) else "") + f"{d.get('name', '').strip()}" for d in dentists]
        doc_pairs_hi = [(f"{get_doctor_city(d)} में " if get_doctor_city(d) else "") + f"{d.get('name', '').strip()}" for d in dentists]
    else:
        doc_pairs_en = doc_names
        doc_pairs_gu = doc_names
        doc_pairs_hi = doc_names

    if len(doc_pairs_en) == 1:
        names_str_en = doc_pairs_en[0]
        names_str_gu = doc_pairs_gu[0]
        names_str_hi = doc_pairs_hi[0]
    elif len(doc_pairs_en) == 2:
        names_str_en = f"{doc_pairs_en[0]} and {doc_pairs_en[1]}"
        names_str_gu = f"{doc_pairs_gu[0]} અને {doc_pairs_gu[1]}"
        names_str_hi = f"{doc_pairs_hi[0]} और {doc_pairs_hi[1]}"
    else:
        names_str_en = f"{doc_pairs_en[0]}, {doc_pairs_en[1]}, and {doc_pairs_en[2]}"
        names_str_gu = f"{doc_pairs_gu[0]}, {doc_pairs_gu[1]} અને {doc_pairs_gu[2]}"
        names_str_hi = f"{doc_pairs_hi[0]}, {doc_pairs_hi[1]} और {doc_pairs_hi[2]}"

    # Language-specific conjunctions and formats
    lk = (lang[:2] if lang else "en").lower()

    if lk == "gu":
        if is_more:
            return (
                f"તમારા વિસ્તાર નજીકના અન્ય ઉપલબ્ધ ડૉક્ટર્સ આ મુજબ છે: {names_str_gu}. "
                f"શું તમે આમાંથી કોઈ ડૉક્ટર પસંદ કરવા માંગો છો, અથવા બીજા વિકલ્પો જોવા માંગો છો?"
            )
        prefix = f"તમારા અપડેટ કરેલા પિનકોડ {pincode} મુજબ" if is_update else f"તમારા પિનકોડ {pincode} મુજબ"
        if include_cities and single_nearby_city:
            near_phrase = f"નજીકના {single_nearby_city}માં અમારા સૌથી નજીકના USD સર્ટિફાઇડ સ્માઇલ ડિઝાઇનર્સ છે"
        elif include_cities:
            near_phrase = "નજીકના શહેરોમાં તમારા સૌથી નજીકના USD સર્ટિફાઇડ સ્માઇલ ડિઝાઇનર્સ છે"
        else:
            near_phrase = "તમારા સૌથી નજીકના 3 USD સર્ટિફાઇડ સ્માઇલ ડિઝાઇનર્સ છે"
        return (
            f"{prefix}, {near_phrase}: {names_str_gu}. "
            f"શું તમે આમાંથી કોઈ ડૉક્ટર સાથે કન્સલ્ટ કરવા માંગો છો, અથવા બીજા વિકલ્પો સાંભળવા માંગો છો?"
        )

    if lk == "hi":
        if is_more:
            return (
                f"आपके क्षेत्र के निकटतम अन्य उपलब्ध डॉक्टर हैं: {names_str_hi}। "
                f"क्या आप इनमें से किसी डॉक्टर का चयन करना चाहेंगे, या और विकल्प देखना चाहेंगे?"
            )
        prefix = f"आपके अपडेट किए गए पिनकोड {pincode} के अनुसार" if is_update else f"आपके पिनकोड {pincode} के अनुसार"
        if include_cities and single_nearby_city:
            near_phrase = f"नजदीकी {single_nearby_city} में हमारे 3 सबसे नजदीकी USD सर्टिफाइड स्माइल डिज़ाइनर हैं"
        elif include_cities:
            near_phrase = "निकटवर्ती शहरों में आपके सबसे नजदीकी USD सर्टिफाइड स्माइल डिज़ाइनर हैं"
        else:
            near_phrase = "आपके निकटतम 3 USD सर्टिफाइड स्माइल डिज़ाइनर हैं"
        return (
            f"{prefix}, {near_phrase}: {names_str_hi}। "
            f"क्या आप इनमें से किसी डॉक्टर से कंसल्ट करना चाहेंगे, या अन्य विकल्प देखना चाहेंगे?"
        )

    if lk == "mr":
        if is_more:
            return (
                f"तुमच्या परिसरातील पुढील उपलब्ध USD प्रमाणित स्माइल डिझायनर्स आहेत: {names_str_en}. "
                f"तुम्ही यापैकी एकाची निवड करू इच्छिता, किंवा इतर पर्याय पाहू इच्छिता?"
            )
        prefix = f"तुमच्या अपडेट केलेल्या पिनकोड {pincode} नुसार" if is_update else f"तुमच्या पिनकोड {pincode} नुसार"
        if include_cities and single_nearby_city:
            near_phrase = f"जवळच्या {single_nearby_city} मधील आमचे 3 सर्वात जवळचे USD प्रमाणित स्माइल डिझायनर्स आहेत"
        elif include_cities:
            near_phrase = "जवळच्या शहरांमधील आमचे USD प्रमाणित स्माइल डिझायनर्स आहेत"
        else:
            near_phrase = "आमचे 3 सर्वात जवळचे USD प्रमाणित स्माइल डिझायनर्स आहेत"
        return (
            f"{prefix}, {near_phrase}: {names_str_en}। "
            f"तुम्ही यापैकी कोणत्याही डॉक्टरांची निवड करू इच्छिता, किंवा इतर पर्याय पाहू इच्छिता?"
        )

    if lk == "bn":
        if is_more:
            return (
                f"আপনার এলাকার নিকটবর্তী পরবর্তী উপলব্ধ USD সার্টিফাইড স্মাইল ডিজাইনার হলেন: {names_str_en}। "
                f"আপনি কি এদের মধ্যে কাউকে নির্বাচন করতে চান, নাকি আরও বিকল্প দেখতে চান?"
            )
        prefix = f"আপনার আপডেট করা পিনকোড {pincode} অনুসারে" if is_update else f"আপনার পিনকোড {pincode} অনুসারে"
        if include_cities and single_nearby_city:
            near_phrase = f"কাছের {single_nearby_city} তে আমাদের ৩ জন নিকটতম USD সার্টিফাইড স্মাইল ডিজাইনার হলেন"
        elif include_cities:
            near_phrase = "নিকটবর্তী শহরে অবস্থিত আমাদের USD সার্টিফাইড স্মাইল ডিজাইনার হলেন"
        else:
            near_phrase = "আমাদের ৩ জন নিকটতম USD সার্টিফাইড স্মাইল ডিজাইনার হলেন"
        return (
            f"{prefix}, {near_phrase}: {names_str_en}। "
            f"আপনি কি এই ডাক্তারদের মধ্যে কাউকে নির্বাচন করতে চান, নাকি অন্য বিকল্প দেখতে চান?"
        )

    if lk == "ta":
        if is_more:
            return (
                f"உங்கள் பகுதிக்கு அருகிலுள்ள அடுத்த USD சான்றளிக்கப்பட்ட ஸ்மைல் டிசைனர்கள்: {names_str_en}. "
                f"இவர்களில் ஒருவரைத் தேர்ந்தெடுக்க விரும்புகிறீர்களா, அல்லது பிற விருப்பங்களைப் பார்க்க விரும்புகிறீர்களா?"
            )
        prefix = f"உங்கள் புதுப்பிக்கப்பட்ட பின்கோட் {pincode} படி" if is_update else f"உங்கள் பின்கோட் {pincode} படி"
        if include_cities and single_nearby_city:
            near_phrase = f"அருகிலுள்ள {single_nearby_city} யில் உள்ள எங்கள் 3 அருகிலுள்ள USD சான்றளிக்கப்பட்ட ஸ்மைல் டிசைனர்கள்"
        elif include_cities:
            near_phrase = "அருகிலுள்ள நகரங்களில் உள்ள எங்கள் USD சான்றளிக்கப்பட்ட ஸ்மைல் டிசைனர்கள்"
        else:
            near_phrase = "எங்கள் 3 அருகிலுள்ள USD சான்றளிக்கப்பட்ட ஸ்மைல் டிசைனர்கள்"
        return (
            f"{prefix}, {near_phrase}: {names_str_en}. "
            f"இவர்களில் ஒரு மருத்துவரைத் தேர்ந்தெடுக்க விரும்புகிறீர்களா, அல்லது பிற விருப்பங்களைப் பார்க்க விரும்புகிறீர்களா?"
        )

    if lk == "te":
        if is_more:
            return (
                f"మీ ప్రాంత సమీపంలో అందుబాటులో ఉన్న తదుపరి USD సర్టిఫైడ్ స్మైల్ డిజైనర్లు: {names_str_en}. "
                f"మీరు వీరిలో ఒకరిని ఎంచుకోవాలనుకుంటున్నారా, లేదా మరిన్ని ఎంపికలు చూడాలనుకుంటున్నారా?"
            )
        prefix = f"మీ అప్‌డేట్ చేసిన పిన్‌కోడ్ {pincode} ప్రకారం" if is_update else f"మీ పిన్‌కోడ్ {pincode} ప్రకారం"
        if include_cities and single_nearby_city:
            near_phrase = f"సమీపంలోని {single_nearby_city} లో మా 3 సమీప USD సర్టిఫైడ్ స్మైల్ డిజైనర్లు"
        elif include_cities:
            near_phrase = "సమీప నగరాల్లోని మా USD సర్టిఫైడ్ స్మైల్ డిజైనర్లు"
        else:
            near_phrase = "మా 3 సమీప USD సర్టిఫైడ్ స్మైల్ డిజైనర్లు"
        return (
            f"{prefix}, {near_phrase}: {names_str_en}. "
            f"మీరు వీరిలో ఒకరిని ఎంచుకోవాలనుకుంటున్నారా, లేదా ఇతర ఎంపికలను చూడాలనుకుంటున్నారా?"
        )

    if lk == "kn":
        if is_more:
            return (
                f"ನಿಮ್ಮ ಪ್ರದೇಶದ ಹತ್ತಿರ ಲಭ್ಯವಿರುವ ಮುಂದಿನ USD ಪ್ರಮಾಣೀಕೃತ ಸ್ಮೈಲ್ ಡಿಸೈನರ್‌ಗಳು: {names_str_en}. "
                f"ನೀವು ಇವರಲ್ಲಿ ಒಬ್ಬರನ್ನು ಆಯ್ಕೆ ಮಾಡಲು ಬಯಸುತ್ತೀರಾ, ಅಥವಾ ಹೆಚ್ಚಿನ ಆಯ್ಕೆಗಳನ್ನು ನೋಡಲು ಬಯಸುತ್ತೀರಾ?"
            )
        prefix = f"ನಿಮ್ಮ ನವೀಕರಿಸಿದ ಪಿನ್‌ಕೋಡ್ {pincode} ಪ್ರಕಾರ" if is_update else f"ನಿಮ್ಮ ಪಿನ್‌ಕೋಡ್ {pincode} ಪ್ರಕಾರ"
        if include_cities and single_nearby_city:
            near_phrase = f"ಹತ್ತಿರದ {single_nearby_city} ನಲ್ಲಿ ನಮ್ಮ 3 ಹತ್ತಿರದ USD ಪ್ರಮಾಣೀಕೃತ ಸ್ಮೈಲ್ ಡಿಸೈನರ್‌ಗಳು"
        elif include_cities:
            near_phrase = "ಹತ್ತಿರದ ನಗರಗಳಲ್ಲಿರುವ ನಮ್ಮ USD ಪ್ರಮಾಣೀಕೃತ ಸ್ಮೈಲ್ ಡಿಸೈನರ್‌ಗಳು"
        else:
            near_phrase = "ನಮ್ಮ 3 ಹತ್ತಿರದ USD ಪ್ರಮಾಣೀಕೃತ ಸ್ಮೈಲ್ ಡಿಸೈನರ್‌ಗಳು"
        return (
            f"{prefix}, {near_phrase}: {names_str_en}. "
            f"ನೀವು ಇವರಲ್ಲಿ ಒಬ್ಬರನ್ನು ಆಯ್ಕೆ ಮಾಡಲು ಬಯಸುತ್ತೀರಾ, ಅಥವಾ ಇತರ ಆಯ್ಕೆಗಳನ್ನು ನೋಡಲು ಬಯಸುತ್ತೀರಾ?"
        )

    if lk == "ml":
        if is_more:
            return (
                f"നിങ്ങളുടെ പ്രദേശത്തിന് അടുത്തുള്ള അടുത്ത ലഭ്യമായ USD സർട്ടിഫൈഡ് സ്മൈൽ ഡിസൈനർമാർ: {names_str_en}. "
                f"ഇവരിൽ ഒരാളെ തിരഞ്ഞെടുക്കാൻ ആഗ്രഹിക്കുന്നുണ്ടോ, അതോ കൂടുതൽ ഓപ്ഷനുകൾ കാണാൻ ആഗ്രഹിക്കുന്നുണ്ടോ?"
            )
        prefix = f"നിങ്ങളുടെ അപ്ഡേറ്റ് ചെയ്ത പിൻകോഡ് {pincode} അനുസരിച്ച്" if is_update else f"നിങ്ങളുടെ പിൻകോഡ് {pincode} അനുസരിച്ച്"
        if include_cities and single_nearby_city:
            near_phrase = f"അടുത്തുള്ള {single_nearby_city} യിൽ ഞങ്ങളുടെ ഏറ്റവും അടുത്തുള്ള 3 USD സർട്ടിഫൈഡ് സ്മൈൽ ഡിസൈനർമാർ"
        elif include_cities:
            near_phrase = "സമീപ നഗരങ്ങളിലുള്ള ഞങ്ങളുടെ USD സർട്ടിഫൈഡ് സ്മൈൽ ഡിസൈനർമാർ"
        else:
            near_phrase = "ഞങ്ങളുടെ ഏറ്റവും അടുത്തുള്ള 3 USD സർട്ടിഫൈഡ് സ്മൈൽ ഡിസൈനർമാർ"
        return (
            f"{prefix}, {near_phrase}: {names_str_en}. "
            f"ഇവരിൽ ഒരാളെ തിരഞ്ഞെടുക്കാൻ ആഗ്രഹിക്കുന്നുണ്ടോ, അതോ മറ്റ് ഓപ്ഷനുകൾ കാണാൻ ആഗ്രഹിക്കുന്നുണ്ടോ?"
        )

    if lk == "pa":
        if is_more:
            return (
                f"ਤੁਹਾਡੇ ਇਲਾਕੇ ਦੇ ਨੇੜੇ ਅਗਲੇ ਉਪਲਬਧ USD ਪ੍ਰਮਾਣਿਤ ਸਮਾਈਲ ਡਿਜ਼ਾਈਨਰ ਹਨ: {names_str_en}. "
                f"ਕੀ ਤੁਸੀਂ ਇਹਨਾਂ ਵਿੱਚੋਂ ਕਿਸੇ ਇੱਕ ਨੂੰ ਚੁਣਨਾ ਚਾਹੋਗੇ, ਜਾਂ ਹੋਰ ਵਿਕਲਪ ਦੇਖਣਾ ਚਾਹੋਗੇ?"
            )
        prefix = f"ਤੁਹਾਡੇ ਅਪਡੇਟ ਕੀਤੇ ਪਿਨਕੋਡ {pincode} ਅਨੁਸਾਰ" if is_update else f"ਤੁਹਾਡੇ ਪਿਨਕੋਡ {pincode} ਅਨੁਸਾਰ"
        if include_cities and single_nearby_city:
            near_phrase = f"ਨੇੜਲੇ {single_nearby_city} ਵਿੱਚ ਸਾਡੇ 3 ਸਭ ਤੋਂ ਨੇੜਲੇ USD ਪ੍ਰਮਾਣਿਤ ਸਮਾਈਲ ਡਿਜ਼ਾਈਨਰ ਹਨ"
        elif include_cities:
            near_phrase = "ਨੇੜਲੇ ਸ਼ਹਿਰਾਂ ਵਿੱਚ ਸਾਡੇ USD ਪ੍ਰਮਾਣਿਤ ਸਮਾਈਲ ਡਿਜ਼ਾਈਨਰ ਹਨ"
        else:
            near_phrase = "ਸਾਡੇ 3 ਸਭ ਤੋਂ ਨੇੜਲੇ USD ਪ੍ਰਮਾਣਿਤ ਸਮਾਈਲ ਡਿਜ਼ਾਈਨਰ ਹਨ"
        return (
            f"{prefix}, {near_phrase}: {names_str_en}. "
            f"ਕੀ ਤੁਸੀਂ ਇਹਨਾਂ ਵਿੱਚੋਂ ਕਿਸੇ ਡਾਕਟਰ ਦੀ ਚੋਣ ਕਰਨਾ ਚਾਹੋਗੇ, ਜਾਂ ਹੋਰ ਵਿਕਲਪ ਦੇਖਣਾ ਚਾਹੋਗੇ?"
        )

    if lk == "or":
        if is_more:
            return (
                f"ଆପଣଙ୍କ ଅଞ୍ଚଳ ନିକଟରେ ଉପଲବ୍ଧ ପରବର୍ତ୍ତୀ USD ସାର୍ଟିଫାଏଡ୍ ସ୍ମାଇଲ୍ ଡିଜାଇନର୍ ହେଲେ: {names_str_en}। "
                f"ଆପଣ ଏମାନଙ୍କ ମଧ୍ୟରୁ କାହାକୁ ଚୟନ କରିବାକୁ ଚାହାଁନ୍ତି କି, କିମ୍ବା ଅଧିକ ବିକଳ୍ପ ଦେଖିବାକୁ ଚାହାଁନ୍ତି?"
            )
        prefix = f"ଆପଣଙ୍କର ଅପଡେଟ୍ ହୋଇଥିବା ପିନକୋଡ୍ {pincode} ଅନୁଯାୟୀ" if is_update else f"ଆପଣଙ୍କର ପିନକୋଡ୍ {pincode} ଅନୁଯାୟୀ"
        if include_cities and single_nearby_city:
            near_phrase = f"ନିକଟସ୍ଥ {single_nearby_city} ରେ ଆମର ୩ ଜଣ ନିକଟତମ USD ସାର୍ଟିଫାଏଡ୍ ସ୍ମାଇଲ୍ ଡିଜାଇନର୍ ହେଲେ"
        elif include_cities:
            near_phrase = "ନିକଟବର୍ତ୍ତୀ ସହରରେ ଆମର USD ସାର୍ଟିଫାଏଡ୍ ସ୍ମାଇଲ୍ ଡିଜାଇନର୍ ହେଲେ"
        else:
            near_phrase = "ଆମର ୩ ଜଣ ନିକଟତମ USD ସାର୍ଟିଫାଏଡ୍ ସ୍ମାଇଲ୍ ଡିଜାଇନର୍ ହେଲେ"
        return (
            f"{prefix}, {near_phrase}: {names_str_en}। "
            f"ଆପଣ ଏମାନଙ୍କ ମଧ୍ୟରୁ କାହାକୁ ଚୟନ କରିବାକୁ ଚାହାଁନ୍ତି କି, କିମ୍ବା ଅନ୍ୟ ବିକଳ୍ପ ଦେଖିବାକୁ ଚାହାଁନ୍ତି?"
        )

    # English / default
    if is_more:
        return (
            f"Here are the next available USD Certified Smile Designers near your area: {names_str_en}. "
            f"Would you like to select one of these doctors, or would you like to hear more options?"
        )
    prefix = f"Based on your updated pincode {pincode}" if is_update else f"Based on your pincode {pincode}"
    if include_cities and single_nearby_city:
        near_phrase = f"our 3 nearest USD Certified Smile Designers nearby in {single_nearby_city} are"
    elif include_cities:
        near_phrase = "your nearest USD Certified Smile Designers are located in nearby cities"
    else:
        near_phrase = "your 3 nearest USD Certified Smile Designers are"
    return (
        f"{prefix}, {near_phrase}: {names_str_en}. "
        f"Would you like to consult with one of these doctors, or would you like to hear other options?"
    )


# -------------------------------------------------------------------------
# ⚡ CITY & PINCODE LOCK VALIDATION ENGINE ⚡
# -------------------------------------------------------------------------
# -------------------------------------------------------------------------
# ⚡ DYNAMIC POSTAL PIN CODE API LOOKUP ENGINE ⚡
# Official India Postal PIN Code API:
# 1. GET https://api.postalpincode.in/pincode/{PINCODE}
# 2. GET https://api.postalpincode.in/postoffice/{POSTOFFICEBRANCHNAME}
# -------------------------------------------------------------------------

_POSTAL_LOCATION_CACHE: Dict[str, Dict] = {}
_POSTOFFICE_BRANCH_CACHE: Dict[str, List[Dict]] = {}


def get_location_for_pincode(pincode: str) -> Optional[Dict]:
    """
    Returns district, state, and aliases for a 6-digit Indian pincode using official Postal PIN Code API:
    GET https://api.postalpincode.in/pincode/{PINCODE}
    Results are cached in memory for fast zero-latency access on subsequent calls.
    """
    clean_pin = re.sub(r"\D", "", str(pincode or "")).strip()
    if len(clean_pin) != 6:
        return None

    if clean_pin in _POSTAL_LOCATION_CACHE:
        return _POSTAL_LOCATION_CACHE[clean_pin]

    try:
        from urllib.parse import quote
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(f"https://api.postalpincode.in/pincode/{clean_pin}", headers=headers, timeout=3.5)
        if resp.status_code == 200:
            data = resp.json()
            if data and isinstance(data, list) and data[0].get("Status") == "Success":
                pos = data[0].get("PostOffice", [])
                if pos:
                    first_po = pos[0]
                    dist = first_po.get("District") or ""
                    state = first_po.get("State") or ""
                    div = first_po.get("Division") or ""
                    circle = first_po.get("Circle") or ""
                    region = first_po.get("Region") or ""
                    block = first_po.get("Block") or ""

                    aliases_set = set()
                    for s in [dist, div, block]:
                        if s:
                            aliases_set.add(s.lower().strip())
                    for po in pos:
                        name = po.get("Name")
                        if name:
                            aliases_set.add(name.lower().strip())
                            clean_name = re.sub(r"\b(h\.?o\.?|s\.?o\.?|b\.?o\.?|g\.?p\.?o\.?)\b", "", name, flags=re.IGNORECASE).strip()
                            if clean_name:
                                aliases_set.add(clean_name.lower())

                    res = {
                        "pincode": clean_pin,
                        "district": dist,
                        "block": block,
                        "state": state,
                        "division": div,
                        "region": region,
                        "circle": circle,
                        "post_offices": pos,
                        "aliases": list(aliases_set),
                        "source": "postal_api"
                    }
                    _POSTAL_LOCATION_CACHE[clean_pin] = res
                    return res
    except Exception as e:
        print(f"[WARN] Postal API lookup failed for {clean_pin}: {e}")

    return None


def get_postoffices_for_branch_name(branch_name: str) -> Optional[List[Dict]]:
    """
    Returns list of Post Office details searching by branch / city name:
    GET https://api.postalpincode.in/postoffice/{POSTOFFICEBRANCHNAME}
    """
    clean_branch = str(branch_name or "").strip()
    if not clean_branch:
        return None

    cache_key = clean_branch.lower()
    if cache_key in _POSTOFFICE_BRANCH_CACHE:
        return _POSTOFFICE_BRANCH_CACHE[cache_key]

    try:
        from urllib.parse import quote
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(f"https://api.postalpincode.in/postoffice/{quote(clean_branch)}", headers=headers, timeout=3.5)
        if resp.status_code == 200:
            data = resp.json()
            if data and isinstance(data, list) and data[0].get("Status") == "Success":
                pos = data[0].get("PostOffice", [])
                if pos:
                    _POSTOFFICE_BRANCH_CACHE[cache_key] = pos
                    return pos
    except Exception as e:
        print(f"[WARN] Postal Branch API lookup failed for {clean_branch}: {e}")

    return None


def get_nearest_dentists_for_travel(patient_pincode: str, patient_city: str, target_city: str) -> List[Dict]:
    """
    Returns the closest USD Certified Smile Designers in target_city ordered by proximity
    to the patient's incoming travel entry route from their residence city / pincode.
    E.g. If patient is from Bhavnagar (364001) traveling to Surat:
    The entry point into Surat is via Hazira Port (Ro-Pax) / Western Surat bypass -> Adajan (395009).
    The first reached dentists are Dr. Purvi Patel and Dr. Bharat R. Patel in Adajan (395009).
    """
    p_city_l = str(patient_city or "").strip().lower()
    p_pin = re.sub(r"\D", "", str(patient_pincode or "")).strip()
    t_city_l = str(target_city or "").strip().lower()

    # Route entry-point pincode in target city
    entry_pincode = ""

    if "surat" in t_city_l:
        # Coming from Bhavnagar / Amreli / Junagadh / Saurashtra coastal
        if (
            "bhavnagar" in p_city_l or "amreli" in p_city_l or "junagadh" in p_city_l or "ghogha" in p_city_l
            or p_pin.startswith("364") or p_pin.startswith("365") or p_pin.startswith("362")
        ):
            # Arrival via Hazira Port (Ro-Pax Ferry) or Western ring road -> Adajan
            entry_pincode = "395009"
        # Coming from Ahmedabad / Vadodara / Bharuch (NH48 North)
        elif (
            "ahmedabad" in p_city_l or "vadodara" in p_city_l or "bharuch" in p_city_l or "ankleshwar" in p_city_l
            or p_pin.startswith("380") or p_pin.startswith("382") or p_pin.startswith("390") or p_pin.startswith("392")
        ):
            # Arrival via NH48 North -> Mota Varachha / Dabholi
            entry_pincode = "394101"
        # Coming from Mumbai / Vapi / Navsari / Valsad (NH48 South)
        elif (
            "mumbai" in p_city_l or "vapi" in p_city_l or "navsari" in p_city_l or "valsad" in p_city_l
            or p_pin.startswith("400") or p_pin.startswith("396")
        ):
            # Arrival via NH48 South -> Vesu / VIP Road
            entry_pincode = "395007"
        else:
            entry_pincode = "395009"

    elif "ahmedabad" in t_city_l:
        if (
            "bhavnagar" in p_city_l or "rajkot" in p_city_l or "surendranagar" in p_city_l
            or p_pin.startswith("364") or p_pin.startswith("360") or p_pin.startswith("363")
        ):
            # Entry via Sarkhej / SG Highway / Prahlad Nagar
            entry_pincode = "380015"
        elif (
            "surat" in p_city_l or "vadodara" in p_city_l or "mumbai" in p_city_l
            or p_pin.startswith("395") or p_pin.startswith("390") or p_pin.startswith("400")
        ):
            # Entry via Expressway / CTM / Jasodanagar
            entry_pincode = "382481"
        elif (
            "gandhinagar" in p_city_l or "himatnagar" in p_city_l
            or p_pin.startswith("382") or p_pin.startswith("383")
        ):
            # Entry via Naroda / Gandhinagar highway
            entry_pincode = "382330"
        else:
            entry_pincode = "380015"

    elif "mumbai" in t_city_l:
        if (
            "surat" in p_city_l or "ahmedabad" in p_city_l or "vadodara" in p_city_l or "baroda" in p_city_l or "vapi" in p_city_l
            or p_pin.startswith("395") or p_pin.startswith("380") or p_pin.startswith("390") or p_pin.startswith("391") or p_pin.startswith("396")
        ):
            # Entry via Western Express Highway / Dahisar / Borivali / Andheri
            entry_pincode = "400053"
        elif "pune" in p_city_l or p_pin.startswith("411"):
            # Entry via Expressway / Vashi / Chembur / Dadar
            entry_pincode = "400012"
        else:
            entry_pincode = "400050"

    else:
        # Default: lookup destination city post office pincode
        pos = get_postoffices_for_branch_name(target_city)
        if pos and pos[0].get("Pincode"):
            entry_pincode = pos[0].get("Pincode")

    print(f"[TRAVEL-SEARCH] 🚗 Finding dentists in destination '{target_city}' for patient from '{patient_city}' ({patient_pincode}) using route entry pincode '{entry_pincode}'...")
    # Fetch dentists by this entry pincode
    all_dentists = fetch_dentists_by_pincode_sync(entry_pincode) if entry_pincode else []
    if not all_dentists:
        all_dentists = fetch_dentists_by_pincode_sync("")

    # Filter/prioritize dentists in the target city
    target_city_dentists = [
        d for d in all_dentists
        if (d.get("city") and t_city_l in d.get("city", "").lower()) or
           (d.get("address") and t_city_l in d.get("address", "").lower()) or
           (entry_pincode and d.get("pincode", "")[:3] == entry_pincode[:3])
    ]
    print(f"[TRAVEL-SUCCESS] 🎯 Found {len(target_city_dentists)} dentists in '{target_city}' closest to entry route: {[d.get('name') for d in target_city_dentists[:3]]}")

    if len(target_city_dentists) >= 3:
        return target_city_dentists[:3]

    # Robust verified doctor list for primary dental hubs if external API timed out or lacks local metadata
    if "mumbai" in t_city_l:
        if len(target_city_dentists) >= 3:
            return target_city_dentists[:3]
        return [
            {"name": "Dr. Nikita Motwani", "clinic_name": "Smile Designers", "pincode": "400053", "city": "Mumbai", "area": "Andheri West"},
            {"name": "Dr. Moez Khakiani", "clinic_name": "Khakiani's Dental Centre", "pincode": "400050", "city": "Mumbai", "area": "Bandra West"},
            {"name": "Dr. Vinita Tekchandani", "clinic_name": "Dentistree", "pincode": "400052", "city": "Mumbai", "area": "Khar West"},
        ]

    if "surat" in t_city_l:
        if "395009" in entry_pincode:
            return [
                {"name": "Dr. Purvi Patel", "clinic_name": "NuFace Maxillofacial & Dental Hospital", "pincode": "395009", "city": "Surat", "area": "Adajan"},
                {"name": "Dr. Bharat R. Patel", "clinic_name": "Smile Dental Clinic", "pincode": "395009", "city": "Surat", "area": "Adajan"},
                {"name": "Dr. Priyanka Kathiriya", "clinic_name": "Kathiriya Dental Care", "pincode": "395004", "city": "Surat", "area": "Dabholi"},
            ]
        elif "394101" in entry_pincode:
            return [
                {"name": "Dr. Viren K Savani", "clinic_name": "Savani Dental Care And Implant Center", "pincode": "394101", "city": "Surat", "area": "Mota Varachha"},
                {"name": "Dr. Priyanka Kathiriya", "clinic_name": "Kathiriya Dental Care", "pincode": "395004", "city": "Surat", "area": "Dabholi"},
                {"name": "Dr. Purvi Patel", "clinic_name": "NuFace Maxillofacial & Dental Hospital", "pincode": "395009", "city": "Surat", "area": "Adajan"},
            ]
        else:
            return [
                {"name": "Dr. Jay Patel", "clinic_name": "Four Seasons Dental", "pincode": "395007", "city": "Surat", "area": "Vesu"},
                {"name": "Dr. Parita Shah", "clinic_name": "Denticare Dental Care Centre", "pincode": "395007", "city": "Surat", "area": "Parle Point"},
                {"name": "Dr. Purvi Patel", "clinic_name": "NuFace Maxillofacial & Dental Hospital", "pincode": "395009", "city": "Surat", "area": "Adajan"},
            ]

    if "ahmedabad" in t_city_l:
        return [
            {"name": "Dr. Alap D Shah", "clinic_name": "IVORIES DENTAL CLINIC", "pincode": "380015", "city": "Ahmedabad", "area": "Prahlad Nagar"},
            {"name": "Dr. Neerav Jhaveri", "clinic_name": "EZ Integrated Dental Solutions", "pincode": "380015", "city": "Ahmedabad", "area": "SG Highway"},
            {"name": "Dr. Ravi Shah", "clinic_name": "Karma Dental", "pincode": "380054", "city": "Ahmedabad", "area": "Bodakdev"},
        ]

    return target_city_dentists[:3] if target_city_dentists else all_dentists[:3]


def format_travel_dentists_speech_text(
    dentists: List[Dict],
    patient_city: str,
    target_city: str,
    lang: str = "en"
) -> str:
    """
    Formats the spoken response recommending closest dentists in target_city when arriving from patient_city.
    """
    if not dentists:
        return f"We would be delighted to assist you with booking an appointment in {target_city.title()}! Our team will contact you to connect you with our certified smile designer."

    names = [d.get("name", "") for d in dentists if d.get("name")]
    lk = (lang or "en").lower()
    if lk in ["gu", "gujarati"]:
        conj = " અને "
    elif lk in ["hi", "hindi"]:
        conj = " और "
    else:
        conj = ", and "

    if len(names) >= 2:
        names_str = ", ".join(names[:-1]) + f"{conj}{names[-1]}"
    elif names:
        names_str = names[0]
    else:
        names_str = "our top certified smile designers"

    p_city_disp = patient_city.title() if patient_city else "your location"
    t_city_disp = target_city.title() if target_city else "the city"

    lk = (lang or "en").lower()
    if lk in ["gu", "gujarati"]:
        return (
            f"ચોક્કસ! તમે {p_city_disp}થી આવો છો, તેથી {t_city_disp}માં પ્રવેશતા જ સૌથી પહેલા પહોંચી શકાય તેવા "
            f"અમારા યુએસડી સર્ટિફાઇડ સ્માઇલ ડિઝાઇનર {names_str} છે. "
            f"શું તમે આમાંથી કોઈ ડૉક્ટર પસંદ કરવા માંગો છો, કે અમારી ટીમ તમને માર્ગદર્શન આપે?"
        )
    if lk in ["hi", "hindi"]:
        return (
            f"बिल्कुल! चूंकि आप {p_city_disp} से आ रहे हैं, {t_city_disp} में प्रवेश करते ही सबसे पहले पहुंचने वाले "
            f"हमारे यूएसडी सर्टिफाइड स्माइल डिज़ाइनर {names_str} हैं। "
            f"क्या आप इनमें से किसी डॉक्टर को चुनना चाहेंगे, या हमारी टीम आपका मार्गदर्शन करे?"
        )
    return (
        f"Certainly! As you are coming from {p_city_disp}, the first USD Certified Smile Designers you will reach "
        f"when arriving in {t_city_disp} are {names_str}. "
        f"Would you like to select one of these doctors, or should our team guide you?"
    )


def validate_city_pincode_match(city: str, pincode: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates if the provided city matches the pincode.
    Returns: (is_match, detected_district_or_city, error_msg)
    """
    if not city or not pincode:
        return True, None, None

    clean_pin = re.sub(r"\D", "", str(pincode or "")).strip()
    if len(clean_pin) != 6:
        return True, None, None

    loc = get_location_for_pincode(clean_pin)
    if not loc:
        # Pincode location couldn't be resolved — do not block user
        return True, None, None

    district_name = (loc.get("district") or "").lower()
    div_name = (loc.get("division") or "").lower()
    aliases = [a.lower() for a in loc.get("aliases", [])]

    # Normalize user's city
    c_norm = city.lower().strip()
    c_words = re.findall(r"[a-z]+", c_norm)

    # Check direct match with aliases or district/division
    is_match = (
        c_norm == district_name or
        c_norm == div_name or
        any(c_norm == a or (len(c_norm) >= 4 and (c_norm in a or a in c_norm)) for a in aliases)
    )
    if not is_match and c_words:
        for w in c_words:
            if len(w) >= 4 and any(w == a or w in a.split() for a in aliases):
                is_match = True
                break

    # If not matched directly, check via branch API for user's city
    if not is_match:
        branch_pos = get_postoffices_for_branch_name(city)
        if branch_pos:
            for bpo in branch_pos:
                b_dist = (bpo.get("District") or "").lower()
                b_div = (bpo.get("Division") or "").lower()
                b_pin = str(bpo.get("PINCode") or bpo.get("Pincode") or "").strip()
                # Matches if the branch has the exact same pincode, or same district/division as the pincode
                if (
                    b_pin == clean_pin
                    or (b_dist and (b_dist == district_name or b_dist in aliases))
                    or (b_div and (b_div == div_name or b_div in aliases))
                ):
                    is_match = True
                    break

    detected_display = loc.get("district", "").split("/")[0].strip() if loc.get("district") else (loc.get("state") or "")
    if is_match:
        return True, detected_display, None

    # Mismatch detected!
    error_msg = f"City '{city}' does not match pincode {clean_pin} ({detected_display} area)"
    return False, detected_display, error_msg


def format_city_pincode_mismatch_speech(city: str, pincode: str, detected_city: str, lang: str = "en") -> str:
    """
    Generates an empathetic clarification prompt when the user's city and pincode do not match.
    """
    lk = (lang[:2] if lang else "en").lower()
    city_display = city.title() if city else "your city"
    det_display = detected_city.title() if detected_city else "another"

    if lk == "gu":
        return (
            f"તમારું પસંદ કરેલું શહેર {city_display} છે, પરંતુ પિનકોડ {pincode} {det_display} વિસ્તારનો છે. "
            f"કૃપા કરીને {city_display} વિસ્તારનો સાચો 6 અંકનો પિનકોડ જણાવશો, અથવા તમારું સાચું શહેર કયું છે તે જણાવશો?"
        )
    if lk == "hi":
        return (
            f"आपका चुना हुआ शहर {city_display} है, लेकिन पिनकोड {pincode} {det_display} क्षेत्र का है। "
            f"कृपया {city_display} का सही 6 अंकों का पिनकोड बता दीजिए, या यदि आपका शहर बदला है तो बताइए?"
        )
    if lk == "mr":
        return (
            f"तुमचे निवडलेले शहर {city_display} आहे, पण पिनकोड {pincode} {det_display} भागाचा आहे. "
            f"कृपया {city_display} चा योग्य 6 अंकी पिनकोड सांगा, किंवा तुमचे शहर बदलले असल्यास सांगा?"
        )
    if lk == "bn":
        return (
            f"আপনার নির্বাচিত শহর {city_display}, কিন্তু পিনকোড {pincode} {det_display} এলাকার। "
            f"দয়া করে {city_display} এর সঠিক ৬ সংখ্যার পিনকোড বলুন, অথবা আপনার শহর পরিবর্তিত হলে জানান?"
        )
    if lk == "ta":
        return (
            f"நீங்கள் தேர்ந்தெடுத்த நகரம் {city_display}, ஆனால் பின்கோட் {pincode} {det_display} பகுதியைச் சேர்ந்தது. "
            f"தயவுசெய்து {city_display} இன் சரியான 6 இலக்க பின்கோட்டைப் பகிருங்கள், அல்லது உங்கள் நகரம் மாறியிருந்தால் தெரியப்படுத்துங்கள்?"
        )
    if lk == "te":
        return (
            f"మీరు ఎంచుకున్న నగరం {city_display}, కానీ పిన్‌కోడ్ {pincode} {det_display} ప్రాంతానికి చెందినది. "
            f"దయచేసి {city_display} యొక్క సరైన 6 అంకెల పిన్‌కోడ్‌ను తెలియజేయండి, లేదా మీ నగరం మారిందో తెలపండి?"
        )
    if lk == "kn":
        return (
            f"ನಿಮ್ಮ ಆಯ್ಕೆ ಮಾಡಿದ ನಗರ {city_display}, ಆದರೆ ಪಿನ್‌ಕೋಡ್ {pincode} {det_display} ಪ್ರದೇಶಕ್ಕೆ ಸೇರಿದೆ. "
            f"ದಯವಿಟ್ಟು {city_display} ನ ಸರಿಯಾದ 6 ಅಂಕಿಗಳ ಪಿನ್‌ಕೋಡ್ ತಿಳಿಸಿ, ಅಥವಾ ನಿಮ್ಮ ನಗರ ಬದಲಾಗಿದ್ದರೆ ತಿಳಿಸಿ?"
        )
    if lk == "ml":
        return (
            f"നിങ്ങൾ തിരഞ്ഞെടുത്ത നഗരം {city_display} ആണ്, എന്നാൽ പിൻകോഡ് {pincode} {det_display} പ്രദേശത്തിന്റേതാണ്. "
            f"ദയവായി {city_display} ന്റെ ശരിയായ 6 അക്ക പിൻകോഡ് നൽകുക, അല്ലെങ്കിൽ നഗരം മാറിയോ എന്ന് അറിയിക്കുക?"
        )
    if lk == "pa":
        return (
            f"ਤੁਹਾਡਾ ਚੁਣਿਆ ਸ਼ਹਿਰ {city_display} ਹੈ, ਪਰ ਪਿਨਕੋਡ {pincode} {det_display} ਇਲਾਕੇ ਦਾ ਹੈ। "
            f"ਕਿਰਪਾ ਕਰਕੇ {city_display} ਦਾ ਸਹੀ 6 ਅੰਕਾਂ ਦਾ ਪਿਨਕੋਡ ਦੱਸੋ, ਜਾਂ ਆਪਣਾ ਨਵਾਂ ਸ਼ਹਿਰ ਦੱਸੋ?"
        )
    if lk == "or":
        return (
            f"ଆପଣଙ୍କର ମନୋନୀତ ସହର {city_display}, କିନ୍ତୁ ପିନକୋଡ୍ {pincode} {det_display} ଅଞ୍ଚଳର। "
            f"ଦୟାକରି {city_display} ର ସଠିକ୍ ୬ ଅଙ୍କ ବିଶିଷ୍ଟ ପିନକୋଡ୍ କୁହନ୍ତୁ, କିମ୍ବା ଆପଣଙ୍କ ସହର ବଦଳିଛି କି ଜଣାନ୍ତୁ?"
        )
    return (
        f"Your selected city is {city_display}, but pincode {pincode} belongs to the {det_display} area. "
        f"Could you please share your correct 6-digit {city_display} area pincode, or let me know if your city has changed?"
    )


def format_city_updated_speech(city: str, lang: str = "en") -> str:
    """
    Generates an empathetic prompt acknowledging the patient's updated/clarified city and asking for their 6-digit area pincode.
    """
    lk = (lang[:2] if lang else "en").lower()
    city_display = city.title() if city else "your city"

    if lk == "gu":
        return (
            f"સમજી ગઈ! તમારું શહેર {city_display} નોંધાઈ ગયું છે. "
            f"{city_display}માં તમારા સૌથી નજીકના USD સર્ટિફાઇડ સ્માઇલ ડિઝાઇનર શોધવા માટે, કૃપા કરીને તમારા વિસ્તારનો 6 અંકનો પિનકોડ જણાવશો?"
        )
    if lk == "hi":
        return (
            f"समझ गई! आपका शहर {city_display} दर्ज कर लिया गया है। "
            f"{city_display} में आपके सबसे नजदीकी USD सर्टिफाइड स्माइल डिज़ाइनर ढूंढने के लिए, कृपया अपने क्षेत्र का 6 अंकों का पिनकोड बता दीजिए?"
        )
    if lk == "mr":
        return (
            f"समजले! तुमचे शहर {city_display} नोंदवले गेले आहे. "
            f"{city_display} मध्ये आमचे सर्वात जवळचे USD प्रमाणित स्माइल डिझायनर शोधण्यासाठी, कृपया तुमच्या परिसराचा 6 अंकी पिनकोड सांगा?"
        )
    if lk == "bn":
        return (
            f"বুঝেছি! আপনার শহর {city_display} আপডেট করা হয়েছে। "
            f"{city_display} তে আমাদের নিকটতম USD সার্টিফাইড স্মাইল ডিজাইনার খুঁজতে, দয়া করে আপনার এলাকার ৬ সংখ্যার পিনকোড বলুন?"
        )
    if lk == "ta":
        return (
            f"புரிந்தது! உங்கள் நகரம் {city_display} எனப் புதுப்பிக்கப்பட்டது. "
            f"{city_display} இல் உள்ள எங்கள் அருகிலுள்ள USD சான்றளிக்கப்பட்ட ஸ்மைல் டிசைனரைக் கண்டறிய, உங்கள் பகுதியின் 6 இலக்க பின்கோட்டைச் சொல்ல முடியுமா?"
        )
    if lk == "te":
        return (
            f"అర్థమైంది! మీ నగరం {city_display} గా అప్‌డేట్ చేయబడింది. "
            f"{city_display} లో మా సమీప USD సర్టిఫైడ్ స్మైల్ డిజైనర్‌ను కనుగొనడానికి, దయచేసి మీ ప్రాంతం యొక్క 6 అంకెల పిన్‌కోడ్‌ను తెలియజేయండి?"
        )
    if lk == "kn":
        return (
            f"ಅರ್ಥವಾಯಿತು! ನಿಮ್ಮ ನಗರವನ್ನು {city_display} ಎಂದು ನವೀಕರಿಸಲಾಗಿದೆ. "
            f"{city_display} ನಲ್ಲಿ ನಮ್ಮ ಹತ್ತಿರದ USD ಪ್ರಮಾಣೀಕೃತ ಸ್ಮೈಲ್ ಡಿಸೈನರ್ ಹುಡುಕಲು, ದಯವಿಟ್ಟು ನಿಮ್ಮ 6 ಅಂಕಿಗಳ ಪಿನ್‌ಕೋಡ್ ತಿಳಿಸಿ?"
        )
    if lk == "ml":
        return (
            f"മനസ്സിലായി! നിങ്ങളുടെ നഗരം {city_display} ആയി മാറ്റിയിട്ടുണ്ട്. "
            f"{city_display} യിൽ ഞങ്ങളുടെ ഏറ്റവും അടുത്തുള്ള USD സർട്ടിഫൈഡ് സ്മൈൽ ഡിസൈനറെ കണ്ടെത്താൻ, ദയവായി നിങ്ങളുടെ 6 അക്ക പിൻകോഡ് നൽകുമോ?"
        )
    if lk == "pa":
        return (
            f"ਸਮਝ ਗਈ! ਤੁਹਾਡਾ ਸ਼ਹਿਰ {city_display} ਅਪਡੇਟ ਹੋ ਗਿਆ ਹੈ। "
            f"{city_display} ਵਿੱਚ ਸਾਡੇ ਸਭ ਤੋਂ ਨੇੜਲੇ USD ਪ੍ਰਮਾਣਿਤ ਸਮਾਈਲ ਡਿਜ਼ਾਈਨਰ ਲੱਭਣ ਲਈ, ਕਿਰਪਾ ਕਰਕੇ ਆਪਣੇ ਇਲਾਕੇ ਦਾ 6 ਅੰਕਾਂ ਦਾ ਪਿਨਕੋਡ ਦੱਸੋ?"
        )
    if lk == "or":
        return (
            f"ବୁଝିଗଲି! ଆପଣଙ୍କ ସହର {city_display} ଅପଡେଟ୍ ହୋଇଛି। "
            f"{city_display} ରେ ଆମର ନିକଟତମ USD ସାର୍ଟିଫାଏଡ୍ ସ୍ମାଇଲ୍ ଡିଜାଇନର୍ ଖୋଜିବା ପାଇଁ, ଦୟାକରି ଆପଣଙ୍କ ଅଞ୍ଚଳର ୬ ଅଙ୍କ ବିଶିଷ୍ଟ ପିନକୋଡ୍ ଜଣାନ୍ତୁ?"
        )
    return (
        f"Understood! We have updated your city to {city_display}. "
        f"To help find your nearest USD Certified Smile Designer in {city_display}, could you please tell me your 6-digit area pincode?"
    )


# -------------------------------------------------------------------------
# ⚡ ONLINE POSTAL PINCODE VALIDATION & CITY RESOLUTION ⚡
# -------------------------------------------------------------------------
def get_pincode_city_info(pincode: str) -> Dict[str, str]:
    """
    Extracts canonical city and display area information for a 6-digit Indian pincode.
    Distinguishes between:
    - canonical_city: The primary district or certified city (e.g. 'Surat', 'Ahmedabad', 'Mumbai')
      used for database storage (appointment booking panel) and review summary.
    - display_city: The conversational display format (e.g. 'Sayan, Surat' or 'Surat')
      used when Riya asks the user for area/city confirmation in speech.
    - area: The specific sub-district, block, or taluka (e.g. 'Sayan').
    """
    loc = get_location_for_pincode(pincode)
    if not loc:
        return {"canonical_city": "", "display_city": "", "area": "", "district": "", "state": ""}

    dist = loc.get("district") or ""
    block = loc.get("block") or ""
    div = loc.get("division") or ""
    state = loc.get("state") or ""

    clean_dist = dist.split("/")[0].split(",")[0].strip() if dist else ""
    clean_block = block.strip() if block and block.upper() not in ["NA", "N/A", "NONE"] else ""
    clean_div = div.split("/")[0].split(",")[0].strip() if div else ""

    # Known certified / independent district cities where block should stand alone as canonical city
    KNOWN_INDEPENDENT_CITIES = {
        "Morbi", "Bhavnagar", "Surendranagar", "Anand", "Nadiad", "Mehsana", "Gandhinagar",
        "Navsari", "Valsad", "Junagadh", "Porbandar", "Bhuj", "Gandhidham", "Patan", "Palanpur",
        "Godhra", "Dahod", "Vapi", "Ankleshwar", "Amreli", "Botad", "Halvad", "Dhrangadhra",
        "Bharuch", "Jamnagar", "Rajkot", "Vadodara", "Surat", "Ahmedabad", "Mumbai", "Pune"
    }

    # Normalize Mumbai variations
    if clean_dist.lower() in ["mumbai", "mumbai suburban", "greater mumbai"]:
        clean_dist = "Mumbai"

    # Determine canonical city & sub-area
    if clean_block and clean_block.title() in KNOWN_INDEPENDENT_CITIES:
        canonical_city = clean_block.title()
        area = ""
    elif clean_dist:
        canonical_city = clean_dist.title()
        area = clean_block.title() if clean_block and clean_block.lower() != canonical_city.lower() else ""
    elif clean_div:
        canonical_city = clean_div.title()
        area = clean_block.title() if clean_block and clean_block.lower() != canonical_city.lower() else ""
    else:
        canonical_city = (state or "").title()
        area = ""

    # Determine display_city (used for conversational confirmation speech, e.g. "Sayan, Surat")
    if area and canonical_city:
        display_city = f"{area}, {canonical_city}"
    else:
        display_city = canonical_city

    return {
        "canonical_city": canonical_city,
        "display_city": display_city,
        "area": area,
        "district": clean_dist.title(),
        "state": state
    }


def get_pincode_canonical_city(pincode: str) -> str:
    """Returns canonical city (e.g. 'Surat') for database CRM & review summary."""
    info = get_pincode_city_info(pincode)
    return info.get("canonical_city") or ""


def get_pincode_display_city(pincode: str) -> str:
    """Returns display city (e.g. 'Sayan, Surat') for conversational confirmation speech."""
    info = get_pincode_city_info(pincode)
    return info.get("display_city") or info.get("canonical_city") or ""


def validate_pincode_online(pincode: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates a 6-digit Indian pincode against official Postal PIN Code API.
    Returns: (is_valid, detected_display_city, error_msg)
    """
    clean_pin = re.sub(r"\D", "", str(pincode or "")).strip()
    if len(clean_pin) != 6:
        return False, None, "Pincode must be exactly 6 digits"

    loc = get_location_for_pincode(clean_pin)
    if not loc or not (loc.get("district") or loc.get("block") or loc.get("division")):
        return False, None, f"Pincode {clean_pin} is not registered or not found in India Post records"

    display_city = get_pincode_display_city(clean_pin)
    return True, display_city, None


def format_invalid_pincode_speech(pincode: str, lang: str = "en") -> str:
    """
    Generates an empathetic clarification prompt when the user provides an invalid/unregistered pincode.
    """
    lk = (lang[:2] if lang else "en").lower()
    if lk == "gu":
        return (
            f"માફ કરશો, પિનકોડ {pincode} પોસ્ટલ રેકોર્ડમાં મળ્યો નથી. "
            f"કૃપા કરીને તમારા વિસ્તારનો સાચો 6 અંકનો પિનકોડ જણાવશો?"
        )
    if lk == "hi":
        return (
            f"माफ़ कीजिए, पिनकोड {pincode} पोस्टल रिकॉर्ड में नहीं मिला। "
            f"कृपया अपने क्षेत्र का सही 6 अंकों का पिनकोड बता दीजिए?"
        )
    if lk == "mr":
        return (
            f"क्षमस्व, पिनकोड {pincode} पोस्टल रेकॉर्डमध्ये आढळला नाही. "
            f"कृपया तुमच्या परिसराचा योग्य 6 अंकी पिनकोड सांगा?"
        )
    if lk == "bn":
        return (
            f"দুঃখিত, পিনকোড {pincode} ডাক রেকর্ডে পাওয়া যায়নি। "
            f"দয়া করে আপনার এলাকার সঠিক ৬ সংখ্যার পিনকোড বলুন?"
        )
    if lk == "ta":
        return (
            f"மன்னிக்கவும், பின்கோட் {pincode} தபால் பதிவுகளில் கிடைக்கவில்லை. "
            f"தயவுசெய்து உங்கள் பகுதியின் சரியான 6 இலக்க பின்கோட்டைப் பகிருங்கள்?"
        )
    if lk == "te":
        return (
            f"క్షమించండి, పిన్‌కోడ్ {pincode} పోస్టల్ రికార్డుల్లో కనుగొనబడలేదు. "
            f"దయచేసి మీ ప్రాంతం యొక్క సరైన 6 అంకెల పిన్‌కోడ్‌ను తెలియజేయండి?"
        )
    if lk == "kn":
        return (
            f"ಕ್ಷಮಿಸಿ, ಪಿನ್‌ಕೋಡ್ {pincode} ಅಂಚೆ ದಾಖಲೆಗಳಲ್ಲಿ ಕಂಡುಬಂದಿಲ್ಲ. "
            f"ದಯವಿಟ್ಟು ನಿಮ್ಮ ಪ್ರದೇಶದ ಸರಿಯಾದ 6 ಅಂಕಿಗಳ ಪಿನ್‌ಕೋಡ್ ತಿಳಿಸಿ?"
        )
    if lk == "ml":
        return (
            f"ക്ഷമിക്കണം, പിൻകോഡ് {pincode} തപാൽ രേഖകളിൽ കാണാനില്ല. "
            f"ദയവായി നിങ്ങളുടെ പ്രദേശത്തിന്റെ ശരിയായ 6 അക്ക പിൻകോഡ് നൽകുമോ?"
        )
    if lk == "pa":
        return (
            f"ਮਾਫ ਕਰਨਾ, ਪਿਨਕੋਡ {pincode} ਡਾਕ ਰਿਕਾਰਡ ਵਿੱਚ ਨਹੀਂ ਮਿਲਿਆ। "
            f"ਕਿਰਪਾ ਕਰਕੇ ਆਪਣੇ ਇਲਾਕੇ ਦਾ ਸਹੀ 6 ਅੰਕਾਂ ਦਾ ਪਿਨਕੋਡ ਦੱਸੋ?"
        )
    if lk == "or":
        return (
            f"କ୍ଷମା କରିବେ, ପିନକୋଡ୍ {pincode} ଡାକ ରେକର୍ଡରେ ମିଳିଲା ନାହିଁ। "
            f"ଦୟାକରି ଆପଣଙ୍କ ଅଞ୍ଚଳର ସଠିକ୍ ୬ ଅଙ୍କ ବିଶିଷ୍ଟ ପିନକୋଡ୍ ଜଣାନ୍ତુ?"
        )
    return (
        f"Sorry, pincode {pincode} was not found in postal records. "
        f"Could you please share your correct 6-digit area pincode?"
    )


def format_invalid_phone_speech(phone_input: str, lang: str = "en") -> str:
    """
    Generates an empathetic clarification prompt when the user provides an invalid phone number (e.g. 9 digits instead of 10).
    """
    digits = "".join(filter(str.isdigit, str(phone_input or "")))
    cnt = len(digits) if digits else len(str(phone_input or "").strip())
    lk = (lang[:2] if lang else "en").lower()

    if lk == "gu":
        return f"તમે {cnt} અંકનો નંબર આપ્યો છે. ભારતમાં માન્ય મોબાઈલ નંબર 10 અંકનો હોય છે. કૃપા કરીને તમારો 10 અંકનો મોબાઈલ નંબર આપશો?"
    if lk == "hi":
        return f"आपने {cnt} अंकों का नंबर दिया है। भारत में मान्य मोबाइल नंबर 10 अंकों का होता है। कृपया अपना 10 अंकों का मोबाइल नंबर प्रदान करें।"
    if lk == "mr":
        return f"तुम्ही {cnt} अंकी नंबर दिला आहे. भारतात वैध मोबाईल નંબર 10 अंकांचा असतो. कृपया तुमचा 10 अंकी मोबाईल नंबर द्या?"
    if lk == "bn":
        return f"আপনি {cnt} সংখ্যার নম্বর দিয়েছেন। ভারতে বৈধ মোবাইল নম্বর ১০ অঙ্কের হয়। দয়া করে আপনার ১০ অঙ্কের মোবাইল নম্বর দিন?"
    if lk == "ta":
        return f"நீங்கள் {cnt} இலக்க எண்ணை வழங்கியுள்ளீர்கள். இந்தியாவில் செல்லுபடியாகும் மொபைல் எண் 10 இலக்கங்கள் கொண்டது. தயவுசெய்து உங்கள் 10 இலக்க மொபைல் எண்ணை வழங்கவும்?"
    if lk == "te":
        return f"మీరు {cnt} అంకెల నంబర్ ఇచ్చారు. భారతదేశంలో సరైన మొబైల్ నంబర్ 10 అంకెలు కలిగి ఉంటుంది. దయచేసి మీ 10 అంకెల మొబైల్ నంబర్‌ను ఇవ్వండి?"
    if lk == "kn":
        return f"ನೀವು {cnt} ಅಂಕಿಗಳ ಸಂಖ್ಯೆಯನ್ನು ನೀಡಿದ್ದೀರಿ. ಭಾರತದಲ್ಲಿ ಮಾನ್ಯವಾದ ಮೊಬೈಲ್ ಸಂಖ್ಯೆಯು 10 ಅಂಕಿಗಳನ್ನು ಹೊಂದಿರುತ್ತದೆ. ದಯವಿಟ್ಟು ನಿಮ್ಮ 10 ಅಂಕಿಗಳ ಮೊಬೈಲ್ ಸಂಖ್ಯೆಯನ್ನು ನೀಡಿ?"
    if lk == "ml":
        return f"നിങ്ങൾ നൽകിയത് {cnt} അക്ക നമ്പറാണ്. ഇന്ത്യയിലെ ശരിയായ മൊബൈൽ നമ്പർ 10 അക്കങ്ങളുള്ളതാണ്. ദയവായി നിങ്ങളുടെ 10 അക്ക മൊബൈൽ നമ്പർ നൽകുക?"
    if lk == "pa":
        return f"ਤੁਸੀਂ {cnt} ਅੰਕਾਂ ਦਾ ਨੰਬਰ ਦਿੱਤਾ ਹੈ। ਭਾਰਤ ਵਿੱਚ 10 ਅੰਕਾਂ ਦਾ ਮੋਬਾਈਲ ਨੰਬਰ ਹੁੰਦਾ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ 10 ਅੰਕਾਂ ਦਾ ਮੋਬਾਈਲ ਨੰਬਰ ਪ੍ਰਦਾਨ ਕਰੋ?"
    if lk == "or":
        return f"ଆପଣ {cnt} ଅଙ୍କ ବିଶିଷ୍ଟ ନମ୍ବର ଦେଇଛନ୍ତି। ଭାରତରେ ମାନ୍ୟ ମୋବାଇଲ୍ ନମ୍ବର 10 ଅଙ୍କର ହୋଇଥାଏ। ଦୟାକରି ଆପଣଙ୍କର 10 ଅଙ୍କ ବିଶିଷ୍ଟ ମୋବାଇଲ୍ ନମ୍ବର ପ୍ରଦାନ କରନ୍ତୁ?"
    return f"You provided a {cnt}-digit number ({phone_input}). A valid mobile number in India must have exactly 10 digits. Could you please provide your 10-digit mobile number?"


def format_city_confirm_speech(pincode: str, city: str, lang: str = "en") -> str:
    """
    Generates a prompt confirming the detected city/area from the 6-digit pincode.
    User's requirement: 'first ask pincode then confirm city with pincode'.
    """
    lk = (lang[:2] if lang else "en").lower()
    city_display = city.title() if city else "your"

    if lk == "gu":
        return f"તમારા પિનકોડ {pincode} મુજબ, તમે {city_display} વિસ્તારમાં રહો છો, બરાબર ને?"
    if lk == "hi":
        return f"आपके पिनकोड {pincode} के अनुसार, आप {city_display} क्षेत्र में रहते हैं, सही ना?"
    if lk == "mr":
        return f"तुमच्या पिनकोड {pincode} नुसार, तुम्ही {city_display} भागात राहता, बरोबर ना?"
    if lk == "bn":
        return f"আপনার পিনকোڈ {pincode} অনুযায়ী, আপনি {city_display} এলাকায় থাকেন, তাই তো?"
    if lk == "ta":
        return f"உங்கள் பின்கோட் {pincode} அடிப்படையில், நீங்கள் {city_display} பகுதியில் வசிக்கிறீர்கள், சரியா?"
    if lk == "te":
        return f"మీ పిన్‌కోడ్ {pincode} ప్రకారం, మీరు {city_display} ప్రాంతంలో నివసిస్తున్నారు, సరైనదేనా?"
    if lk == "kn":
        return f"ನಿಮ್ಮ ಪಿನ್‌ಕೋಡ್ {pincode} ಪ್ರಕಾರ, ನೀವು {city_display} ಪ್ರದೇಶದಲ್ಲಿ ವಾಸಿಸುತ್ತಿದ್ದೀರಿ, ಸರಿಯೇ?"
    if lk == "ml":
        return f"നിങ്ങളുടെ പിൻകോഡ് {pincode} അനുസരിച്ച്, നിങ്ങൾ {city_display} പ്രദേശത്താണ് താമസിക്കുന്നത്, ശരിയല്ലേ?"
    if lk == "pa":
        return f"ਤੁਹਾਡੇ ਪਿਨਕੋਡ {pincode} ਅਨੁਸਾਰ, ਤੁਸੀਂ {city_display} ਇਲਾਕੇ ਵਿੱਚ ਰਹਿੰਦੇ ਹੋ, ਠੀਕ ਹੈ ਨਾ?"
    if lk == "or":
        return f"ଆପଣଙ୍କ ପିନକୋଡ୍ {pincode} ଅନୁଯାୟୀ, ଆପଣ {city_display} ଅଞ୍ଚଳରେ ରହୁଛନ୍ତି, ଠିକ୍ ତ?"
    return f"Based on your pincode {pincode}, you reside in {city_display} area, right?"



# -------------------------------------------------------------------------
# ⚡ INDIAN STATE VS. CITY RECOGNITION ENGINE ⚡
# -------------------------------------------------------------------------
INDIAN_STATES_DATA: Dict[str, Dict] = {
    "Sikkim": {
        "aliases": ["sikkim", "સિક્કિમ", "सिक्किम", "sikim", "shikkim"],
        "sample_cities": {
            "en": "Gangtok, Namchi, Singtam, or Pakyong",
            "hi": "गंगटोक, नामची, सिंगतम या पाक्योन्ग",
            "gu": "ગંગટોક, નામચી, સિંગતમ કે પાક્યોંગ",
        },
        "default_city": "Gangtok",
    },
    "Gujarat": {
        "aliases": ["gujarat", "ગુજરાત", "गुजरात", "gujrat", "gujarath"],
        "sample_cities": {
            "en": "Ahmedabad, Surat, Vadodara, or Rajkot",
            "hi": "अहमदाबाद, सूरत, वडोदरा या राजकोट",
            "gu": "અમદાવાદ, સુરત, વડોદરા કે રાજકોટ",
        },
        "default_city": "Ahmedabad",
    },
    "Maharashtra": {
        "aliases": ["maharashtra", "મહારાષ્ટ્ર", "महाराष्ट्र", "maharastra", "maha"],
        "sample_cities": {
            "en": "Mumbai, Pune, Nagpur, or Nashik",
            "hi": "मुंबई, पुणे, नागपुर या नासिक",
            "gu": "મુંબઈ, પુણે, નાગપુર કે નાશિક",
        },
        "default_city": "Mumbai",
    },
    "Rajasthan": {
        "aliases": ["rajasthan", "રાજસ્થાન", "राजस्थान", "rajsthan"],
        "sample_cities": {
            "en": "Jaipur, Jodhpur, Udaipur, or Kota",
            "hi": "जयपुर, जोधपुर, उदयपुर या कोटा",
            "gu": "જયપુર, જોધપુર, ઉદયપુર કે કોટા",
        },
        "default_city": "Jaipur",
    },
    "Madhya Pradesh": {
        "aliases": ["madhya pradesh", "મધ્ય પ્રદેશ", "मध्य प्रदेश", "mp", "m.p."],
        "sample_cities": {
            "en": "Indore, Bhopal, Gwalior, or Jabalpur",
            "hi": "इंदौर, भोपाल, ग्वालियर या जबलपुर",
            "gu": "ઇન્દોર, ભોપાલ, ગ્વાલિયર કે જબલપુર",
        },
        "default_city": "Indore",
    },
    "Uttar Pradesh": {
        "aliases": ["uttar pradesh", "ઉત્તર પ્રદેશ", "उत्तर प्रदेश", "up", "u.p."],
        "sample_cities": {
            "en": "Lucknow, Kanpur, Varanasi, or Agra",
            "hi": "लखनऊ, कानपुर, वाराणसी या आगरा",
            "gu": "લખનૌ, કાનપુર, વારાણસી કે આગ્રા",
        },
        "default_city": "Lucknow",
    },
    "Karnataka": {
        "aliases": ["karnataka", "કર્ણાટક", "कर्नाटक", "karnatak"],
        "sample_cities": {
            "en": "Bangalore, Mysuru, Hubballi, or Mangaluru",
            "hi": "बैंगलोर, मैसूर, हुबली या मैंगलोर",
            "gu": "બેંગલોર, મૈસૂર, હુબલી કે મેંગલોર",
        },
        "default_city": "Bangalore",
    },
    "Tamil Nadu": {
        "aliases": ["tamil nadu", "તમિલનાડુ", "तमिलनाडु", "tamilnadu", "tn", "t.n."],
        "sample_cities": {
            "en": "Chennai, Coimbatore, Madurai, or Salem",
            "hi": "चेन्नई, कोयम्बटूर, मदुरै या सेलम",
            "gu": "ચેન્નઈ, કોઈમ્બતૂર, મદુરૈ કે સેલેમ",
        },
        "default_city": "Chennai",
    },
    "Telangana": {
        "aliases": ["telangana", "તેલંગાણા", "तेलंगाना", "telengana"],
        "sample_cities": {
            "en": "Hyderabad, Warangal, or Nizamabad",
            "hi": "हैदराबाद, वारंगल या निजामाबाद",
            "gu": "હૈદરાબાદ, વારંગલ કે નિઝામાબાદ",
        },
        "default_city": "Hyderabad",
    },
    "Andhra Pradesh": {
        "aliases": ["andhra pradesh", "આંધ્ર પ્રદેશ", "आंध्र प्रदेश", "andhra", "ap", "a.p."],
        "sample_cities": {
            "en": "Visakhapatnam, Vijayawada, Guntur, or Tirupati",
            "hi": "विशाखापट्टनम, विजयवाड़ा, गुंटूर या तिरुपति",
            "gu": "વિશાખાપટ્ટનમ, વિજયવાડા, ગુંટૂર કે તિરુપતિ",
        },
        "default_city": "Visakhapatnam",
    },
    "West Bengal": {
        "aliases": ["west bengal", "પશ્ચિમ બંગાળ", "पश्चिम बंगाल", "bengal", "paschim banga"],
        "sample_cities": {
            "en": "Kolkata, Siliguri, Howrah, or Durgapur",
            "hi": "कोलकाता, सिलीगुड़ी, हावड़ा या दुर्गापुर",
            "gu": "કોલકાતા, સિલીગુડી, હાવડા કે દુર્ગાપુર",
        },
        "default_city": "Kolkata",
    },
    "Bihar": {
        "aliases": ["bihar", "બિહાર", "बिहार"],
        "sample_cities": {
            "en": "Patna, Gaya, Bhagalpur, or Muzaffarpur",
            "hi": "पटना, गया, भागलपुर या मुजफ्फरपुर",
            "gu": "પટના, ગયા, ભાગલપુર કે મુઝફ્ફરપુર",
        },
        "default_city": "Patna",
    },
    "Punjab": {
        "aliases": ["punjab", "પંજાબ", "पंजाब"],
        "sample_cities": {
            "en": "Ludhiana, Amritsar, Jalandhar, or Patiala",
            "hi": "लुधियाना, अमृतसर, जालंधर या पटियाला",
            "gu": "લુધિયાણા, અમૃતસર, જાલંધર કે પટિયાલા",
        },
        "default_city": "Ludhiana",
    },
    "Haryana": {
        "aliases": ["haryana", "હરિયાણા", "हरियाणा"],
        "sample_cities": {
            "en": "Gurugram, Faridabad, Panipat, or Ambala",
            "hi": "गुरुग्राम, फरीदाबाद, पानीपत या अंबाला",
            "gu": "ગુરુગ્રામ, ફરીદાબાદ, પાણીપત કે અંબાલા",
        },
        "default_city": "Gurugram",
    },
    "Kerala": {
        "aliases": ["kerala", "કેરળ", "केरल"],
        "sample_cities": {
            "en": "Kochi, Thiruvananthapuram, Kozhikode, or Thrissur",
            "hi": "कोच्चि, तिरुवनंतपुरम, कोझिकोड या त्रिशूर",
            "gu": "કોચી, તિરુવનંતપુરમ, કોઝિકોડ કે ત્રિશૂર",
        },
        "default_city": "Kochi",
    },
    "Odisha": {
        "aliases": ["odisha", "ઓડિશા", "ओडिशा", "orissa"],
        "sample_cities": {
            "en": "Bhubaneswar, Cuttack, Rourkela, or Puri",
            "hi": "भुवनेश्वर, कटक, राउरकेला या पुरी",
            "gu": "ભુવનેશ્વર, કટક, રાઉરકેલા કે પુરી",
        },
        "default_city": "Bhubaneswar",
    },
    "Assam": {
        "aliases": ["assam", "આસામ", "અસમ", "असम"],
        "sample_cities": {
            "en": "Guwahati, Silchar, Dibrugarh, or Jorhat",
            "hi": "गुवाहाटी, सिलचर, डिब्रूगढ़ या जोरहाट",
            "gu": "ગુવાહાટી, સિલચર, ડિબ્રુગઢ કે જોરહાટ",
        },
        "default_city": "Guwahati",
    },
    "Jharkhand": {
        "aliases": ["jharkhand", "ઝારખંડ", "झारखंड"],
        "sample_cities": {
            "en": "Ranchi, Jamshedpur, Dhanbad, or Bokaro",
            "hi": "रांची, जमशेदपुर, धनबाद या बोकारो",
            "gu": "રાંચી, જમશેદપુર, ધનબાદ કે બોકારો",
        },
        "default_city": "Ranchi",
    },
    "Chhattisgarh": {
        "aliases": ["chhattisgarh", "છત્તીસગઢ", "छत्तीसगढ़", "chattisgarh"],
        "sample_cities": {
            "en": "Raipur, Bhilai, Bilaspur, or Korba",
            "hi": "रायपुर, भिलाई, बिलासपुर या कोरबा",
            "gu": "રાયપુર, ભિલાઈ, બિલાસપુર કે કોરબા",
        },
        "default_city": "Raipur",
    },
    "Uttarakhand": {
        "aliases": ["uttarakhand", "ઉત્તરાખંડ", "उत्तराखंड", "uttaranchal"],
        "sample_cities": {
            "en": "Dehradun, Haridwar, Rishikesh, or Haldwani",
            "hi": "देहरादून, हरिद्वार, ऋषिकेश या हल्द्वानी",
            "gu": "દેહરાદૂન, હરિદ્વાર, ઋષિકેશ કે હલ્દ્વાની",
        },
        "default_city": "Dehradun",
    },
    "Himachal Pradesh": {
        "aliases": ["himachal pradesh", "હિમાચલ પ્રદેશ", "हिमाचल प्रदेश", "himachal"],
        "sample_cities": {
            "en": "Shimla, Dharamshala, Solan, or Mandi",
            "hi": "शिमला, धर्मशाला, सोलन या मंडी",
            "gu": "શિમલા, ધર્મશાલા, સોલન કે મંડી",
        },
        "default_city": "Shimla",
    },
    "Goa": {
        "aliases": ["goa", "ગોવા", "गोवा"],
        "sample_cities": {
            "en": "Panaji, Margao, Vasco da Gama, or Mapusa",
            "hi": "पणजी, मडगाँव, वास्को या मापुसा",
            "gu": "પણજી, મડગાંવ, વાસ્કો કે માપુસા",
        },
        "default_city": "Panaji",
    },
    "Tripura": {
        "aliases": ["tripura", "ત્રિપુરા", "त्रिपुरा"],
        "sample_cities": {
            "en": "Agartala, Dharmanagar, or Udaipur",
            "hi": "अगरतला, धर्मनगर या उदयपुर",
            "gu": "અગરતલા, ધર્માનગર કે ઉદયપુર",
        },
        "default_city": "Agartala",
    },
    "Meghalaya": {
        "aliases": ["meghalaya", "મેઘાલય", "मेघालय"],
        "sample_cities": {
            "en": "Shillong, Tura, or Jowai",
            "hi": "शिलांग, तुरा या जोवाई",
            "gu": "શિલોંગ, તુરા કે જોવાઈ",
        },
        "default_city": "Shillong",
    },
    "Manipur": {
        "aliases": ["manipur", "મણિપુર", "मणिपुर"],
        "sample_cities": {
            "en": "Imphal, Churachandpur, or Thoubal",
            "hi": "इंफाल, चुराचांदपुर या थौबल",
            "gu": "ઇમ્ફાલ, ચુરાચંદપુર કે થૌબલ",
        },
        "default_city": "Imphal",
    },
    "Nagaland": {
        "aliases": ["nagaland", "નાગાલેન્ડ", "नागालैंड"],
        "sample_cities": {
            "en": "Kohima, Dimapur, or Mokokchung",
            "hi": "कोहिमा, दीमापुर या मोकोकचुंग",
            "gu": "કોહિમા, દીમાપુર કે મોકોકચુંગ",
        },
        "default_city": "Dimapur",
    },
    "Mizoram": {
        "aliases": ["mizoram", "મિઝોરમ", "मिज़ोरम", "मिजोरम"],
        "sample_cities": {
            "en": "Aizawl, Lunglei, or Champhai",
            "hi": "आइजोल, लुंगलेई या चम्फाई",
            "gu": "આઇઝોલ, લુંગલેઈ કે ચમ્ફાઈ",
        },
        "default_city": "Aizawl",
    },
    "Arunachal Pradesh": {
        "aliases": ["arunachal pradesh", "અરુણાચલ પ્રદેશ", "अरुणाचल प्रदेश", "arunachal"],
        "sample_cities": {
            "en": "Itanagar, Naharlagun, or Pasighat",
            "hi": "ईटानगर, नाहरलागुन या पासीघाट",
            "gu": "ઇટાનગર, નાહરલાગુન કે પાસીઘાટ",
        },
        "default_city": "Itanagar",
    },
    "Jammu and Kashmir": {
        "aliases": ["jammu and kashmir", "jammu & kashmir", "જમ્મુ અને કાશ્મીર", "जम्मू और कश्मीर", "kashmir", "jammu kashmir"],
        "sample_cities": {
            "en": "Srinagar, Jammu, or Anantnag",
            "hi": "श्रीनगर, जम्मू या अनंतनाग",
            "gu": "શ્રીનગર, જમ્મુ કે અનંતનાગ",
        },
        "default_city": "Srinagar",
    },
    "Ladakh": {
        "aliases": ["ladakh", "લદ્દાખ", "लद्दाख"],
        "sample_cities": {
            "en": "Leh or Kargil",
            "hi": "लेह या कारगिल",
            "gu": "લેહ કે કારગિલ",
        },
        "default_city": "Leh",
    }
}


def detect_indian_state(text: str) -> Optional[str]:
    """
    Detects if the user mentioned an Indian state name.
    Returns standard State name (e.g. 'Sikkim', 'Gujarat', 'Maharashtra') or None.
    """
    if not text:
        return None
    tl = str(text).lower().strip()

    # Check each state and its aliases
    for state_name, data in INDIAN_STATES_DATA.items():
        aliases = data.get("aliases", [])
        for alias in aliases:
            if alias.isascii():
                pattern = rf"\b{re.escape(alias)}\b"
                if re.search(pattern, tl, re.IGNORECASE):
                    return state_name
            else:
                if alias in tl:
                    return state_name
    return None


def format_state_to_city_speech(state: str, lang: str = "en") -> str:
    """
    Generates an empathetic clarification prompt when the user provides an Indian State instead of a City.
    Asks which city or town inside that state they reside in, providing relevant examples.
    """
    lang = (lang or "en").lower()
    state_display = state.title() if state else "your state"
    state_info = INDIAN_STATES_DATA.get(state, {})
    sample_cities_dict = state_info.get("sample_cities", {})
    aliases = state_info.get("aliases", [])

    if lang in ["gu", "gujarati"]:
        gu_name = next((a for a in aliases if any('\u0A80' <= c <= '\u0AFF' for c in a)), state_display)
        samples = sample_cities_dict.get("gu") or sample_cities_dict.get("en", "ગંગટોક કે નામચી")
        return (
            f"{gu_name} એક સુંદર રાજ્ય છે! {gu_name}માં તમે કયા શહેરમાં રહો છો "
            f"(જેમ કે {samples})?"
        )
    if lang in ["hi", "hindi"]:
        hi_name = next((a for a in aliases if any('\u0900' <= c <= '\u097F' for c in a)), state_display)
        samples = sample_cities_dict.get("hi") or sample_cities_dict.get("en", "गंगटोक या नामची")
        return (
            f"{hi_name} एक खूबसूरत राज्य है! {hi_name} में आप किस शहर या कस्बे में रहते हैं "
            f"(जैसे कि {samples})?"
        )
    samples = sample_cities_dict.get("en", "Gangtok or Namchi")
    return (
        f"{state_display} is a wonderful state! Which city or town do you reside in inside {state_display} "
        f"(for example, {samples})?"
    )


