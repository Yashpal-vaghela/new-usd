import os
import base64
import threading
from typing import Dict, Any, Optional

import numpy as np
import cv2
from django.conf import settings

try:
    from ultralytics import YOLO
except Exception:
    YOLO = None

MODEL = None
MODEL_LOCK = threading.Lock()

def _model_path() -> str:
    # detector/ml_models/best.pt (default)
    default_path = os.path.join(os.path.dirname(__file__), "ml_models", "best.pt")
    return getattr(settings, "TEETH_MODEL_PATH", default_path)

def load_model():
    """
    Lazily load Ultralytics YOLO model once per process.
    """
    global MODEL
    if YOLO is None:
        raise RuntimeError("ultralytics is not installed. Run: pip install ultralytics")
    if MODEL is not None:
        return MODEL
    with MODEL_LOCK:
        if MODEL is None:
            MODEL = YOLO(_model_path())
    return MODEL

def decode_base64_image(data_url_or_b64: str) -> np.ndarray:
    """
    Accepts either a data URL 'data:image/jpeg;base64,...' or raw base64.
    Returns BGR image (OpenCV).
    """
    if not data_url_or_b64:
        raise ValueError("Empty image")
    b64 = data_url_or_b64
    if "," in b64 and b64.strip().lower().startswith("data:"):
        b64 = b64.split(",", 1)[1]
    img_bytes = base64.b64decode(b64)
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image")
    return img

def encode_image_to_base64_jpeg(img_bgr: np.ndarray, quality: int = 85) -> str:
    """
    Encode BGR image to base64 JPEG data URL.
    """
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)]
    ok, buf = cv2.imencode(".jpg", img_bgr, encode_params)
    if not ok:
        raise ValueError("Could not encode image")
    b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
    return "data:image/jpeg;base64," + b64

def run_inference_on_bgr(img_bgr, conf_threshold=0.65):
    if conf_threshold is None:
        conf_threshold = getattr(settings, 'TEETH_DETECTION_THRESHOLD', 0.65)
    conf_threshold = float(conf_threshold)

    model = load_model()
    results = model(img_bgr, conf=conf_threshold)

    if len(results) == 0:
        return {
            'max_conf': 0.0,
            'visible': False,
            'annotated_bgr': img_bgr,
            'mask_bgr': None
        }

    r = results[0]

    max_conf = 0.0
    try:
        if hasattr(r, 'boxes') and r.boxes is not None and len(r.boxes) > 0:
            confs = []
            for box in r.boxes:
                try:
                    confs.append(float(box.conf))
                except Exception:
                    pass
            if confs:
                max_conf = max(confs)
    except Exception:
        max_conf = 0.0

    visible = max_conf > conf_threshold

    try:
        annotated = r.plot()              
        annotated_bgr = cv2.cvtColor(annotated, cv2.COLOR_RGB2BGR)
    except Exception:
        annotated_bgr = img_bgr.copy()

    mask_bgr = None
    try:
        if hasattr(r, 'masks') and r.masks is not None:
            mask_arr = r.masks.data.cpu().numpy()
            if mask_arr.size > 0:
                combined = (mask_arr.any(axis=0).astype('uint8')) * 255
                mask_bgr = cv2.cvtColor(combined, cv2.COLOR_GRAY2BGR)
    except Exception:
        mask_bgr = None

    return {
        'max_conf': float(max_conf),
        'visible': bool(visible),
        'annotated_bgr': annotated_bgr,
        'mask_bgr': mask_bgr,
    }