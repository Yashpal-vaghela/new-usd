import re

def is_explain_only_question(input_text=""):
    text = str(input_text or "").lower().strip()
    if not text:
        return False
    return (
        text.startswith("what is") or
        text.startswith("what are") or
        text.startswith("what's") or
        text.startswith("whats") or
        text.startswith("define") or
        text.startswith("explain") or
        text.startswith("tell me about") or
        text.startswith("what does") or
        text.startswith("meaning of") or
        "what is ultimate smile design" in text or
        "what are veneers" in text or
        "what are crowns" in text or
        "what are aligners" in text or
        "what is smile design" in text
    )

def is_personal_problem_text(input_text=""):
    text = str(input_text or "").lower().strip()
    if not text:
        return False
    keywords = [
        "i have", "i'm facing", "im facing", "i am facing", "my teeth", "my tooth",
        "my gums", "my smile", "pain", "ache", "gap", "gaps", "chip", "chipped",
        "broken", "missing tooth", "missing teeth", "stain", "yellow", "crooked",
        "cavity", "decay", "sensitivity", "bleeding", "swollen", "दर्द", "दिक्कत",
        "गैप", "टूट", "पीला", "દર્દ", "સમસ્યા", "ગેપ", "તૂટ", "પીળ"
    ]
    return any(kw in text for kw in keywords)

def detect_tag_from_text(input_text=""):
    text = str(input_text or "").lower().strip()
    if not text:
        return None
        
    tag_match = re.search(r"<!--\s*\[?(LINK_[A-Z_]+|END_CHAT)\]?\s*-->", input_text, re.IGNORECASE)
    if tag_match:
        return f"[{tag_match.group(1).upper()}]"
        
    if "end chat" in text or "goodbye" in text or "bye" in text or "take care" in text or "see you" in text:
        return "[END_CHAT]"
        
    # 1. Immediately share LINK_CONSULT if user talks about booking or consulting
    if any(k in text for k in ["consultation", "schedule", "appointment", "book", "visit the clinic", "book a visit", "consult with dentist", "कंसल्टेशन", "अपॉइंटमेंट", "बुक", "परामर्श", "કન્સલ્ટેશન", "એપોઇન્ટમેન્ટ", "બુક"]) or ("consult" in text and "consultant" not in text and "consulting" not in text):
        return "[LINK_CONSULT]"
        
    # 2. Immediately share LINK_DENTISTS if user talks about nearest / certified smile designers
    if any(k in text for k in [
        "certified dentist", "certified dentists", "certified smile designer", "certified smile designers",
        "certified designer", "certified designers", "smile designer", "smile designers",
        "nearest designer", "find dentist", "find a designer", "nearby dentist", "locate dentist",
        "dentist in", "dentists in", "designer in", "designers in", "clinic in", "clinics in",
        "dentist near", "dentists near", "clinic near", "clinics near",
        "how many dentist", "how many dentists", "how many designer", "how many designers",
        "is certified", "are certified",
        "सर्टिफाइड डेंटिस्ट", "नजदीकी डेंटिस्ट", "करीबी डेंटिस्ट", "डेंटिस्ट ढूंढ", "स्माइल डिज़ाइनर",
        "में डेंटिस्ट", "के डेंटिस्ट",
        "સર્ટિફાઇડ ડેન્ટિસ્ટ", "નજીકના ડેન્ટિસ્ટ", "ડેન્ટિસ્ટ શોધ", "સ્માઇલ ડિઝાઇનર",
        "માં ડેન્ટિસ્ટ", "ના ડેન્ટિસ્ટ"
    ]):
        return "[LINK_DENTISTS]"
        
    # 3. For any OTHER links, we strictly require explicit link request keywords
    explicit_link_words = [
        "link", "url", "website", "site", "page", "button", "click", "href", "address",
        "लिंक", "वेबसाइट", "पेज", "बटन", "લિંક", "વેબસાઇટ", "પેજ", "બટન",
        "send me", "share", "give me", "provide", "show me", "open", "go to", "where can i", "how to"
    ]
    if not any(w in text for w in explicit_link_words):
        return None

    if any(k in text for k in ["virtual smile", "try on", "try-on", "smile try", "smile makeover", "design my smile", "see how your smile", "before and after", "before/after", "virtual try on", "वर्चुअल स्माइल", "ट्राय ऑन", "वर्चुअल ट्राय", "વર્ચ્યુઅલ સ્માઇલ", "ટ્રાય ઑન"]):
        return "[LINK_VTRYON]"
    if any(k in text for k in ["contact", "reach out", "get in touch", "call us", "phone number", "संपर्क", "कॉल", "संपर्क करें", "સંપર્ક", "કૉલ", "સંપર્ક કરો"]):
        return "[LINK_CONTACT]"
    if any(k in text for k in ["dentist connect", "become certified dentist", "collaborate", "partner", "join our network", "डेंटिस्ट连接", "सहयोग", "પાર્ટનર", "ડેન્ટિસ્ટ કનેક્ટ"]):
        return "[LINK_CONNECT]"
    if any(k in text for k in ["gallery", "results", "before and after", "before/after", "गैलरी", "रिजल्ट", "ગેલેરી", "રિઝલ્ટ"]):
        return "[LINK_GALLERY]"
    if any(k in text for k in ["authentication", "authentication card", "authentic", "verify warranty", "warranty", "verify treatment", "genuine treatment", "genuine products", "authentication certificate"]):
        return "[LINK_WARRANTY]"
        
    return None

