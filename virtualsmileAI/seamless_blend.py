import os
import threading
from typing import Optional

import cv2
import numpy as np

# Global model singletons
_BISENET_SESSION = None
_BISENET_FAILED = False
_BISENET_LOCK = threading.Lock()
_MP_DETECTOR = None
_MP_FAILED = False
_MP_LOCK = threading.Lock()
_YOLO_MODEL = None
_YOLO_LOCK = threading.Lock()

# Inner lip landmark indices from MediaPipe 468/478 Face Mesh
# Forms the closed polygon of the oral aperture
INNER_LIP_INDICES = [
    78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308,  # Upper inner lip
    324, 318, 402, 317, 14, 87, 178, 88, 95            # Lower inner lip
]


def _get_ml_dir() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "ml_models")


def get_bisenet_model():
    """Lazily load BiSeNet ResNet-34 face-parsing ONNX model singleton."""
    global _BISENET_SESSION, _BISENET_FAILED
    if _BISENET_SESSION is not None:
        return _BISENET_SESSION
    if _BISENET_FAILED:
        return None

    with _BISENET_LOCK:
        if _BISENET_SESSION is not None:
            return _BISENET_SESSION
        if _BISENET_FAILED:
            return None

        model_path = os.path.join(_get_ml_dir(), "bisenet_resnet_34.onnx")
        if not os.path.isfile(model_path):
            _BISENET_FAILED = True
            return None
        try:
            import onnxruntime as ort
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 2
            opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            _BISENET_SESSION = ort.InferenceSession(model_path, sess_options=opts, providers=['CPUExecutionProvider'])
            print("[SeamlessLipLock] Loaded BiSeNet ResNet-34 semantic face parser successfully.")
        except Exception as e:
            _BISENET_FAILED = True
            print(f"[SeamlessLipLock] BiSeNet loader note: {e}")
            return None

    return _BISENET_SESSION


def get_face_landmarker():
    """Lazily load MediaPipe FaceLandmarker singleton."""
    global _MP_DETECTOR, _MP_FAILED
    if _MP_DETECTOR is not None:
        return _MP_DETECTOR
    if _MP_FAILED:
        return None

    with _MP_LOCK:
        if _MP_DETECTOR is not None:
            return _MP_DETECTOR
        if _MP_FAILED:
            return None

        model_path = os.path.join(_get_ml_dir(), "face_landmarker.task")
        if not os.path.isfile(model_path):
            _MP_FAILED = True
            return None
        try:
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision

            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                num_faces=1,
            )
            _MP_DETECTOR = vision.FaceLandmarker.create_from_options(options)
        except Exception as e:
            _MP_FAILED = True
            if "4551" in str(e):
                print(f"[SeamlessLipLock] MediaPipe native DLL blocked by Windows Smart App Control/Code Integrity ({e}). Running seamlessly with primary YOLO dental segmentation & lip-lock.")
            else:
                print(f"[SeamlessLipLock] MediaPipe loader note: {e}")
            return None

    return _MP_DETECTOR


def get_teeth_model():
    """Lazily load and cache Ultralytics YOLO teeth segmentation model singleton."""
    global _YOLO_MODEL
    if _YOLO_MODEL is not None:
        return _YOLO_MODEL

    with _YOLO_LOCK:
        if _YOLO_MODEL is None:
            model_path = os.path.join(_get_ml_dir(), "best.pt")
            if not os.path.isfile(model_path):
                return None
            try:
                from ultralytics import YOLO
                _YOLO_MODEL = YOLO(model_path)
            except Exception as e:
                print(f"[SeamlessLipLock] YOLO loader note: {e}")
                return None

    return _YOLO_MODEL


def _get_mask_from_yolo(img_bgr: np.ndarray, conf: float = 0.15) -> Optional[np.ndarray]:
    """Accurate teeth segmentation mask using local YOLO model."""
    model = get_teeth_model()
    if model is None or img_bgr is None:
        return None

    try:
        h, w = img_bgr.shape[:2]
        results = model(img_bgr, conf=conf, verbose=False)
        if not results or len(results) == 0:
            return None

        r = results[0]
        if hasattr(r, 'masks') and r.masks is not None and len(r.masks.data) > 0:
            mask_arr = r.masks.data.cpu().numpy()
            combined = (mask_arr.any(axis=0).astype('uint8')) * 255
            if combined.shape[:2] != (h, w):
                combined = cv2.resize(combined, (w, h), interpolation=cv2.INTER_NEAREST)

            # Filter out stray false detections on clothing, buttons, jewelry, or background far from mouth
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(combined)
            if num_labels > 2:
                largest_idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
                lx, ly, lw, lh, larea = stats[largest_idx]
                cleaned = np.zeros_like(combined)
                for i in range(1, num_labels):
                    cx, cy, cw, ch, area = stats[i]
                    vert_dist = abs((cy + ch / 2.0) - (ly + lh / 2.0))
                    horiz_dist = abs((cx + cw / 2.0) - (lx + lw / 2.0))
                    if vert_dist < max(90, int(lh * 1.8)) and horiz_dist < max(180, int(lw * 1.4)):
                        cleaned[labels == i] = 255
                combined = cleaned

            return combined
        return None
    except Exception as e:
        print(f"[SeamlessLipLock] YOLO detection note: {e}")
        return None


def _enforce_mask_boundary_box(
    mask: np.ndarray,
    y_top: int,
    y_bot: int,
    x_left: int,
    x_right: int,
    feather_px: int = 6,
) -> np.ndarray:
    """
    Hard-clips a float mask to a bounding box [y_top:y_bot, x_left:x_right]
    with a smooth linear feather ramp on all four sides so there is zero bleed
    outside the detected dental arch region.
    """
    h, w = mask.shape[:2]
    result = mask.copy()

    # Zero out everything strictly outside bounding box
    result[:max(0, y_top - feather_px), :] = 0.0
    result[min(h, y_bot + feather_px):, :] = 0.0
    result[:, :max(0, x_left - feather_px)] = 0.0
    result[:, min(w, x_right + feather_px):] = 0.0

    # Top feather ramp (y_top - feather_px  →  y_top)
    for dy in range(feather_px):
        row = y_top - feather_px + dy
        if 0 <= row < h:
            alpha = dy / float(max(feather_px, 1))
            result[row, :] = result[row, :] * alpha

    # Bottom feather ramp (y_bot  →  y_bot + feather_px)
    for dy in range(feather_px):
        row = y_bot + dy
        if 0 <= row < h:
            alpha = 1.0 - dy / float(max(feather_px, 1))
            result[row, :] = result[row, :] * alpha

    # Left feather ramp (x_left - feather_px  →  x_left)
    for dx in range(feather_px):
        col = x_left - feather_px + dx
        if 0 <= col < w:
            alpha = dx / float(max(feather_px, 1))
            result[:, col] = result[:, col] * alpha

    # Right feather ramp (x_right  →  x_right + feather_px)
    for dx in range(feather_px):
        col = x_right + dx
        if 0 <= col < w:
            alpha = 1.0 - dx / float(max(feather_px, 1))
            result[:, col] = result[:, col] * alpha

    return np.clip(result, 0.0, 1.0)


