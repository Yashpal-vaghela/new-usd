import os
import json
import time
import uuid

from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from virtualsmileAI.forms import SmileDesignLeadForm
from django.utils import timezone
from virtualsmileAI.gemini import add_logo_on_right
from .yolo import decode_base64_image, run_inference_on_bgr, encode_image_to_base64_jpeg

THRESHOLD = getattr(settings, "TEETH_DETECTION_THRESHOLD", 0.65)

def smile(request):
    if request.method == "POST":
        form = SmileDesignLeadForm(request.POST)
        if form.is_valid():
            submission = form.save()
            return render(request, "virtual-smile-try-on.html", {
                "form": SmileDesignLeadForm(),
                "success": True
            })
        else:
            form = SmileDesignLeadForm()

            # current_datetime_ist = timezone.localtime(timezone.now())
            # formatted_datetime = current_datetime_ist.strftime("%d-%m-%Y %I:%M %p")
            # context_dict = {
            #     "Name":submission.name,
            #     "Phone":submission.phone,
            #     "City":submission.city,
            #     "Message":submission.message
            # }

    return render(request, "virtual-smile-try-on.html", {"threshold": THRESHOLD})

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


from .gemini import generate_smile_design

@csrf_exempt
def smile_design_api(request):
    """Accepts JSON {image: dataUrl/base64}. Saves before image, sends to Gemini, saves after, returns URLs."""
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
    os.makedirs(out_dir, exist_ok=True)
    ts = int(time.time())
    uid = uuid.uuid4().hex[:10]
    before_name = f"before_{ts}_{uid}.jpg"
    after_name = f"after_{ts}_{uid}.jpg"
    before_path = os.path.join(out_dir, before_name)
    after_path = os.path.join(out_dir, after_name)

    import cv2
    cv2.imwrite(before_path, img_bgr)
    
    add_logo_on_right(
        before_path,
        os.path.join(settings.MEDIA_ROOT, "logo", "usd-logo.png")
        )

    # Run Gemini (full image)
    try:
        generate_smile_design(before_path, after_path)
    except RuntimeError as e:
        # Not configured or no image returned
        msg = str(e)
        if "GEMINI_API_KEY" in msg or "not installed" in msg.lower() or "not configured" in msg.lower():
            return JsonResponse({"error": msg}, status=501)
        return JsonResponse({"error": msg}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    before_url = settings.MEDIA_URL + "smile_design/" + before_name
    after_url = settings.MEDIA_URL + "smile_design/" + after_name
    return JsonResponse({"before_url": before_url, "after_url": after_url, "ok": True})