def detect_best_tag(user_text="", bot_text=""):
    return detect_tag_from_text(user_text)

def detect_best_tag_with_fallback(user_text="", bot_text="", pending_action_tag=None):
    user_tag = detect_tag_from_text(user_text)
    
    yes_words = [
        "yes", "yeah", "yup", "sure", "okay", "ok", "please", "send",
        "send me", "go ahead", "do it", "haan", "ha", "haanji", "ji",
        "yes please", "haji", "sare", "thik", "ok please", "sure please", "haan ji",
        "mokal", "moklo", "mokhal", "bhejo", "dijiye", "bhej", "share", "provide",
        "મોકલો", "મોકલ", "ભેજો", "भेजो", "लिंक", "લિંક"
    ]
    lower_user = str(user_text or "").lower()
    
    final_tag = user_tag
    if not final_tag and pending_action_tag:
        if any(w in lower_user for w in yes_words):
            final_tag = pending_action_tag
            pending_action_tag = None
            return final_tag, pending_action_tag
            
    link_tags = [
        "[LINK_DENTISTS]", "[LINK_CONSULT]", "[LINK_CONTACT]",
        "[LINK_GALLERY]", "[LINK_VTRYON]", "[LINK_CONNECT]", "[LINK_WARRANTY]"
    ]
    
    # If the user did not explicitly trigger a tag, check if the bot actively offers/provides one
    if not final_tag and bot_text:
        bot_tag = detect_tag_from_text(bot_text)
        if bot_tag in link_tags:
            lower_bot = str(bot_text).lower()
            bot_link_words = [
                "link", "provide", "send", "here is", "click", "button",
                "લિંક", "મોકલી", "મોકલ", "મોકલાવું", "ભેજ", "भेज", "लिंक"
            ]
            if any(w in lower_bot for w in bot_link_words):
                final_tag = bot_tag
                pending_action_tag = None
                return final_tag, pending_action_tag
            
    # Track the active topic to establish the pending tag for the next turn
    if user_tag in link_tags:
        pending_action_tag = user_tag
    elif bot_text:
        bot_tag = detect_tag_from_text(bot_text)
        if bot_tag in link_tags:
            pending_action_tag = bot_tag
            
    return final_tag, pending_action_tag
