import os
import json
import time
import uuid
import urllib.request

from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_POST
from django.conf import settings
from django.utils import timezone

from virtualsmileAI.forms import SmileDesignLeadForm
from virtualsmileAI.gemini import add_logo_on_right
from .yolo import decode_base64_image, run_inference_on_bgr, encode_image_to_base64_jpeg
from .gemini import generate_smile_design
from .models import SmileDesignLead

THRESHOLD = getattr(settings, "TEETH_DETECTION_THRESHOLD", 0.55)


def smile(request):
    """
    Renders the main page. If you post a normal HTML form (non-AJAX),
    it will also save lead using SmileDesignLeadForm.
    """
    if request.method == "POST":
        form = SmileDesignLeadForm(request.POST)

        if form.is_valid():
            submission = form.save()
            print("✅ SAVED:", submission)
            return render(
                request,
                "virtual-smile-try-on.html",
                {"form": SmileDesignLeadForm(), "success": True, "threshold": THRESHOLD},
            )

        print("❌ FORM ERRORS:", form.errors)
        print("❌ POST DATA:", request.POST)
        return render(
            request,
            "virtual-smile-try-on.html",
            {"form": form, "success": False, "threshold": THRESHOLD},
        )

    # ✅ IMPORTANT: Always send both threshold + form for GET
    return render(
        request,
        "virtual-smile-try-on.html",
        {"threshold": THRESHOLD, "form": SmileDesignLeadForm()},
    )


@require_POST
@csrf_protect
def create_smile_lead_api(request):
    """
    ✅ For Bootstrap modal submit (AJAX)
    POST JSON: { name, phone, city, message }
    Saves into SmileDesignLead table via SmileDesignLeadForm.
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    # Map to your form fields (make sure form has same field names)
    data = {
        "name": (payload.get("name") or "").strip(),
        "phone": (payload.get("phone") or "").strip(),
        "city": (payload.get("city") or "").strip(),
        "email": (payload.get("email") or "").strip(),
    }

    form = SmileDesignLeadForm(data)
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)

    obj = form.save(commit=False)

    obj.before_image = request.session.get("smile_before", "")
    obj.after_image = request.session.get("smile_after", "")
    obj.save()
    request.session.pop("smile_before", None)
    request.session.pop("smile_after", None)
    return JsonResponse({"ok": True, "id": obj.id})


@require_POST
@csrf_protect
def trigger_whatsapp_api(request):
    def to_absolute(url):
        if not url:
            return ""
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return request.build_absolute_uri(url)

    try:
        incoming = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    lead_id = incoming.get("lead_id")
    if not lead_id:
        return JsonResponse({"ok": False, "error": "Missing lead_id"}, status=400)

    before_url = (incoming.get("before_url") or "").strip()
    after_url = (incoming.get("after_url") or "").strip()

    try:
        lead = SmileDesignLead.objects.get(id=lead_id)
    except SmileDesignLead.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Lead not found"}, status=404)

    # Save media paths (optional)
    media_prefix = settings.MEDIA_URL.rstrip("/") + "/"

    def normalize_media_path(url):
        if not url:
            return ""
        if url.startswith(media_prefix):
            return url[len(media_prefix):]
        abs_media = request.build_absolute_uri(settings.MEDIA_URL)
        if url.startswith(abs_media):
            return url[len(abs_media):]
        return url

    if before_url and not lead.before_image:
        lead.before_image = normalize_media_path(before_url)
    if after_url and not lead.after_image:
        lead.after_image = normalize_media_path(after_url)
    if before_url or after_url:
        lead.save(update_fields=["before_image", "after_image"])

    # Phone normalization
    raw_phone = (lead.phone or "").strip()
    cleaned = "".join(ch for ch in raw_phone if ch.isdigit() or ch == "+")
    if cleaned and not cleaned.startswith("+"):
        if cleaned.startswith("91"):
            cleaned = "+" + cleaned
        elif len(cleaned) == 10:
            cleaned = "+91" + cleaned

    if not cleaned or not cleaned.startswith("+") or len(cleaned) < 12:
        return JsonResponse({"ok": False, "error": f"Invalid phone: {cleaned}"}, status=400)

    out_payload = {
        "Name": lead.name,
        "Email": lead.email,
        "Contact": cleaned,
        "Image": to_absolute(after_url),  # ✅ absolute
        "DateTime": timezone.localtime(lead.created_at).strftime("%d%m%y %H:%M:%S"),
    }

    # If image missing, fail early
    if not out_payload["Image"].startswith("http"):
        return JsonResponse({"ok": False, "error": f"Invalid Image URL: {out_payload['Image']}"}, status=400)

    webhook_url = getattr(
        settings,
        "WHATSAPP_WEBHOOK_URL",
        "https://bikapi.bikayi.app/chatbot/webhook/N8eHI9BWzqVPK7RnXu2xs5qIQt23?flow=aismilede5921",
    )

    try:
        data = json.dumps(out_payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_body = resp.read().decode("utf-8", errors="ignore")
            status = resp.status

        # Try to parse Bikayi response
        try:
            parsed = json.loads(resp_body)
        except Exception:
            parsed = {"raw": resp_body}

        ok = (200 <= status < 300)
        # Respect common success flags if present
        if isinstance(parsed, dict):
            if "success" in parsed:
                ok = ok and bool(parsed["success"])
            if "ok" in parsed:
                ok = ok and bool(parsed["ok"])

        return JsonResponse({"ok": ok, "status": status, "response": parsed})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=502)

@csrf_exempt
# def detect_api(request):
#     """
#     POST JSON: { image: <base64 dataURL> }
#     Returns: { conf: float, visible: bool, annotated: <base64 dataURL> }
#     """
#     if request.method != "POST":
#         return HttpResponseBadRequest("POST required")