def _tooth_vs_lip_colour(
    img_bgr: np.ndarray,
    tooth_ref: np.ndarray,
    lip_ref: np.ndarray,
):
    """
    Per-patient LAB colour split between this patient's teeth and their lips/skin.
    Returns (tooth_like, lip_like) boolean maps, or (None, None) when the references are too
    small or the colours are not separable (e.g. very dark photo).
    """
    tooth_ref = tooth_ref > 0
    lip_ref = lip_ref > 0
    if np.count_nonzero(tooth_ref) < 30 or np.count_nonzero(lip_ref) < 30:
        return None, None

    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    L = lab[:, :, 0].astype(np.float32)
    A = lab[:, :, 1].astype(np.float32)
    lt, ll = float(np.median(L[tooth_ref])), float(np.median(L[lip_ref]))
    at, al = float(np.median(A[tooth_ref])), float(np.median(A[lip_ref]))
    dL, dA = lt - ll, al - at

    score = np.zeros(L.shape, dtype=np.float32)
    if abs(dL) > 5.0:
        score += (L - (lt + ll) / 2.0) / dL
    if dA > 3.0:
        score += ((at + al) / 2.0 - A) / dA
    if abs(dL) <= 5.0 and dA <= 3.0:
        return None, None

    tooth_like = score > 0.0
    lip_like = (A > (at + al) / 2.0 + 0.25 * dA) if dA > 3.0 else (score < -0.5)
    return tooth_like, lip_like


def _surrounding_ring(binary: np.ndarray, inner: int = 6, outer: int = 18) -> np.ndarray:
    """Band of pixels just outside a mouth mask (mostly lip/skin), used as the lip colour reference."""
    b = (binary > 0).astype(np.uint8)
    near = cv2.dilate(b, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * inner + 1, 2 * inner + 1)))
    far = cv2.dilate(b, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * outer + 1, 2 * outer + 1)))
    return (far > 0) & (near == 0)


def _outward_feather(binary: np.ndarray, w: int, grow_allowed: Optional[np.ndarray] = None) -> np.ndarray:
    """
    Fills holes, grows the mask slightly and feathers OUTWARD only: the mask is 1.0 over every
    original tooth pixel, so no rim of the original teeth survives the blend.
    With grow_allowed, growth only enters tooth-coloured pixels: it covers yellow enamel rims
    but never creeps onto the lip (that is what made the lower lip look lowered at the corners).
    """
    binary = (binary > 0).astype(np.uint8)
    cnts, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if cnts:
        cv2.drawContours(binary, cnts, -1, 1, -1)

    grow = max(3, min(8, int(round(w * 0.006))))
    if grow_allowed is not None:
        allowed = (grow_allowed > 0).astype(np.uint8)
        k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        for _ in range(grow):
            binary = binary | (cv2.dilate(binary, k3) & allowed)
        grow_px = 1
    else:
        grow_px = 2
    binary = cv2.dilate(binary, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * grow_px + 1, 2 * grow_px + 1)))

    # Smooth the outline: pixel-level colour decisions leave a zigzag edge along the lip that
    # shows up as a jagged cut on top of the teeth. A real lip line is a smooth curve.
    smooth_sigma = max(1.5, w * 0.0015)
    binary = (cv2.GaussianBlur(binary.astype(np.float32), (0, 0), smooth_sigma) > 0.5).astype(np.uint8)

    dist_out = cv2.distanceTransform(1 - binary, cv2.DIST_L2, 5)
    r = max(2.5, min(5.0, float(w) * 0.003))
    t = np.clip(1.0 - dist_out / r, 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def get_side_fade_mask(img_bgr: np.ndarray, margin_px: int = 6, feather_px: int = 10, yolo_teeth: Optional[np.ndarray] = None) -> np.ndarray:
    """
    Computes a 2-D attenuation mask (values 0-1) that fades smoothly to 0.0 outside the
    patient's actual dental arch footprint on LEFT, RIGHT, TOP and BOTTOM.
    Guarantees 0% bleed on all four boundaries.
    """
    h, w = img_bgr.shape[:2]
    side_fade = np.ones((h, w), dtype=np.float32)
    if yolo_teeth is None:
        yolo_teeth = _get_mask_from_yolo(img_bgr)

    if yolo_teeth is not None and np.sum(yolo_teeth > 0) > 50:
        ys, xs = np.where(yolo_teeth > 0)
        x_min, x_max = int(np.min(xs)), int(np.max(xs))
        y_min, y_max = int(np.min(ys)), int(np.max(ys))
        teeth_w = x_max - x_min
        teeth_h = y_max - y_min

        # Scale margin with arch size — tighter on small arches
        eff_margin_x = max(margin_px, int(teeth_w * 0.03))
        eff_margin_y = max(margin_px, int(teeth_h * 0.04))

        # ── LEFT boundary ───────────────────────────────────────────────────────
        x_left_hard = max(0, x_min - eff_margin_x)
        x_left_feather_start = max(0, x_left_hard - feather_px)
        side_fade[:, :x_left_feather_start] = 0.0
        for x in range(x_left_feather_start, x_left_hard):
            side_fade[:, x] = (x - x_left_feather_start) / float(max(feather_px, 1))
        # hard zero left of arch
        side_fade[:, :x_left_feather_start] = 0.0

        # ── RIGHT boundary ──────────────────────────────────────────────────────
        x_right_hard = min(w, x_max + eff_margin_x)
        x_right_feather_end = min(w, x_right_hard + feather_px)
        side_fade[:, x_right_feather_end:] = 0.0
        for x in range(x_right_hard, x_right_feather_end):
            side_fade[:, x] = 1.0 - (x - x_right_hard) / float(max(feather_px, 1))

        # ── TOP boundary (prevent bleed above upper lip) ─────────────────────
        y_top_hard = max(0, y_min - eff_margin_y)
        y_top_feather_start = max(0, y_top_hard - feather_px)
        side_fade[:y_top_feather_start, :] = 0.0
        for y in range(y_top_feather_start, y_top_hard):
            side_fade[y, :] = (y - y_top_feather_start) / float(max(feather_px, 1))

        # ── BOTTOM boundary (prevent bleed into chin/neck) ───────────────────
        y_bot_hard = min(h, y_max + eff_margin_y)
        y_bot_feather_end = min(h, y_bot_hard + feather_px)
        side_fade[y_bot_feather_end:, :] = 0.0
        for y in range(y_bot_hard, y_bot_feather_end):
            side_fade[y, :] = 1.0 - (y - y_bot_hard) / float(max(feather_px, 1))

    return side_fade


def _get_mask_from_mediapipe(img_bgr: np.ndarray, before_path: Optional[str] = None) -> Optional[np.ndarray]:
    """
    Extracts the oral aperture polygon using MediaPipe FaceLandmarker.
    Captures oral aperture opening covering visible teeth.
    """
    detector = get_face_landmarker()
    if detector is None:
        return None

    try:
        import mediapipe as mp
        h, w = img_bgr.shape[:2]

        if before_path and os.path.isfile(before_path):
            mp_img = mp.Image.create_from_file(before_path)
        else:
            # Create from RGB numpy array
            rgb_img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_img)

        detection_result = detector.detect(mp_img)
        if not detection_result.face_landmarks:
            return None

        landmarks = detection_result.face_landmarks[0]
        pts = []
        for idx in INNER_LIP_INDICES:
            lm = landmarks[idx]
            px = int(np.clip(lm.x * w, 0, w - 1))
            py = int(np.clip(lm.y * h, 0, h - 1))
            pts.append([px, py])

        pts_arr = np.array(pts, dtype=np.int32)
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [pts_arr], 255)
        return mask
    except Exception as e:
        print(f"[SeamlessLipLock] MediaPipe detection note: {e}")
        return None


