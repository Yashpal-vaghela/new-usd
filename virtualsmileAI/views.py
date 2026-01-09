import os
import json
import time
import uuid

from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_POST
from django.conf import settings

from virtualsmileAI.forms import SmileDesignLeadForm
from virtualsmileAI.gemini import add_logo_on_right
from .yolo import decode_base64_image, run_inference_on_bgr, encode_image_to_base64_jpeg
from .gemini import generate_smile_design

THRESHOLD = getattr(settings, "TEETH_DETECTION_THRESHOLD", 0.65)


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
        "message": (payload.get("message") or "").strip(),
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


@csrf_exempt
def detect_api(request):
    """
    POST JSON: { image: <base64 dataURL> }
    Returns: { conf: float, visible: bool, annotated: <base64 dataURL> }
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    img_b64 = payload.get("image")
    if not img_b64:
        return HttpResponseBadRequest("Missing image")

    try:
        img_bgr = decode_base64_image(img_b64)
        out = run_inference_on_bgr(img_bgr)

        conf = float(out["max_conf"])
        visible = bool(out["visible"])

        # You can keep returning annotated (even if you hide in UI)
        annotated = encode_image_to_base64_jpeg(out["annotated_bgr"], quality=80)

        return JsonResponse({"conf": conf, "visible": visible, "annotated": annotated})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


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