#     try:
#         payload = json.loads(request.body.decode("utf-8"))
#     except Exception:
#         return HttpResponseBadRequest("Invalid JSON")

#     img_b64 = payload.get("image")
#     if not img_b64:
#         return HttpResponseBadRequest("Missing image")

#     try:
#         img_bgr = decode_base64_image(img_b64)
#         out = run_inference_on_bgr(img_bgr)

#         conf = float(out["max_conf"])
#         visible = bool(out["visible"])

#         # You can keep returning annotated (even if you hide in UI)
#         annotated = encode_image_to_base64_jpeg(out["annotated_bgr"], quality=80)

#         return JsonResponse({"conf": conf, "visible": visible, "annotated": annotated})
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def capture_api(request):
    """
    POST JSON: { image: <base64 dataURL>, conf: float }
    Saves image only if conf > THRESHOLD.
    Returns: { saved: bool, path: <media url>, conf: float }
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    img_b64 = payload.get("image")
    conf = payload.get("conf", 0)

    if img_b64 is None:
        return HttpResponseBadRequest("Missing image")

    try:
        conf = float(conf)
    except Exception:
        conf = 0.0

    if conf <= THRESHOLD:
        return JsonResponse({"saved": False, "reason": "confidence too low", "conf": conf})

    try:
        img_bgr = decode_base64_image(img_b64)

        out_dir = os.path.join(settings.MEDIA_ROOT, "captures")
        os.makedirs(out_dir, exist_ok=True)

        fname = f"capture_{int(time.time())}_{uuid.uuid4().hex[:8]}.jpg"
        out_path = os.path.join(out_dir, fname)

        import cv2
        cv2.imwrite(out_path, img_bgr)

        url = settings.MEDIA_URL + "captures/" + fname
        return JsonResponse({"saved": True, "path": url, "conf": conf})
    except Exception as e:
        return JsonResponse({"saved": False, "error": str(e)}, status=400)


@csrf_exempt
def smile_design_api(request):
    """
    Accepts JSON {image: dataUrl/base64}.
    Saves before image, adds logo on right, sends to Gemini, saves after, returns URLs.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    img_b64 = payload.get("image")
    if not img_b64:
        return JsonResponse({"error": "Missing image"}, status=400)

    try:
        img_bgr = decode_base64_image(img_b64)
    except Exception as e:
        return JsonResponse({"error": f"Could not decode image: {str(e)}"}, status=400)

    out_dir = os.path.join(settings.MEDIA_ROOT, "smile_design")
    before_dir = os.path.join(out_dir, "before")
    after_dir = os.path.join(out_dir, "after")

    os.makedirs(before_dir, exist_ok=True)
    os.makedirs(after_dir, exist_ok=True)

    ts = int(time.time())
    uid = uuid.uuid4().hex[:10]

    before_name = f"before_{ts}_{uid}.jpg"
    after_name = f"after_{ts}_{uid}.jpg"

    before_path = os.path.join(before_dir, before_name)
    after_path = os.path.join(after_dir, after_name)

    import cv2
    cv2.imwrite(before_path, img_bgr)

    # ✅ add logo (as your code already does)
    try:
        add_logo_on_right(
            before_path,
            os.path.join(settings.MEDIA_ROOT, "logo", "usd-logo.png"),
        )
    except Exception as e:
        # If logo fails, still continue with Gemini
        print("⚠️ Logo add failed:", e)

    # ✅ Run Gemini (full image)
    try:
        generate_smile_design(before_path, after_path)
    except RuntimeError as e:
        msg = str(e)
        if "GEMINI_API_KEY" in msg or "not installed" in msg.lower() or "not configured" in msg.lower():
            return JsonResponse({"error": msg}, status=501)
        return JsonResponse({"error": msg}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    request.session["smile_before"] = f"smile_design/before/{before_name}"
    request.session["smile_after"] = f"smile_design/after/{after_name}"
    request.session.modified = True

    before_url = f"{settings.MEDIA_URL}smile_design/before/{before_name}"
    after_url = f"{settings.MEDIA_URL}smile_design/after/{after_name}"

    return JsonResponse({"before_url": before_url, "after_url": after_url, "ok": True})