def _get_mask_from_bisenet(
    b_img: np.ndarray,
    a_img: Optional[np.ndarray] = None,
    before_path: Optional[str] = None,
    feather_kernel_size: int = 11,
    feather_sigma: float = 2.5,
) -> Optional[np.ndarray]:
    """
    Sub-pixel Continuous BiSeNet ResNet-34 Face-Parsing + Color-Adaptive Boundary:
    1. Extracts continuous softmax probability fields at 512x512 and upsamples with
       smooth bilinear interpolation to camera resolution (eliminates blocky staircases).
    2. Uses patient's real lip chroma (LAB a* channel) and YOLO ground-truth enamel to
       dynamically snap to the true anatomical lip border.
    3. Employs signed distance fields for continuous Hermite smoothstep feathering:
       Eliminates all hard boolean cliff cuts, scratches, and artificial artifacts.
    """
    session = get_bisenet_model()
    if session is None or b_img is None:
        return None

    try:
        h, w = b_img.shape[:2]
        rgb = cv2.cvtColor(b_img, cv2.COLOR_BGR2RGB)

        # Ground-truth teeth from YOLO (anchored on genuine enamel across both b_img and a_img)
        yb = _get_mask_from_yolo(b_img, conf=0.10)
        ya = _get_mask_from_yolo(a_img, conf=0.10) if a_img is not None else None
        if yb is not None and ya is not None:
            yolo_enamel = cv2.bitwise_or(yb, ya)
        else:
            yolo_enamel = yb if yb is not None else ya

        has_yolo_teeth = yolo_enamel is not None and np.sum(yolo_enamel > 0) > 40

        def _parse(x0: int, y0: int, x1: int, y1: int):
            crop = cv2.resize(rgb[y0:y1, x0:x1], (512, 512), interpolation=cv2.INTER_LINEAR)
            tensor = crop.astype(np.float32) / 255.0
            mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
            std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
            tensor = (tensor - mean) / std
            tensor = np.transpose(tensor, (2, 0, 1))[np.newaxis, ...]

            logits = session.run(['output'], {'input': tensor})[0][0]  # (19, 512, 512)

            # Softmax for smooth continuous probabilities across classes
            exp_logits = np.exp(logits - np.max(logits, axis=0, keepdims=True))
            probs = exp_logits / np.sum(exp_logits, axis=0, keepdims=True)

            # Class 11: oral cavity, 12: upper lip, 13: lower lip.
            # Smooth sub-pixel resize back into the crop's place in the full frame.
            def up(p):
                full = np.zeros((h, w), dtype=np.float32)
                full[y0:y1, x0:x1] = cv2.resize(p, (x1 - x0, y1 - y0), interpolation=cv2.INTER_LINEAR)
                return full
            return up(probs[11]), up(probs[12]), up(probs[13])

        # Parse a face-sized square around the mouth at its true aspect ratio. Squashing the
        # whole frame to 512x512 shrinks the mouth to ~100px and blurs the lip line by 2-4px,
        # which is worst on angled/side photos. Same single inference, ~2x more mouth detail.
        p_mouth = None
        if has_yolo_teeth:
            ys_y, xs_y = np.where(yolo_enamel > 0)
            side = int(min(max(h, w), max(256, 3.5 * (xs_y.max() - xs_y.min()))))
            cx = int((xs_y.min() + xs_y.max()) / 2)
            cy = int((ys_y.min() + ys_y.max()) / 2 - 0.2 * side)  # mouth sits ~70% down a face crop
            x0 = int(np.clip(cx - side // 2, 0, max(0, w - side)))
            y0 = int(np.clip(cy - side // 2, 0, max(0, h - side)))
            p_mouth, p_upper_lip, p_lower_lip = _parse(x0, y0, min(w, x0 + side), min(h, y0 + side))
            if np.sum(p_mouth > 0.28) < 50:
                p_mouth = None  # crop missed the mouth (stray YOLO hit) -> parse full frame
        if p_mouth is None:
            p_mouth, p_upper_lip, p_lower_lip = _parse(0, 0, w, h)
        p_lips = p_upper_lip + p_lower_lip

        # Optical lip chroma discrimination using LAB color space
        # Lips have prominent magenta/red chroma (a* > 132 in 8-bit LAB)
        # Teeth enamel is neutral (a* ~ 126-132) with higher lightness
        lab = cv2.cvtColor(b_img, cv2.COLOR_BGR2LAB)
        a_ch = lab[:, :, 1].astype(np.float32)
        chroma_lip = np.clip((a_ch - 132.0) / 12.0, 0.0, 1.0)

        # Combined lip confidence: model agreement + optical color confirmation from input image
        lip_confidence = np.clip(p_lips * (0.60 + 0.40 * chroma_lip), 0.0, 1.0)

        # Oral cavity core: high mouth probability OR confirmed YOLO enamel from input image
        if has_yolo_teeth:
            mouth_seed = (p_mouth > 0.28) | (yolo_enamel > 0)
        else:
            mouth_seed = (p_mouth > 0.40)

        # Teeth opening: mouth cavity minus confirmed lip tissue
        teeth_binary = (mouth_seed & (lip_confidence < 0.60)).astype(np.uint8)

        # LIP EXCLUSION: only where lip clearly beats mouth (low thresholds ate the outer
        # 3-8px of real teeth after 512px upsampling, leaving original enamel visible)
        teeth_binary[(p_upper_lip > 0.60) & (p_upper_lip > p_mouth)] = 0
        teeth_binary[(p_lower_lip > 0.60) & (p_lower_lip > p_mouth)] = 0

        # Patient-specific teeth/lip colour split: drop lip-coloured pixels on the lip border
        # (keeps the real lip line, incl. the thin corners) and let the mask grow only into
        # tooth-coloured rims later.
        tooth_ref = (yolo_enamel > 0) if has_yolo_teeth else ((p_mouth > 0.6) & (lip_confidence < 0.2))
        tooth_like, lip_like = _tooth_vs_lip_colour(b_img, tooth_ref, p_lips > 0.7)
        if lip_like is not None:
            border = (p_lips > 0.30) & lip_like
            if has_yolo_teeth:
                border &= ~(yolo_enamel > 0)
            teeth_binary[border] = 0

        # Mouth-opening extent from the face parser (used so YOLO misses can't cut the mask)
        ys_m, xs_m = np.where(p_mouth > 0.28)
        mouth_ext = (int(ys_m.min()), int(ys_m.max()), int(xs_m.min()), int(xs_m.max())) if len(ys_m) > 50 else None

        # Landmark Perimeter Lock: If MediaPipe detects the patient's oral aperture on b_img,
        # confine the mask strictly within the oral aperture, preserving 100% of upper & lower lips.
        mp_aperture = _get_mask_from_mediapipe(b_img, before_path=before_path)
        ap_x_left, ap_x_right = None, None
        ap_y_top, ap_y_bot = None, None

        if mp_aperture is not None and np.sum(mp_aperture > 0) > 40:
            ys_ap, xs_ap = np.where(mp_aperture > 0)
            if len(ys_ap) > 50:
                ap_y_top = int(np.min(ys_ap))
                ap_y_bot = int(np.max(ys_ap))
                ap_x_left = int(np.min(xs_ap))
                ap_x_right = int(np.max(xs_ap))
                ap_height = ap_y_bot - ap_y_top

                # STRICT upper lip lock: NO upward expansion into upper lip!
                mp_allowed_zone = mp_aperture.copy()
                mp_allowed_zone[:ap_y_top, :] = 0

                # HARD bottom lock: zero out any allowed zone below aperture bottom + small margin
                bottom_lock_row = min(h, ap_y_bot + max(4, int(ap_height * 0.06)))
                mp_allowed_zone[bottom_lock_row:, :] = 0

                # Allow full horizontal mouth opening width (corner to corner)
                left_lock_col = max(0, ap_x_left - max(15, int((ap_x_right - ap_x_left) * 0.08)))
                right_lock_col = min(w, ap_x_right + max(15, int((ap_x_right - ap_x_left) * 0.08)))
                mp_allowed_zone[:, :left_lock_col] = 0
                mp_allowed_zone[:, right_lock_col:] = 0

            # Confine teeth_binary inside mp_allowed_zone
            teeth_binary = (teeth_binary & (mp_allowed_zone > 0)).astype(np.uint8)

        # Compute YOLO-based bounding box spanning full oral aperture
        yolo_bbox = None
        if yolo_enamel is not None and np.sum(yolo_enamel > 0) > 40:
            ys_y, xs_y = np.where(yolo_enamel > 0)
            yolo_bl = int(np.min(xs_y))
            yolo_br = int(np.max(xs_y))
            if ap_x_left is not None:
                yolo_bl = min(yolo_bl, ap_x_left)
                yolo_br = max(yolo_br, ap_x_right)
            y_top_yolo = int(np.min(ys_y))
            if ap_y_top is not None:
                y_top_yolo = max(y_top_yolo, ap_y_top)
            yolo_bbox = (
                y_top_yolo, int(np.max(ys_y)),   # y_top, y_bot
                yolo_bl, yolo_br,                 # x_left, x_right
            )

        # Anatomical column lock on teeth_binary
        ys_teeth, xs_teeth = np.where(teeth_binary > 0)
        teeth_bbox = None
        if len(ys_teeth) > 50:
            y_top_tb = int(np.min(ys_teeth))
            y_bot_tb = int(np.max(ys_teeth))
            x_left_tb = int(np.min(xs_teeth))
            x_right_tb = int(np.max(xs_teeth))
            tb_height = y_bot_tb - y_top_tb

            eff_left = x_left_tb
            eff_right = x_right_tb
            if ap_x_left is not None:
                eff_left = min(eff_left, ap_x_left)
            if ap_x_right is not None:
                eff_right = max(eff_right, ap_x_right)
            if yolo_enamel is not None and np.sum(yolo_enamel > 0) > 0:
                ys_ye, xs_ye = np.where(yolo_enamel > 0)
                eff_left = min(eff_left, int(np.min(xs_ye)))
                eff_right = max(eff_right, int(np.max(xs_ye)))

            if mouth_ext is not None:
                y_bot_tb = max(y_bot_tb, mouth_ext[1])
                eff_left = min(eff_left, mouth_ext[2])
                eff_right = max(eff_right, mouth_ext[3])
                tb_height = y_bot_tb - y_top_tb

            eff_top = max(y_top_tb, ap_y_top) if ap_y_top is not None else y_top_tb
            teeth_bbox = (eff_top, y_bot_tb, eff_left, eff_right)

            # STRICT top lock: NO upward dilation into upper lip!
            if ap_y_top is not None:
                teeth_binary[:ap_y_top, :] = 0

            # STRICT bottom row lock: anything below bottom + 5% of height is noise → zero
            hard_bot = min(h, y_bot_tb + max(3, int(tb_height * 0.05)))
            teeth_binary[hard_bot:, :] = 0

            # Left/right column lock: eff_left/right already span the parser's full mouth opening,
            # so a small margin is enough (a wide one let Gemini's corners replace the real ones)
            arch_w = eff_right - eff_left
            hard_left = max(0, eff_left - max(8, int(arch_w * 0.04)))
            hard_right = min(w, eff_right + max(8, int(arch_w * 0.04)))
            teeth_binary[:, :hard_left] = 0
            teeth_binary[:, hard_right:] = 0

        # Clean isolated noise blobs; keep all components with significant area inside mouth
        if np.sum(teeth_binary > 0) < 40:
            return None

        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(teeth_binary)
        if num_labels > 2:
            clean_mask = np.zeros_like(teeth_binary)
            for i in range(1, num_labels):
                if stats[i, cv2.CC_STAT_AREA] >= 20:
                    clean_mask[labels == i] = 1
            teeth_binary = clean_mask

        # Morphological close to seal interdental shadows and small gaps
        k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        teeth_binary = cv2.morphologyEx(teeth_binary, cv2.MORPH_CLOSE, k_close)

        # Upper-lip band: right under the upper lip only replace pixels that were tooth in the
        # original. Otherwise Gemini's upper teeth climb into the dark band under the lip and the
        # teeth look moved up / the lip looks moved.
        if tooth_like is not None and np.any(teeth_binary):
            ys_t = np.where(teeth_binary > 0)[0]
            band_h = max(3, int((ys_t.max() - ys_t.min()) * 0.15))
            top_band = (np.cumsum(teeth_binary, axis=0) <= band_h) & (teeth_binary > 0) & (p_upper_lip > 0.10)
            keep = tooth_like | (yolo_enamel > 0) if has_yolo_teeth else tooth_like
            # Only drop pixels that are positively lip-coloured or dark (shadow band), never
            # merely "not tooth-like": pale lips vs grey teeth would otherwise notch real teeth.
            L_ch = lab[:, :, 0].astype(np.float32)
            tooth_L = float(np.median(L_ch[tooth_ref])) if np.any(tooth_ref) else float(np.median(L_ch[teeth_binary > 0]))
            dark = L_ch < 0.55 * tooth_L
            teeth_binary[top_band & ~keep & (lip_like | dark)] = 0

        # Whole opening covered, outward-only feather (no original-tooth rim)
        smooth_mask = _outward_feather(teeth_binary, w, grow_allowed=tooth_like)

        # Final 4-side boundary enforcement using full mouth aperture bbox
        bbox_ref = yolo_bbox or teeth_bbox
        if bbox_ref is not None:
            bt, bb, bl, br = bbox_ref
            if mouth_ext is not None:
                bb = max(bb, mouth_ext[1])
                bl = min(bl, mouth_ext[2])
                br = max(br, mouth_ext[3])
            if ap_x_left is not None:
                bl = min(bl, ap_x_left)
            if ap_x_right is not None:
                br = max(br, ap_x_right)
            if yolo_enamel is not None and np.sum(yolo_enamel > 0) > 0:
                ys_ye, xs_ye = np.where(yolo_enamel > 0)
                bl = min(bl, int(np.min(xs_ye)))
                br = max(br, int(np.max(xs_ye)))
            arch_h = max(bb - bt, 1)
            arch_w2 = max(br - bl, 1)
            y_top_clamp = max(ap_y_top, bt) if ap_y_top is not None else bt
            smooth_mask = _enforce_mask_boundary_box(
                smooth_mask,
                y_top=y_top_clamp,   # STRICT upper lip freeze - NEVER dilate or climb up into upper lip
                y_bot=min(h - 1, bb + max(4, int(arch_h * 0.05))),
                x_left=max(0, bl - max(8, int(arch_w2 * 0.04))),
                x_right=min(w - 1, br + max(8, int(arch_w2 * 0.04))),
                feather_px=6,
            )

        print(f"[SeamlessLipLock] Sub-pixel 4-side boundary-locked mask generated ({np.sum(smooth_mask > 0.05)} px).")
        return smooth_mask.astype(np.float32)

    except Exception as e:
        print(f"[SeamlessLipLock] Dynamic BiSeNet segmentation note: {e}")
        return None


def get_accurate_teeth_mask(
    b_img: np.ndarray,
    a_img: Optional[np.ndarray] = None,
    before_path: Optional[str] = None,
    binary: bool = False,
    dilate_px: int = 2,
    feather_kernel_size: int = 15,
    feather_sigma: float = 3.0,
) -> np.ndarray:
    """
    Produces the clinically accurate, coordinate-locked composite mask:
    1. Primary: BiSeNet ResNet-34 sub-pixel face parsing + color-adaptive boundary.
    2. Secondary: MediaPipe FaceLandmarker inner lip aperture + YOLO consensus with signed distance feathering.
    3. Tertiary: YOLO dental segmentation strictly constrained to patient's original anatomy.
    """
    h, w = b_img.shape[:2]

    try:
        # 1. Primary SOTA Face-Parsing: BiSeNet ResNet-34 Consensus Fusion
        bisenet_mask = _get_mask_from_bisenet(
            b_img=b_img,
            a_img=a_img,
            before_path=before_path,
            feather_kernel_size=feather_kernel_size,
            feather_sigma=feather_sigma,
        )
        if bisenet_mask is not None and np.sum(bisenet_mask > 0.05) > 50:
            if binary:
                return (bisenet_mask > 0.10).astype(np.uint8) * 255
            return bisenet_mask

        # 2. Secondary Dental Segmentation via YOLO (trained on dental photography)
        yb = _get_mask_from_yolo(b_img, conf=0.10)
        ya = _get_mask_from_yolo(a_img, conf=0.10) if a_img is not None else None
        if ya is not None and ya.shape[:2] != (h, w):
            ya = cv2.resize(ya, (w, h), interpolation=cv2.INTER_LINEAR)

        # Dental core: combine genuine enamel detections from both b_img and a_img
        k_tuck = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        if yb is not None and ya is not None:
            teeth_core = cv2.dilate(cv2.bitwise_or(yb, ya), k_tuck)
        elif yb is not None and np.sum(yb > 0) > 50:
            teeth_core = cv2.dilate(yb, k_tuck)
        elif ya is not None and np.sum(ya > 0) > 50:
            teeth_core = cv2.dilate(ya, k_tuck)
        else:
            teeth_core = None

        if teeth_core is not None:
            cnts, _ = cv2.findContours(teeth_core, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            clean_teeth = np.zeros_like(teeth_core)
            if cnts:
                cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
                max_area = cv2.contourArea(cnts[0])
                for c in cnts:
                    if cv2.contourArea(c) > max(150, max_area * 0.05):
                        cv2.drawContours(clean_teeth, [c], -1, 255, -1)
            teeth_core = clean_teeth

        # Extract MediaPipe inner lip aperture polygon (if full face detected)
        detector = get_face_landmarker()
        aperture_poly = None

        if detector is not None:
            try:
                import mediapipe as mp
                if before_path and os.path.isfile(before_path):
                    mp_img = mp.Image.create_from_file(before_path)
                else:
                    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(b_img, cv2.COLOR_BGR2RGB))
                res = detector.detect(mp_img)
                if res.face_landmarks:
                    lms = res.face_landmarks[0]
                    pts = [[int(np.clip(lms[idx].x * w, 0, w - 1)), int(np.clip(lms[idx].y * h, 0, h - 1))] for idx in INNER_LIP_INDICES]
                    aperture_poly = np.zeros((h, w), dtype=np.uint8)
                    cv2.fillPoly(aperture_poly, [np.array(pts, dtype=np.int32)], 1)
            except Exception as mp_err:
                pass

        if aperture_poly is not None:
            combined_binary = aperture_poly.copy()
            if teeth_core is not None:
                combined_binary = cv2.bitwise_or(combined_binary, (teeth_core > 0).astype(np.uint8))

            # Compute bounding box for 4-side lock
            ys_cb, xs_cb = np.where(combined_binary > 0)
            cb_bbox = None
            if len(ys_cb) > 50:
                y_top = int(np.min(ys_cb))
                y_bot = int(np.max(ys_cb))
                x_left = int(np.min(xs_cb))
                x_right = int(np.max(xs_cb))
                cb_height = y_bot - y_top
                cb_width = x_right - x_left
                cb_bbox = (y_top, y_bot, x_left, x_right)

                # Hard bottom lock
                hard_bot = min(h, y_bot + max(3, int(cb_height * 0.05)))
                combined_binary[hard_bot:, :] = 0

                # Left/right column lock: generous margin so corner teeth are NEVER clipped
                hard_left = max(0, x_left - max(15, int(cb_width * 0.08)))
                hard_right = min(w, x_right + max(15, int(cb_width * 0.08)))
                combined_binary[:, :hard_left] = 0
                combined_binary[:, hard_right:] = 0

            tooth_like, _ = _tooth_vs_lip_colour(
                b_img,
                teeth_core if teeth_core is not None else combined_binary,
                _surrounding_ring(combined_binary),
            )
            final_mask = _outward_feather(combined_binary, w, grow_allowed=tooth_like)

            # Apply 4-side boundary box clamp
            if cb_bbox is not None:
                bt, bb, bl, br = cb_bbox
                ah = max(bb - bt, 1)
                aw = max(br - bl, 1)
                final_mask = _enforce_mask_boundary_box(
                    final_mask,
                    y_top=bt,   # Strict upper lip lock
                    y_bot=min(h - 1, bb + max(3, int(ah * 0.05))),
                    x_left=max(0, bl - max(15, int(aw * 0.08))),
                    x_right=min(w - 1, br + max(15, int(aw * 0.08))),
                    feather_px=6,
                )

        elif teeth_core is not None:
            teeth_binary = (teeth_core > 0).astype(np.uint8)
            ys_tb, xs_tb = np.where(teeth_binary > 0)
            tc_bbox = None
            if len(ys_tb) > 50:
                y_top = int(np.min(ys_tb))
                y_bot = int(np.max(ys_tb))
                x_left = int(np.min(xs_tb))
                x_right = int(np.max(xs_tb))
                tc_height = y_bot - y_top
                tc_width = x_right - x_left
                tc_bbox = (y_top, y_bot, x_left, x_right)

                # Hard bottom/left/right lock
                hard_bot = min(h, y_bot + max(3, int(tc_height * 0.05)))
                teeth_binary[hard_bot:, :] = 0
                hard_left = max(0, x_left - max(15, int(tc_width * 0.08)))
                hard_right = min(w, x_right + max(15, int(tc_width * 0.08)))
                teeth_binary[:, :hard_left] = 0
                teeth_binary[:, hard_right:] = 0

            tooth_like, _ = _tooth_vs_lip_colour(b_img, teeth_binary, _surrounding_ring(teeth_binary))
            final_mask = _outward_feather(teeth_binary, w, grow_allowed=tooth_like)

            if tc_bbox is not None:
                bt, bb, bl, br = tc_bbox
                ah = max(bb - bt, 1)
                aw = max(br - bl, 1)
                final_mask = _enforce_mask_boundary_box(
                    final_mask,
                    y_top=bt,   # Strict upper lip lock
                    y_bot=min(h - 1, bb + max(3, int(ah * 0.05))),
                    x_left=max(0, bl - max(15, int(aw * 0.08))),
                    x_right=min(w - 1, br + max(15, int(aw * 0.08))),
                    feather_px=6,
                )
        else:
            return np.zeros((h, w), dtype=np.uint8 if binary else np.float32)

        final_mask = np.clip(final_mask, 0.0, 1.0)

        if binary:
            return (final_mask > 0.10).astype(np.uint8) * 255
        return final_mask

    except Exception as e:
        print(f"[AccurateTeethMask Note]: {e}")
        return np.zeros((h, w), dtype=np.uint8 if binary else np.float32)


def detect_bite_space_line(
    img_bgr: np.ndarray,
    before_path: Optional[str] = None,
    cached_mask: Optional[np.ndarray] = None,
    cached_mask_float: Optional[np.ndarray] = None,
) -> dict:
    """
    Scans the patient's oral aperture and dental arch geometry to deterministically determine:
    1. If lower teeth exist (dual arch vs single upper arch).
    2. If a dark horizontal inter-arch space line / bite gap exists between top and bottom teeth.
    3. If teeth meet in touching edge-to-edge contact.
    
    Returns a dictionary with geometric bite metrics and detected flags.
    """
    default_res = {
        "status": "fallback",
        "bottom_teeth_exist": False,
        "has_space_line": False,
        "is_touching_bite": False,
        "is_closed_smile": False,
        "valley_y": None,
        "valley_val": None,
        "top_peak": None,
        "bot_peak": None,
        "ymin": None,
        "ymax": None,
        "xmin": None,
        "xmax": None,
        "cached_mask": None,
        "cached_mask_float": None,
    }
    if img_bgr is None:
        return default_res

    h, w = img_bgr.shape[:2]

    try:
        if cached_mask is not None:
            mask = cached_mask
            mask_float = cached_mask_float if cached_mask_float is not None else (mask > 0).astype(np.float32)
        else:
            mask_float = get_accurate_teeth_mask(b_img=img_bgr, a_img=img_bgr, before_path=before_path, binary=False)
            mask = (mask_float > 0.10).astype(np.uint8) * 255 if mask_float is not None else None

        if mask is None or np.sum(mask > 0) < 50:
            return {
                "status": "closed_smile",
                "bottom_teeth_exist": False,
                "has_space_line": False,
                "is_touching_bite": False,
                "is_closed_smile": True,
                "valley_y": None,
                "valley_val": None,
                "top_peak": None,
                "bot_peak": None,
                "ymin": None,
                "ymax": None,
                "xmin": None,
                "xmax": None,
                "cached_mask": mask,
                "cached_mask_float": mask_float,
            }

        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        ys, xs = np.where(mask > 0)
        ymin, ymax = int(np.min(ys)), int(np.max(ys))
        xmin, xmax = int(np.min(xs)), int(np.max(xs))

        span_y = ymax - ymin
        if span_y < 12:
            return {
                "status": "closed_smile",
                "bottom_teeth_exist": False,
                "has_space_line": False,
                "is_touching_bite": False,
                "is_closed_smile": True,
                "valley_y": None,
                "valley_val": None,
                "top_peak": None,
                "bot_peak": None,
                "ymin": ymin,
                "ymax": ymax,
                "xmin": xmin,
                "xmax": xmax,
                "cached_mask": mask,
                "cached_mask_float": mask_float,
            }

        # Analyze central 60% of the dental arch width (incisor region)
        cx1 = int(xmin + (xmax - xmin) * 0.20)
        cx2 = int(xmin + (xmax - xmin) * 0.80)

        row_means = []
        for y in range(ymin, ymax + 1):
            row_pixels = gray[y, cx1:cx2]
            row_mask = mask[y, cx1:cx2] > 0
            if np.any(row_mask):
                row_means.append((y, float(np.mean(row_pixels[row_mask]))))
            else:
                row_means.append((y, float(np.mean(row_pixels))))

        if len(row_means) < 12:
            return default_res

        profile = np.array([m[1] for m in row_means])
        ys_arr = np.array([m[0] for m in row_means])
        L = len(profile)

        # 1. Top peak is in the upper 50%
        top_peak_idx = int(np.argmax(profile[: int(L * 0.50)]))
        top_peak = float(profile[top_peak_idx])
        top_y = ys_arr[top_peak_idx]

        # 2. Valley must be strictly BELOW top peak
        search_end = min(L - 2, int(L * 0.88))
        if search_end > top_peak_idx + 2:
            rel_v = int(np.argmin(profile[top_peak_idx + 2 : search_end]))
            valley_idx = top_peak_idx + 2 + rel_v
        else:
            valley_idx = int(L * 0.50)
        valley_val = float(profile[valley_idx])
        valley_y = ys_arr[valley_idx]

        # 3. Bottom peak must be strictly BELOW the valley
        if valley_idx < L - 2:
            bot_search = profile[valley_idx + 1 :]
            bot_rel = int(np.argmax(bot_search))
            bot_idx = valley_idx + 1 + bot_rel
            bot_peak = float(profile[bot_idx])
            bot_y = ys_arr[bot_idx]
        else:
            bot_peak = 0.0
            bot_y = ymax

        lower_arch_height = ymax - valley_y
        lower_ratio = lower_arch_height / max(1, span_y)
        # 4. Accurate Dual-Arch vs Single-Arch Discrimination:
        # A true dual arch has:
        # a) A distinct top peak (upper teeth),
        # b) A distinct incisal valley / dark space below the top peak,
        # c) A distinct second peak (lower teeth) strictly below the valley with genuine elevation,
        # d) A genuine vertical separation: valley_drop >= 12.0 and lower_arch_height >= 14.
        valley_drop = min(top_peak - valley_val, bot_peak - valley_val)
        peak_dist_y = abs(bot_y - top_y)

        # Check YOLO for genuine enamel detections strictly in the lower region below the detected valley
        yb_detect = _get_mask_from_yolo(img_bgr, conf=0.10)
        yolo_bot_px = 0
        if yb_detect is not None and valley_y is not None:
            lower_split = max(valley_y + 2, ymin + int(span_y * 0.50))
            if lower_split < ymax:
                yolo_bot_px = int(np.sum(yb_detect[lower_split:ymax, xmin:xmax] > 0))

        # Bottom teeth exist ONLY when there is clear physical and optical proof of a second arch:
        # 1. Distinct two peaks separated by a valley (valley_drop >= 12.0 and peak_dist >= 12px)
        # 2. Or strong YOLO enamel detection in the lower half AND a discernible valley separating them
        has_dual_peak = bool(
            (valley_drop >= 12.0)
            and (peak_dist_y >= 10)
            and (bot_peak > 65.0)
            and (lower_arch_height >= 12)
            and (lower_ratio >= 0.20)
        )
        has_yolo_lower = bool(
            (yolo_bot_px >= 80)
            and (valley_drop >= 8.0)
            and (peak_dist_y >= 10)
            and (lower_arch_height >= 12)
        )

        bottom_teeth_exist = bool(has_dual_peak or has_yolo_lower)

        # Criteria: Genuine open bite space line: Must be dark oral cavity shadow (valley_val < 78.0) AND deep drop (> 30.0 below peaks)
        # Width of the dark dip relative to the upper-to-lower peak distance (scale-free).
        # A touching bite still has a dark contact line, but it is narrow (ratio ~0.2-0.28);
        # a real open bite gap is wide (~0.4). Without this a dark contact line was called
        # "open" and Gemini opened a gap and pushed the lower teeth down.
        bot_i = bot_idx if valley_idx < L - 2 else L - 1
        half_level = valley_val + 0.5 * max(min(top_peak, bot_peak) - valley_val, 1.0)
        lo = valley_idx
        while lo > top_peak_idx and profile[lo - 1] < half_level:
            lo -= 1
        hi = valley_idx
        while hi < bot_i and profile[hi + 1] < half_level:
            hi += 1
        gap_rows = hi - lo + 1
        gap_ratio = gap_rows / float(max(1, bot_i - top_peak_idx))

        has_space_line = bool(
            bottom_teeth_exist
            and (valley_val < 85.0)
            and (valley_val < top_peak - 28.0)
            and (valley_val < bot_peak - 25.0)
            and (gap_ratio >= 0.33)
            and (gap_rows >= 5)
        )
        # Touching bite / closed bite: Upper and lower teeth touch in continuous contact
        is_touching_bite = bool(bottom_teeth_exist and not has_space_line)

        print(f"[DetectBite] bottom_teeth={bottom_teeth_exist}, space_line={has_space_line}, touching={is_touching_bite}, valley_y={valley_y} (val={valley_val:.1f} vs top={top_peak:.1f}, bot={bot_peak:.1f}, drop={valley_drop:.1f}, gap={gap_rows}px ratio={gap_ratio:.2f})")

        return {
            "status": "ok",
            "bottom_teeth_exist": bool(bottom_teeth_exist),
            "has_space_line": bool(has_space_line),
            "is_touching_bite": bool(is_touching_bite),
            "is_closed_smile": False,
            "valley_y": valley_y,
            "valley_val": valley_val,
            "top_peak": top_peak,
            "bot_peak": bot_peak,
            "ymin": ymin,
            "ymax": ymax,
            "xmin": xmin,
            "xmax": xmax,
            "cached_mask": mask,
            "cached_mask_float": mask_float,
        }
    except Exception as e:
        print(f"[DetectBite Note]: {e}")
        return default_res


def align_after_to_before(
    b_img: np.ndarray,
    a_img: np.ndarray,
    exclude_mask: Optional[np.ndarray] = None,
    max_dim: int = 768,
) -> np.ndarray:
    """
    Registers Gemini's output onto the original photo (affine ECC on the face, mouth excluded).
    Gemini often returns a slightly reframed/rescaled image, which makes the generated teeth
    sit lower/higher than the original mouth opening and the mask appear to "slide".
    """
    h, w = b_img.shape[:2]
    if a_img.shape[:2] != (h, w):
        a_img = cv2.resize(a_img, (w, h), interpolation=cv2.INTER_LANCZOS4)

    s = min(1.0, max_dim / float(max(h, w)))
    sw, sh = max(1, int(w * s)), max(1, int(h * s))
    bg = cv2.GaussianBlur(cv2.cvtColor(cv2.resize(b_img, (sw, sh)), cv2.COLOR_BGR2GRAY), (5, 5), 0).astype(np.float32)
    ag = cv2.GaussianBlur(cv2.cvtColor(cv2.resize(a_img, (sw, sh)), cv2.COLOR_BGR2GRAY), (5, 5), 0).astype(np.float32)

    # Ignore the mouth itself (it is supposed to change) when estimating the alignment
    in_mask = np.full((sh, sw), 255, dtype=np.uint8)
    if exclude_mask is not None and np.any(exclude_mask > 0):
        em = cv2.resize((exclude_mask > 0).astype(np.uint8) * 255, (sw, sh), interpolation=cv2.INTER_NEAREST)
        k = max(9, int(sw * 0.03)) | 1
        em = cv2.dilate(em, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        in_mask[em > 0] = 0

    warp = np.eye(2, 3, dtype=np.float32)
    try:
        criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 80, 1e-5)
        _, warp = cv2.findTransformECC(bg, ag, warp, cv2.MOTION_AFFINE, criteria, in_mask, 5)
    except cv2.error as e:
        print(f"[SeamlessLipLock] Alignment skipped (ECC did not converge): {e}")
        return a_img

    # Sanity check: reject implausible warps (keep raw image instead of distorting it)
    scale_x = float(np.hypot(warp[0, 0], warp[1, 0]))
    scale_y = float(np.hypot(warp[0, 1], warp[1, 1]))
    warp[:, 2] /= s
    shift = float(np.hypot(warp[0, 2], warp[1, 2]))
    if not (0.85 < scale_x < 1.15 and 0.85 < scale_y < 1.15) or shift > 0.10 * max(h, w):
        print(f"[SeamlessLipLock] Alignment rejected (scale={scale_x:.3f}/{scale_y:.3f}, shift={shift:.1f}px).")
        return a_img

    print(f"[SeamlessLipLock] Aligned AI output to original (dx={warp[0, 2]:.1f}, dy={warp[1, 2]:.1f}, scale={scale_x:.3f}/{scale_y:.3f}).")
    return cv2.warpAffine(
        a_img, warp, (w, h),
        flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_REPLICATE,
    )


def preserve_space_line_shadow(
    b_img: np.ndarray,
    a_img: np.ndarray,
    bite_info: Optional[dict] = None,
) -> np.ndarray:
    """
    Per user directive: If there is a gap between top and bottom line, fill it, and even if only 2 teeth
    attach, count as a connected whole smile. Never darken or burn artificial dark notches onto teeth.
    """
    return a_img


def apply_seamless_lip_lock(
    before_path: str,
    after_path: str,
    output_path: Optional[str] = None,
    feather_kernel_size: int = 15,
    feather_sigma: float = 3.0,
    dilate_px: int = 2,
    bite_info: Optional[dict] = None,
    cached_mask: Optional[np.ndarray] = None,
) -> bool:
    """
    Seamless Anatomical Lip-Lock Composite:
    Locks 100% of the patient's original lips, skin, mustache, cheeks, and perioral
    facial geometry from before_path, while embedding Gemini's refined teeth from after_path
    strictly inside the dental footprint (both upper and lower teeth).

    Uses a soft Gaussian alpha feather to eliminate all hard cut lines and sticker seams.

    Returns:
        True if successfully blended, False if fallback to raw Gemini image.
    """
    if output_path is None:
        output_path = after_path

    try:
        env_val = os.environ.get("ENABLE_SEAMLESS_LIP_LOCK", "true").strip().lower()
        if env_val in ["false", "0", "no", "off"]:
            print("[SeamlessLipLock] Skipped (ENABLE_SEAMLESS_LIP_LOCK is disabled).")
            return False

        if not os.path.isfile(before_path) or not os.path.isfile(after_path):
            print("[SeamlessLipLock] Warning: before or after file missing.")
            return False

        b_img = cv2.imread(before_path)
        a_img = cv2.imread(after_path)
        if b_img is None or a_img is None:
            print("[SeamlessLipLock] Warning: Failed to decode image with OpenCV.")
            return False

        h, w = b_img.shape[:2]

        # Ensure after_img matches before dimensions exactly
        if a_img.shape[:2] != (h, w):
            a_img = cv2.resize(a_img, (w, h), interpolation=cv2.INTER_LANCZOS4)

        # Mask comes from the ORIGINAL photo only: the patient's real mouth opening is the
        # ground truth. Using Gemini's teeth here lets the mask slide down over the lower lip.
        if cached_mask is not None:
            mask_blurred = cached_mask
            if mask_blurred.shape[:2] != (h, w):
                mask_blurred = cv2.resize(mask_blurred, (w, h), interpolation=cv2.INTER_LINEAR)
        else:
            mask_blurred = get_accurate_teeth_mask(
                b_img=b_img,
                a_img=None,
                before_path=before_path,
                binary=False,
                dilate_px=dilate_px,
                feather_kernel_size=feather_kernel_size,
                feather_sigma=feather_sigma,
            )

        if np.sum(mask_blurred > 0.05) == 0:
            print("[SeamlessLipLock] No mouth region detected; using raw AI image.")
            return False

        # Snap Gemini's teeth back onto the original mouth before compositing
        a_img = align_after_to_before(b_img, a_img, exclude_mask=(mask_blurred > 0.05))

        mask_3ch = np.repeat(mask_blurred[:, :, np.newaxis], 3, axis=2)

        # Alpha composite:
        # Inside dental footprint = 100% Gemini refined teeth & ceramic luster (both arches)
        # Outside footprint = 100% Original lips, mustache, cheeks, corners, skin
        blended = (a_img.astype(np.float32) * mask_3ch + b_img.astype(np.float32) * (1.0 - mask_3ch))

        # Depth shading so teeth sit INSIDE the mouth instead of looking pasted on top of it:
        # 1) soft shadow where the upper lip overhangs the teeth,
        # 2) teeth darken toward the mouth corners (the arch curves back into the cheeks).
        inside = (mask_blurred > 0.5).astype(np.float32)
        ys_in, xs_in = np.where(inside > 0)
        if len(ys_in) > 0:
            shade_h = max(3.0, (ys_in.max() - ys_in.min()) * 0.10)
            depth = np.cumsum(inside, axis=0)  # px below the mask's top edge, per column
            lip_shade = (1.0 - np.clip((depth - 1.0) / shade_h, 0.0, 1.0)) ** 2 * 0.30

            x_c = (xs_in.min() + xs_in.max()) / 2.0
            half_w = max(1.0, (xs_in.max() - xs_in.min()) / 2.0)
            dx = np.abs(np.arange(w, dtype=np.float32) - x_c) / half_w
            corridor = (np.clip((dx - 0.35) / 0.65, 0.0, 1.0) ** 1.5 * 0.45)[np.newaxis, :]

            shade = 1.0 - (1.0 - lip_shade) * (1.0 - corridor)
            shade = cv2.GaussianBlur(shade * inside, (0, 0), max(1.5, shade_h / 3.0))

            # Shade bright enamel only. Darkening the seam pixels (lip edge / dark gap) right at
            # the mask border drew a crisp black outline along the upper lip.
            a_gray = cv2.cvtColor(a_img, cv2.COLOR_BGR2GRAY).astype(np.float32)
            p40, p85 = np.percentile(a_gray[inside > 0], [40, 85])
            enamel_w = np.clip((a_gray - p40) / max(p85 - p40, 1.0), 0.0, 1.0)
            shade *= enamel_w * mask_blurred
            blended *= (1.0 - shade)[:, :, np.newaxis]

        blended = np.clip(blended, 0, 255).astype(np.uint8)

        # Space Line Shadow Guard: If before image had a space line, ensure it remains dark and crisp
        if bite_info is None:
            bite_info = detect_bite_space_line(b_img, before_path=before_path)
        blended = preserve_space_line_shadow(b_img, blended, bite_info=bite_info)

        # Save result with high quality
        cv2.imwrite(output_path, blended, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        print(f"[SeamlessLipLock] Successfully locked lips and blended teeth using seamless_blend.py to {output_path}")
        return True

    except Exception as e:
        print(f"[SeamlessLipLock Warning]: Blending encountered an error: {e}. Keeping raw AI output.")
        return False
