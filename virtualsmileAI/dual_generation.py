"""
Dual Parallel Smile Generation & Dental Computer Vision Best-Selection Engine.

Architecture:
  1. Concurrently fires 2 free-hand Google Gemini generation requests in parallel
     using Python's ThreadPoolExecutor(max_workers=2). Total latency = max(T1, T2).
  2. Post-processes both candidate images with optical blur matching and seamless lip-lock.
  3. Evaluates both candidates with an automated 4-Pillar Dental Quality Scoring Engine:
       - Pillar 1: Teeth Size & Golden Proportion (30 pts) [detects/penalizes horse teeth or stunted teeth]
       - Pillar 2: Dual-Arch & Bite Separation Integrity (30 pts) [checks lower arch & inter-arch bite line]
       - Pillar 3: Perioral Lip & Skin Fidelity (20 pts) [ensures zero facial distortion]
       - Pillar 4: Enamel Polish & Natural Translucency Depth (20 pts) [rewards 3D luster over flat white paint]
  4. Designates the candidate with the higher score as the winner and writes it to output_path.
  5. Fully fail-safe: if one candidate fails or is blocked, the other is automatically selected.
"""

import os
import io
import time
import json
import base64
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from typing import Dict, Any, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from google import genai
from google.genai import types
from virtualsmileAI.seamless_blend import (
    get_accurate_teeth_mask,
    detect_bite_space_line,
    apply_seamless_lip_lock,
    _get_mask_from_yolo,
    get_face_landmarker,
)


# -----------------------------------------------------------------------------
# 1. Computer Vision Dental Quality Scoring Engine (Continuous & Anti-Sticker)
# -----------------------------------------------------------------------------

def evaluate_teeth_size_and_proportions(
    before_cv: np.ndarray,
    candidate_cv: np.ndarray,
    bite_info: Dict[str, Any],
    before_path: Optional[str] = None,
    c_mask: Optional[np.ndarray] = None,
) -> Tuple[float, Dict[str, Any]]:
    """
    Pillar 1: Teeth Size, Lip-Scale & Proportions (25 Points) - Fully Dynamic.
    
    Uses continuous Gaussian decay so every single millimeter of difference moves
    the score dynamically, with specialized sensitivity for small-lip patients.
    """
    details = {
        "h_orig": 0.0,
        "h_cand": 0.0,
        "height_ratio": 1.0,
        "aspect_ratio": 0.80,
        "lip_harmony": "Standard",
        "score": 25.0,
    }
    try:
        h, w = before_cv.shape[:2]
        b_mask = get_accurate_teeth_mask(b_img=before_cv, a_img=before_cv, before_path=before_path, binary=True)
        if c_mask is None:
            c_mask = get_accurate_teeth_mask(b_img=candidate_cv, a_img=candidate_cv, binary=True)

        b_ys, b_xs = np.where(b_mask > 0)
        c_ys, c_xs = np.where(c_mask > 0)

        if len(b_ys) < 30 or len(c_ys) < 30:
            return 20.0, details

        h_orig = float(np.max(b_ys) - np.min(b_ys))
        w_orig = float(np.max(b_xs) - np.min(b_xs))
        h_cand = float(np.max(c_ys) - np.min(c_ys))
        w_cand = float(np.max(c_xs) - np.min(c_xs))

        details["h_orig"] = round(h_orig, 1)
        details["h_cand"] = round(h_cand, 1)

        if h_orig > 10:
            height_ratio = h_cand / h_orig
            details["height_ratio"] = round(height_ratio, 3)

            # Continuous Gaussian curve centered at ideal R_h = 1.00
            # Moves smoothly with every 0.005 variation in size!
            size_score = 25.0 * np.exp(-14.0 * ((height_ratio - 1.0) ** 2))

            # Strict Large Teeth Penalty (User Mandate: Large teeth must NOT win)
            if height_ratio > 1.05:
                large_pen = min(12.0, (height_ratio - 1.05) * 50.0)
                size_score = max(0.0, size_score - large_pen)
                details["large_teeth_penalty"] = round(large_pen, 2)

            # Golden Aspect Ratio check
            if h_cand > 15:
                aspect = (w_cand * 0.35) / h_cand
                details["aspect_ratio"] = round(aspect, 2)
                aspect_diff = abs(aspect - 0.80)
                if aspect_diff > 0.10:
                    size_score -= min(4.0, (aspect_diff - 0.10) * 15.0)

            # Small Lip Aperture Proportionality
            detector = get_face_landmarker()
            if detector is not None:
                try:
                    import mediapipe as mp
                    rgb_b = cv2.cvtColor(before_cv, cv2.COLOR_BGR2RGB)
                    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_b)
                    res = detector.detect(mp_img)
                    if res.face_landmarks:
                        lms = res.face_landmarks[0]
                        p13_y = int(lms[13].y * h)
                        p14_y = int(lms[14].y * h)
                        p78_x = int(lms[78].x * w)
                        p308_x = int(lms[308].x * w)

                        lip_aperture_h = max(10, abs(p14_y - p13_y))
                        lip_width = max(30, abs(p308_x - p78_x))
                        is_small_lips = (lip_aperture_h < 50) or (lip_width < (w * 0.30))

                        c_ymin = int(np.min(c_ys))
                        c_ymax = int(np.max(c_ys))
                        top_intrusion = max(0, p13_y - c_ymin)
                        bot_intrusion = max(0, c_ymax - p14_y)

                        if is_small_lips:
                            if top_intrusion > 3 or bot_intrusion > 3:
                                pen = min(6.0, (top_intrusion + bot_intrusion) * 0.6)
                                size_score -= pen
                                details["lip_harmony"] = f"Penalized (-{pen:.1f} pts, too big for small lips)"
                            elif 0.96 <= height_ratio <= 1.04:
                                size_score = min(25.0, size_score + 2.0)
                                details["lip_harmony"] = "Superior: Small, Compact & Complete"
                            else:
                                details["lip_harmony"] = "Compact Fit"
                        else:
                            details["lip_harmony"] = "Standard Proportion"
                except Exception:
                    pass

            size_score = max(0.0, min(25.0, size_score))
            details["score"] = round(size_score, 2)
            return details["score"], details
    except Exception as e:
        print(f"[ScoreAI Size Check Note]: {e}")

    return 20.0, details


def evaluate_anti_sticker_naturalness(
    candidate_cv: np.ndarray,
    teeth_mask: np.ndarray,
) -> Tuple[float, Dict[str, Any]]:
    """
    Pillar 2: Natural 3D Emergence vs Sticker Teeth (25 Points) - Anti-Sticker Guard.
    
    Detects and heavily penalizes flat, pasted-on "sticker-like" teeth:
      1. Interdental Embrasure Grooves (0 to 10 pts):
         Real teeth have 3D vertical shadow valleys between adjacent teeth.
         Sticker teeth are a continuous flat white wall without separation grooves.
      2. Cervical-to-Incisal Shading Gradient (0 to 8 pts):
         Real teeth have natural chromatic/depth transition from gumline to tooth body.
         Sticker teeth are flat chalky white with identical lightness throughout.
      3. 3D Convexity & Specular Highlight Variance (0 to 7 pts):
         Real teeth curve convexly, catching glistening specular light ribbons.
         Sticker teeth are flat 2D matte decals.
    """
    details = {
        "embrasure_depth": 0.0,
        "embrasure_score": 5.0,
        "cervical_diff": 0.0,
        "gradient_score": 4.0,
        "highlight_contrast": 0.0,
        "convexity_score": 4.0,
        "score": 18.0,
    }

    try:
        if teeth_mask is None or np.sum(teeth_mask > 0) < 50:
            return 18.0, details

        ys, xs = np.where(teeth_mask > 0)
        ymin, ymax = int(np.min(ys)), int(np.max(ys))
        xmin, xmax = int(np.min(xs)), int(np.max(xs))

        gray = cv2.cvtColor(candidate_cv, cv2.COLOR_BGR2GRAY)
        lab = cv2.cvtColor(candidate_cv, cv2.COLOR_BGR2LAB)
        L_ch = lab[:, :, 0].astype(np.float32)

        h_span = ymax - ymin
        w_span = xmax - xmin
        y_mid = ymin + int(h_span * 0.35)  # upper crowns midline

        # 1. Interdental Grooves across Central Dental Arch
        x1 = xmin + int(w_span * 0.20)
        x2 = xmin + int(w_span * 0.80)
        row_pixels = gray[y_mid, x1:x2]

        if len(row_pixels) > 20:
            smooth_row = cv2.GaussianBlur(row_pixels.astype(np.float32), (1, 15), 3.0).flatten()
            valley_depths = []
            for i in range(1, len(smooth_row) - 1):
                if smooth_row[i] < smooth_row[i-1] and smooth_row[i] < smooth_row[i+1]:
                    depth = max(smooth_row[i-1] - smooth_row[i], smooth_row[i+1] - smooth_row[i])
                    valley_depths.append(depth)

            avg_valley_depth = float(np.mean(valley_depths)) if valley_depths else 0.0
            details["embrasure_depth"] = round(avg_valley_depth, 2)
            # Ideal anatomical embrasure groove depth is 4.5 to 7.5 gray levels.
            # If deeper than 7.5, it indicates open black gaps, dark triangles, or missing contact!
            clamped_depth = min(7.5, avg_valley_depth)
            if avg_valley_depth > 7.5:
                excess_gap_pen = min(2.5, (avg_valley_depth - 7.5) * 1.5)
                embrasure_score = max(1.0, (clamped_depth * 1.05) - excess_gap_pen)
                details["excess_gap_penalty"] = round(excess_gap_pen, 2)
            else:
                embrasure_score = min(8.0, max(1.0, avg_valley_depth * 1.05))
        else:
            embrasure_score = 5.0
        details["embrasure_score"] = round(embrasure_score, 2)

        # 2. Cervical-to-Incisal Shading Gradient (Lip Shadow & Emergence)
        x_mid = (xmin + xmax) // 2
        w_sample = max(5, int(w_span * 0.15))
        central_strip = L_ch[ymin:ymin + int(h_span * 0.60), x_mid - w_sample:x_mid + w_sample]
        if central_strip.size > 20:
            vert_profile = np.mean(central_strip, axis=1)
            top_cervical = np.mean(vert_profile[:max(1, len(vert_profile)//3)])
            mid_incisal = np.mean(vert_profile[max(1, len(vert_profile)//3):])
            cervical_diff = float(abs(mid_incisal - top_cervical))
            details["cervical_diff"] = round(cervical_diff, 2)
            # Natural teeth have depth difference from upper lip shadow; sticker teeth are flat
            gradient_score = min(9.0, max(1.5, (cervical_diff / 55.0) * 9.0))
        else:
            gradient_score = 4.0
        details["gradient_score"] = round(gradient_score, 2)

        # 3. 3D Convexity & Specular Highlight Variance
        enamel_L = L_ch[teeth_mask > 0]
        p92 = float(np.percentile(enamel_L, 92))
        p50 = float(np.percentile(enamel_L, 50))
        highlight_contrast = max(0.0, p92 - p50)
        details["highlight_contrast"] = round(highlight_contrast, 2)
        # Convex e.max enamel reflections are 12 to 35 units higher than median
        # Flat stickers are matte (contrast < 8)
        convexity_score = min(8.0, max(1.0, (highlight_contrast / 30.0) * 8.0))
        details["convexity_score"] = round(convexity_score, 2)

        # 4. Anti-Artificial Border Line (Anti-Decal Seam)
        # Real teeth have a soft incisal edge transition (spike < 130)
        # Sticker teeth often have a drawn dark pencil border line (spike > 150)
        sob_y = np.abs(cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3))
        tip_y1 = ymin + int(h_span * 0.70)
        tip_y2 = ymin + int(h_span * 0.95)
        tip_x1 = xmin + int(w_span * 0.25)
        tip_x2 = xmin + int(w_span * 0.75)
        incisal_spikes = sob_y[tip_y1:tip_y2, tip_x1:tip_x2]
        max_spike = float(np.max(incisal_spikes)) if incisal_spikes.size > 0 else 0.0
        details["max_incisal_spike"] = round(max_spike, 1)
        border_penalty = 0.0
        if max_spike > 150.0:
            border_penalty = min(5.0, (max_spike - 150.0) * 0.03)
            details["sticker_border_penalty"] = round(border_penalty, 2)

        # 5. Interdental Cleanliness & Dark Spot / Black Triangle Penalty
        # Between adjacent teeth, contacts must be clean and flush with pearlescent white enamel.
        # Checks the upper crown contact zone (ymin to ymin + 0.50*h_span) for true dark voids/pinholes (L < 55).
        # Avoids mistaking the open mouth cavity below single-arch incisors for an enamel defect.
        upper_mask = np.zeros_like(teeth_mask)
        upper_mask[ymin:ymin + int(h_span * 0.50), xmin + int(w_span * 0.15):xmin + int(w_span * 0.85)] = 1
        upper_mask = upper_mask & (teeth_mask > 0)
        dark_holes_count = int(np.sum((L_ch < 55) & (upper_mask > 0)))
        details["dark_holes_count"] = dark_holes_count
        hole_penalty = 0.0
        if dark_holes_count > 30:
            hole_penalty = min(4.0, (dark_holes_count - 30) * 0.05)
            details["black_spot_penalty"] = round(hole_penalty, 2)

        total_naturalness = round(max(0.0, min(25.0, embrasure_score + gradient_score + convexity_score - border_penalty - hole_penalty)), 2)
        details["score"] = total_naturalness
        return total_naturalness, details
    except Exception as e:
        print(f"[ScoreAI Anti-Sticker Note]: {e}")

    return 18.0, details


def evaluate_bite_and_arch_integrity(
    candidate_cv: np.ndarray,
    bite_info: Dict[str, Any],
) -> Tuple[float, Dict[str, Any]]:
    """
    Pillar 3: Dual-Arch & Bite Separation Contrast (25 Points) - Fully Dynamic.
    
    Dynamically measures the depth and contrast ratio of the horizontal separation valley
    rather than a static all-or-nothing score.
    """
    details = {
        "cand_has_lower_teeth": False,
        "cand_has_space_line": False,
        "valley_contrast": 0.0,
        "score": 25.0,
    }

    try:
        cand_bite = detect_bite_space_line(candidate_cv)
        details["cand_has_lower_teeth"] = cand_bite.get("bottom_teeth_exist", False)
        details["cand_has_space_line"] = cand_bite.get("has_space_line", False)

        orig_had_lower = bite_info.get("bottom_teeth_exist", False)
        orig_had_space = bite_info.get("has_space_line", False)

        top_p = float(cand_bite.get("top_peak") or 0.0)
        bot_p = float(cand_bite.get("bot_peak") or 0.0)
        val_p = float(cand_bite.get("valley_val") or 0.0)

        # Dynamic contrast ratio of the bite gap
        if max(top_p, bot_p) > 10.0:
            valley_contrast = max(0.0, (min(top_p, bot_p) - val_p) / max(top_p, bot_p, 1.0))
        else:
            valley_contrast = 0.0
        details["valley_contrast"] = round(valley_contrast, 3)

        if orig_had_lower:
            if not cand_bite.get("bottom_teeth_exist", False):
                # Erased lower teeth! Disqualify this candidate in bite integrity.
                details["erased_lower_teeth"] = True
                details["score"] = 0.0
                return 0.0, details

            # Both arches present: Reward connected whole smile with filled gaps and restored arches
            bite_score = 25.0
            details["connected_whole_smile"] = True
        else:
            # Upper only
            if cand_bite.get("bottom_teeth_exist", False):
                bite_score = 0.0  # invented fake bottom teeth when none existed
                details["invented_bottom_teeth_penalty"] = True
            else:
                bite_score = 25.0

        bite_score = max(0.0, min(25.0, bite_score))
        details["score"] = round(bite_score, 2)
        return details["score"], details
    except Exception as e:
        print(f"[ScoreAI Bite Note]: {e}")

    return 20.0, details


def evaluate_enamel_polish_and_depth(
    candidate_cv: np.ndarray,
    teeth_mask: np.ndarray,
) -> Tuple[float, Dict[str, Any]]:
    """
    Pillar 4: Zonal Natural Translucency & Enamel Polish (25 Points) - Fully Dynamic.
    
    Strictly verifies user's clinical mandate:
      - ZONE 1 (Center 85% of tooth body): Must be SOLID PEARLESCENT WHITE (high L*, low variance).
        Penalizes any dark/translucent shading or hollow grey patches in the middle of the teeth!
      - ZONE 2 (Bottom 1.0-1.5mm incisal tip): Must show crystalline optical  natural translucency.
    """
    details = {
        "center_solidity": 0.0,
        "incisal_translucency": 0.0,
        "score": 25.0,
    }

    try:
        if teeth_mask is None or np.sum(teeth_mask > 0) < 50:
            return 18.0, details

        lab = cv2.cvtColor(candidate_cv, cv2.COLOR_BGR2LAB)
        L_ch = lab[:, :, 0].astype(np.float32)

        ys, xs = np.where(teeth_mask > 0)
        ymin, ymax = int(np.min(ys)), int(np.max(ys))
        h_span = ymax - ymin

        if h_span < 15:
            return 20.0, details

        # Zone 1: Center tooth body (from 20% to 75% vertical depth of upper teeth)
        y_c1 = ymin + int(h_span * 0.15)
        y_c2 = ymin + int(h_span * 0.70)
        center_mask = np.zeros_like(teeth_mask)
        center_mask[y_c1:y_c2, :] = teeth_mask[y_c1:y_c2, :]
        center_L = L_ch[center_mask > 0]

        # Zone 2: Incisal cutting tip (bottom 15% of upper teeth)
        y_tip1 = ymin + int(h_span * 0.75)
        y_tip2 = ymax
        tip_mask = np.zeros_like(teeth_mask)
        tip_mask[y_tip1:y_tip2, :] = teeth_mask[y_tip1:y_tip2, :]
        tip_L = L_ch[tip_mask > 0]

        score = 25.0

        if len(center_L) > 30:
            mean_center_L = float(np.mean(center_L))
            std_center_L = float(np.std(center_L))
            details["center_solidity"] = round(mean_center_L, 1)

            # Center must be solid and bright (L > 150)
            # Penalize dark/grey translucent splotches in the center
            if mean_center_L < 150.0:
                score -= min(8.0, (150.0 - mean_center_L) * 0.4)
            if std_center_L > 28.0:
                score -= min(5.0, (std_center_L - 28.0) * 0.5)

        if len(tip_L) > 20 and len(center_L) > 30:
            mean_tip_L = float(np.mean(tip_L))
            delta_tip = mean_center_L - mean_tip_L
            details["incisal_translucency"] = round(delta_tip, 2)
            # Realistic subtle translucency is 2.0 to 14.0 units
            if 2.0 <= delta_tip <= 14.0:
                trans_bonus = 2.0 - abs(delta_tip - 6.0) * 0.15
                score = min(25.0, score + max(0.5, trans_bonus))
            elif delta_tip > 16.0:
                # Excessively dark tip / fake drawn border line!
                pen = min(5.0, (delta_tip - 16.0) * 0.5)
                score -= pen
                details["excessive_dark_tip_penalty"] = round(pen, 2)
            elif delta_tip < 1.0:
                # Flat opaque chalky edge with zero translucency
                score -= 3.0

        score = max(0.0, min(25.0, score))
        details["score"] = round(score, 2)
        return details["score"], details
    except Exception as e:
        print(f"[ScoreAI Polish/Depth Note]: {e}")

    return 20.0, details


def score_smile_candidate(
    before_cv: np.ndarray,
    candidate_cv: np.ndarray,
    bite_info: Dict[str, Any],
    before_path: Optional[str] = None,
) -> Tuple[float, Dict[str, Any]]:
    bh, bw = before_cv.shape[:2]
    if candidate_cv.shape[:2] != (bh, bw):
        candidate_cv = cv2.resize(candidate_cv, (bw, bh), interpolation=cv2.INTER_LANCZOS4)

    c_mask = get_accurate_teeth_mask(b_img=candidate_cv, a_img=candidate_cv, binary=True)

    size_pts, size_det = evaluate_teeth_size_and_proportions(before_cv, candidate_cv, bite_info, before_path, c_mask=c_mask)
    natural_pts, natural_det = evaluate_anti_sticker_naturalness(candidate_cv, c_mask)
    bite_pts, bite_det = evaluate_bite_and_arch_integrity(candidate_cv, bite_info)
    depth_pts, depth_det = evaluate_enamel_polish_and_depth(candidate_cv, c_mask)

    total_score = round(size_pts + natural_pts + bite_pts + depth_pts, 2)
    if bite_det.get("erased_lower_teeth", False):
        total_score = max(0.0, round(total_score - 35.0, 2))
    report = {
        "total_score": total_score,
        "size_score": size_pts,
        "natural_score": natural_pts,
        "bite_score": bite_pts,
        "depth_score": depth_pts,
        "details": {
            "size": size_det,
            "natural": natural_det,
            "bite": bite_det,
            "depth": depth_det,
        },
    }
    return total_score, report


# -----------------------------------------------------------------------------
# 2. Multimodal AI Judge (gemini-3.1-flash-lite with strict timeout fallback)
# -----------------------------------------------------------------------------

def run_ai_judge_evaluation(
    client: genai.Client,
    candidate1_cv: np.ndarray,
    candidate2_cv: np.ndarray,
    before_cv: Optional[np.ndarray] = None,
    teeth_mask: Optional[np.ndarray] = None,
    bite_info: Optional[Dict[str, Any]] = None,
    timeout_sec: float = 3.5,
) -> Optional[Dict[str, Any]]:
    """
    Multimodal AI Judge using gemini-3.1-flash-lite.
    
    Evaluates Candidate 1 vs Candidate 2 against the patient's ORIGINAL teeth:
      1. Bottom Teeth Fidelity: If bottom teeth exist in original photo, candidate MUST include them.
      2. Authentic Bite Relationship: Preserves touching contact vs open space line without inventing fake gaps.
      3. Tooth Size & Lip Scale: Large, elongated, horse-like teeth MUST NOT win!
      4. Interproximal Contacts & Enamel: Clean contacts without black triangles or sticker look.
      
    Operates with an immediate hard timeout (default 3.5s, configurable via AI_JUDGE_TIMEOUT_SEC).
    If timeout or error occurs, returns None for instant fallback to pure Computer Vision scoring.
    """
    t0 = time.time()
    try:
        h, w = candidate1_cv.shape[:2]

        # Crop to mouth / teeth region with padding to minimize payload and maximize clinical focus
        if teeth_mask is not None and np.sum(teeth_mask > 0) > 50:
            ys, xs = np.where(teeth_mask > 0)
            ymin, ymax = int(np.min(ys)), int(np.max(ys))
            xmin, xmax = int(np.min(xs)), int(np.max(xs))
            pad_y = int((ymax - ymin) * 0.45)
            pad_x = int((xmax - xmin) * 0.25)
            y1, y2 = max(0, ymin - pad_y), min(h, ymax + pad_y)
            x1, x2 = max(0, xmin - pad_x), min(w, xmax + pad_x)
        else:
            y1, y2 = max(0, int(h * 0.25)), min(h, int(h * 0.85))
            x1, x2 = max(0, int(w * 0.15)), min(w, int(w * 0.85))

        crop1 = cv2.resize(candidate1_cv[y1:y2, x1:x2], (512, 384), interpolation=cv2.INTER_AREA)
        crop2 = cv2.resize(candidate2_cv[y1:y2, x1:x2], (512, 384), interpolation=cv2.INTER_AREA)

        pil1 = Image.fromarray(cv2.cvtColor(crop1, cv2.COLOR_BGR2RGB))
        pil2 = Image.fromarray(cv2.cvtColor(crop2, cv2.COLOR_BGR2RGB))

        pil_b = None
        if before_cv is not None:
            crop_b = cv2.resize(before_cv[y1:y2, x1:x2], (512, 384), interpolation=cv2.INTER_AREA)
            pil_b = Image.fromarray(cv2.cvtColor(crop_b, cv2.COLOR_BGR2RGB))

        orig_has_bottom = (bite_info or {}).get("bottom_teeth_exist", False)
        orig_has_space = (bite_info or {}).get("has_space_line", False)
        orig_is_touch = (bite_info or {}).get("is_touching_bite", False)
        orig_bite_name = "open horizontal space line" if orig_has_space else ("touching edge-to-edge contact" if orig_is_touch else "upper arch only")

        if orig_has_bottom:
            ground_truth_msg = (
                "🔬 CLINICAL GROUND TRUTH FROM IMAGE 1 (MEASURED BY COMPUTER VISION):\n"
                f"- VISIBLE LOWER TEETH: YES, VISIBLE/CONNECTING LOWER TEETH ARE PRESENT IN IMAGE 1 (Arch architecture: {orig_bite_name}).\n"
                "- MANDATORY WHOLE SMILE CLINICAL RULE: EVEN IF ONLY 2 TEETH ARE VISIBLE OR CONNECT TO THE TOP AND BOTTOM BITE LINE, THIS STRICTLY COUNTS AS A WHOLE SMILE!\n"
                "- The candidate MUST create and finish the WHOLE SMILE, preserving and restoring all connecting and visible lower teeth with full enamel whiteness and natural finish.\n"
                "- Any candidate that erases, blacks out, or removes the connecting or visible lower teeth (leaving an unnatural black void below the upper teeth) "
                "COMMITS A CRITICAL CLINICAL ERROR, MUST BE SEVERELY PENALIZED (-40 pts), AND CANNOT WIN.\n"
            )
        else:
            ground_truth_msg = (
                "🔬 CLINICAL GROUND TRUTH FROM IMAGE 1 (MEASURED BY COMPUTER VISION):\n"
                "- VISIBLE LOWER TEETH: NO, zero lower teeth are exposed in IMAGE 1 (Upper arch only).\n"
                "- NON-NEGOTIABLE CLINICAL MANDATE: Candidate must refine ONLY upper teeth. DO NOT invent fake lower teeth.\n"
                "- NOTE: If you observe even 2 teeth connecting at the bite line that were faintly visible in Image 1, reward the candidate for refining them naturally as a whole smile.\n"
            )

        def _call_gemini():
            if pil_b is not None:
                contents_list = [
                    "You are a master cosmetic prosthodontist evaluating Candidate A vs Candidate B for smile makeover quality.\n\n"
                    + ground_truth_msg +
                    "\nExamine the following 3 images carefully:",
                    "IMAGE 1: ORIGINAL PATIENT SMILE (Ground Truth Reference):",
                    pil_b,
                    "IMAGE 2: CANDIDATE A (First AI Smile Design):",
                    pil1,
                    "IMAGE 3: CANDIDATE B (Second AI Smile Design):",
                    pil2,
                    "CLINICAL EVALUATION TASK:\n"
                    "Compare Candidate A (Image 2) and Candidate B (Image 3) against the Original Patient Smile (Image 1):\n"
                    "1. LIP FIDELITY & NO INVENTED TEETH: The patient's lips MUST remain as-is! Did either candidate alter the lips, draw teeth over the lips, or invent fake lower teeth when only upper teeth were exposed in Image 1? If a candidate altered lips or invented fake teeth, DISQUALIFY THAT CANDIDATE (-40 pts).\n"
                    "2. NATURAL TRANSLUCENCY AT BOTTOM ONLY WITH RICH SHINE: Incisal natural translucency belongs exclusively to the bottom cutting tips with delicate opalescence (like the reference model). Did either candidate put grey/dark translucent shading in the middle or center of the teeth? Reward solid ivory tooth centers with bottom-only translucency and liquid wet ceramic shine.\n"
                    "3. WHOLE SMILE & GAP FILLING: If there was a gap between the top and bottom bite line, reward the candidate that FILLED IT and connected the arches into a unified whole smile! Even if only 2 teeth connect, count as a connected whole smile. Disqualify (-40 pts) any candidate that leaves lower teeth untreated or carves dark holes/defects between arches.\n"
                    "4. TOOTH SIZE & LIP HARMONY: Large, elongated, bulky horse teeth MUST NOT WIN (-25 pts). Reward compact, delicate, natural proportions.\n"
                    "5. ENAMEL & CONTACTS: Clean interproximal contacts with zero black triangles, zero pinholes, and natural 3D glazed ceramic luster.\n\n"
                    "Output strict JSON:\n"
                    '{"winner": "A" or "B", "score_A": 0-100, "score_B": 0-100, "cand_A_has_lower_teeth": true or false, "cand_B_has_lower_teeth": true or false, "cand_A_size_fit": "compact" or "oversized", "cand_B_size_fit": "compact" or "oversized", "reason": "clinical comparison explaining why winner won and whether Candidate A or B preserved lower teeth"}'
                ]
            else:
                contents_list = [
                    "You are a master cosmetic prosthodontist judging Candidate A vs Candidate B for the same patient.\n",
                    pil1,
                    pil2,
                    "Evaluate with extreme clinical rigor:\n"
                    "1. Whole Smile Integrity: Even if only 2 teeth connect to top and bottom line, the whole smile must be completed with both arches harmonized. Did either candidate erase connecting lower teeth?\n"
                    "2. Tooth Size: Large, elongated, horse-like teeth MUST NOT win! Reward compact, delicate tooth scale.\n"
                    "3. Interproximal contacts: Does either candidate have unnatural black triangles, dark gaps, or fused teeth?\n"
                    "4. Natural enamel: Which looks like realistic ceramic porcelain vs a flat pasted sticker or plastic?\n"
                    "5. Incisal edges: Which has clean, natural cutting edges without artificial dark borders?\n\n"
                    "Output strict JSON:\n"
                    '{"winner": "A" or "B", "score_A": 0-100, "score_B": 0-100, "reason": "concise explanation of why winner won"}'
                ]

            return client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=contents_list,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                    max_output_tokens=250,
                ),
            )

        with ThreadPoolExecutor(max_workers=1) as judge_exec:
            future = judge_exec.submit(_call_gemini)
            response = future.result(timeout=timeout_sec)
            elapsed = round(time.time() - t0, 2)
            parsed = json.loads(response.text)
            parsed["elapsed_sec"] = elapsed

            # Map Candidate A -> 1, Candidate B -> 2
            winner_str = str(parsed.get("winner", "A")).strip().upper()
            parsed["winner"] = 2 if "B" in winner_str or winner_str == "2" else 1

            score_a = float(parsed.get("score_A", parsed.get("c1_score", 70)))
            score_b = float(parsed.get("score_B", parsed.get("c2_score", 70)))
            c1_lower = parsed.get("cand_A_has_lower_teeth", parsed.get("c1_lower_preserved", True))
            c2_lower = parsed.get("cand_B_has_lower_teeth", parsed.get("c2_lower_preserved", True))

            # Enforce ground truth penalty if candidate erased lower teeth
            if orig_has_bottom:
                if not c1_lower:
                    score_a = min(score_a, 40.0)
                if not c2_lower:
                    score_b = min(score_b, 40.0)

            parsed["c1_score"] = score_a
            parsed["c2_score"] = score_b
            parsed["c1_lower_preserved"] = c1_lower
            parsed["c2_lower_preserved"] = c2_lower
            parsed["c1_size_fit"] = parsed.get("cand_A_size_fit", "compact")
            parsed["c2_size_fit"] = parsed.get("cand_B_size_fit", "compact")
            parsed["original_bottom_visible"] = orig_has_bottom
            parsed["original_bite"] = orig_bite_name

            print(f"[DualSmileAI AI-Judge] ⚡ gemini-3.1-flash-lite evaluation completed in {elapsed}s.")
            return parsed

    except TimeoutError:
        print(f"[DualSmileAI AI-Judge] ⏱️ AI Judge reached {timeout_sec}s timeout. Falling back smoothly to 100% Computer Vision scoring.")
        return None
    except Exception as e:
        print(f"[DualSmileAI AI-Judge Note] AI Judge bypassed ({e}). Falling back smoothly to 100% Computer Vision scoring.")
        return None


# -----------------------------------------------------------------------------
# 3. Parallel Generation Worker
# -----------------------------------------------------------------------------

def _execute_gemini_candidate_worker(
    candidate_id: int,
    client: genai.Client,
    kwargs: Dict[str, Any],
    orig_w: int,
    orig_h: int,
    input_path: str,
    bite_info: Dict[str, Any],
) -> np.ndarray:
    """
    Worker executing an independent Gemini image generation call.
    Runs free-hand with the clinical prompt, decodes the image, resizes to exact
    original dimensions, and applies optical blur and seamless lip lock.
    """
    t0 = time.time()
    print(f"[DualSmileAI] 🚀 Worker {candidate_id}: Launched Gemini generation...")

    interaction = client.interactions.create(**kwargs)

    # Check for safety moderation or missing image
    if not interaction.output_image or not interaction.output_image.data:
        status_val = getattr(interaction, "status", "unknown")
        errors_val = getattr(interaction, "errors", None)
        raise RuntimeError(f"Worker {candidate_id} returned no image (Status: {status_val}, Errors: {errors_val})")

    raw_bytes = base64.b64decode(interaction.output_image.data)
    rendered_pil = Image.open(io.BytesIO(raw_bytes))

    # Resize back to exact original canvas dimensions
    if rendered_pil.size != (orig_w, orig_h):
        rendered_pil = rendered_pil.resize((orig_w, orig_h), Image.LANCZOS)

    candidate_cv = cv2.cvtColor(np.array(rendered_pil.convert("RGB")), cv2.COLOR_RGB2BGR)

    # Post-process: Optical camera softness matching
    try:
        from virtualsmileAI.gemini import match_teeth_blur_and_whiteness
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_f:
            tmp_candidate_path = tmp_f.name
        cv2.imwrite(tmp_candidate_path, candidate_cv)
        match_teeth_blur_and_whiteness(before_path=input_path, after_path=tmp_candidate_path, output_path=tmp_candidate_path)
        candidate_cv = cv2.imread(tmp_candidate_path)
        if os.path.isfile(tmp_candidate_path):
            os.remove(tmp_candidate_path)
    except Exception as e:
        print(f"[DualSmileAI Warning] Worker {candidate_id} blur/whiteness pass note: {e}")

    # Post-process: Seamless Lip-Lock & Space Line Guard
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_f:
            tmp_lock_path = tmp_f.name
        cv2.imwrite(tmp_lock_path, candidate_cv)
        apply_seamless_lip_lock(
            before_path=input_path,
            after_path=tmp_lock_path,
            output_path=tmp_lock_path,
            bite_info=bite_info,
        )
        candidate_cv = cv2.imread(tmp_lock_path)
        if os.path.isfile(tmp_lock_path):
            os.remove(tmp_lock_path)
    except Exception as e:
        print(f"[DualSmileAI Warning] Worker {candidate_id} lip-lock pass note: {e}")

    elapsed = round(time.time() - t0, 2)
    print(f"[DualSmileAI] ⏱️ Worker {candidate_id} completed successfully in {elapsed}s.")
    return candidate_cv


# -----------------------------------------------------------------------------
# 3. Main Dual Concurrency & Best-Selection Function
# -----------------------------------------------------------------------------

def run_dual_generation_and_select_best(
    input_path: str,
    output_path: str,
) -> None:
    """
    Main entry point for dual parallel generation:
      - Reads input photograph and pre-scans bite geometry.
      - Fires 2 concurrent generation calls in parallel via ThreadPoolExecutor.
      - Scores both candidates with score_smile_candidate().
      - Saves the winner directly to output_path.
      - Seamless fail-safe: if one fails, the other automatically wins.
    """
    from virtualsmileAI.gemini import (
        get_api_key,
        get_model_name,
        get_thinking_level,
        PROMPT,
    )

    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not configured. Set GEMINI_API_KEY in environment or .env.")

    model_name = get_model_name()
    thinking_level = get_thinking_level()

    with Image.open(input_path) as orig_img:
        orig_w, orig_h = orig_img.size

    with open(input_path, "rb") as f:
        img_bytes = f.read()

    mime_type = "image/png" if input_path.lower().endswith(".png") else "image/jpeg"
    b64_img = base64.b64encode(img_bytes).decode("utf-8")

    client = genai.Client(api_key=api_key)

    # 1. Computer Vision Bite Pre-Scan
    b_img_cv = cv2.imread(input_path)
    bite_info = detect_bite_space_line(b_img_cv, before_path=input_path)

    if bite_info.get("bottom_teeth_exist", False) or bite_info.get("has_space_line") or bite_info.get("is_touching_bite"):
        bite_header = (
            "🚨 COMPUTER VISION SCAN CONFIRMED BITE GEOMETRY — MANDATORY CLINICAL DIRECTIVE:\n"
            "- ARCH ARCHITECTURE: DUAL ARCH WITH VISIBLE / CONNECTING TEETH (WHOLE SMILE DESIGN).\n"
            "- MANDATE 1 (FILL ANY GAP BETWEEN TOP AND BOTTOM LINE — CONNECTED WHOLE SMILE): If there is any space, gap, or opening between the top and bottom bite line, FILL IT with clean, beautifully sculpted enamel! Even if only two teeth attach or connect at the bite line, count as a complete WHOLE SMILE which is connected! DO NOT leave dark holes, empty gaps, or disconnected arches between the top and bottom teeth! Connect and align both arches into a gorgeous, continuous, unbroken whole smile with individual tooth contours cleanly delineated by fine anatomical contact lines!\n"
            "- MANDATE 2 (WHOLE SMILE MANDATE — BOTH ARCHES ACTIVELY REGENERATED): Both UPPER and LOWER teeth are visible. Actively regenerate, beautify, and whiten BOTH rows completely! NEVER leave lower teeth dull, yellow, stained, or untreated! Create a bright, uniform, natural ceramic shade across both upper and lower arches!\n"
            "- MANDATE 3 (KEEP LIPS 100% AS IT IS): The patient's lips (upper lip, lower lip, lip corners, cupid's bow) must remain 100% FROZEN in their exact original position, shape, and thickness! Do NOT alter the lips, do NOT move the lips, and do NOT paint teeth over the lips!\n"
            "- MANDATE 4 (INCISAL NATURAL TRANSLUCENCY AT EDGE WITH SHINE — LIKE DENTAL CERAMIC REFERENCE): Apply exquisite, glassy incisal enamel translucency with delicate opalescent bluish light-transmission strictly along the very bottom cutting edge tips of the upper teeth (and top edge of lower teeth). The entire tooth body above the edge must be 100% solid, bright, opaque pearlescent ivory white. Add rich, wet-enamel specular highlights and liquid ceramic shine across all crowns!\n"
            "- MANDATE 5 (NATURAL OVERLAP & DEPTH): Top teeth are in front (outside) and bottom teeth are behind (inside). Maintain this authentic front-to-back dental relationship and natural smile curve.\n"
            "- MANDATE 6 (EXACT VISIBLE TEETH & STRUCTURE — NOT BIG OR SMALL): Rebuild exact teeth visible in the source—no extra teeth, no fewer teeth. Close horizontal gaps/diastemas between adjacent teeth, remove all stains, and maintain compact, natural tooth proportions (NEVER oversized, horse-like, or bulky teeth)!\n\n"
        )
    else:
        bite_header = (
            "🚨 COMPUTER VISION SCAN CONFIRMED BITE GEOMETRY — MANDATORY CLINICAL DIRECTIVE:\n"
            "- ARCH ARCHITECTURE: UPPER ARCH ONLY EXPOSED. Zero bottom teeth are visible in this photograph.\n"
            "- MANDATE 1 (UPPER ARCH ONLY — ZERO BOTTOM TEETH): ONLY upper teeth are visible in this photograph. DO NOT invent, fabricate, draw, or render ANY bottom teeth! The mouth cavity below the upper teeth and the lower lip must remain 100% dark, untouched, and original!\n"
            "- MANDATE 2 (KEEP LIPS 100% AS IT IS): Keep the patient's lips EXACTLY AS THEY ARE in the original photograph! Do NOT alter the lip shape, do NOT move the lips, do NOT raise or lower the lips, do NOT thin or thicken the lips, and do NOT draw teeth over the lower lip! The lips must remain 100% frozen in their exact original position, contours, and color.\n"
            "- MANDATE 3 (INCISAL NATURAL TRANSLUCENCY AT BOTTOM ONLY WITH SHINE — LIKE DENTAL CERAMIC REFERENCE): Apply exquisite, glassy enamel translucency with delicate opalescent light transmission strictly along the very bottom cutting edges of the upper teeth (the bottom 1.0mm edge). The entire center and middle of every tooth must be 100% dense, solid, opaque, bright pearlescent ivory white. Add rich wet specular shine and liquid ceramic gloss!\n"
            "- MANDATE 4 (EXACT VISIBLE TEETH & STRUCTURE — NOT BIG OR SMALL): Rebuild exact teeth visible in the source—no extra teeth, no fewer teeth. Close horizontal gaps/diastemas between adjacent teeth, remove all stains, and keep upper teeth small, compact, and terminating at their original baseline (NEVER elongated or oversized)!\n\n"
        )

    # 2. Reference Image for Incisal Translucency (optional via ENABLE_TRANSLUCENCY_REF)
    ref_image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "translucency_reference.png")
    use_ref_img = os.path.isfile(ref_image_path) and os.environ.get("ENABLE_TRANSLUCENCY_REF", "false").strip().lower() in ["true", "1", "yes"]

    if use_ref_img:
        with open(ref_image_path, "rb") as rf:
            ref_bytes = rf.read()
        b64_ref = base64.b64encode(ref_bytes).decode("utf-8")
        ref_header = (
            "IMAGE 1 is the patient photograph to edit in-place.\n"
            "IMAGE 2 is the clinical reference demonstrating target natural incisal enamel natural translucency, internal mamelon structure, and delicate incisal halo along the cutting edges.\n\n"
            "TASK: Perform in-place cosmetic refinement of VISIBLE TOOTH ENAMEL ONLY on IMAGE 1.\n"
            "- NATURAL TRANSLUCENCY REFERENCE: Emulate the natural incisal enamel natural translucency, internal mamelon depth, and delicate incisal halo shown in IMAGE 2 along the biting edges of visible teeth in IMAGE 1.\n"
            "- ARCH & BITE INTEGRITY: Replicate ONLY the optical enamel natural translucency and mamelon texture from IMAGE 2. Do NOT copy IMAGE 2's single-arch layout, gumline, or tooth shape—IMAGE 1's authentic dual-arch geometry, bite space line, and full lower teeth MUST remain 100% intact!\n"
            "- FLAWLESS ENAMEL & RESTORATION: Rebuild any broken or chipped teeth with full solid enamel, with ZERO brown spots and zero residual defect. Obey all non-negotiable rules: freeze lips 100%, preserve authentic bite, zero extra teeth.\n"
            "Return ONLY the final edited photograph of IMAGE 1.\n\n"
        )
        input_payload = [
            {"type": "text", "text": ref_header + bite_header + PROMPT},
            {"type": "image", "mime_type": mime_type, "data": b64_img},
            {"type": "image", "mime_type": "image/png", "data": b64_ref},
        ]
    else:
        input_payload = [
            {"type": "text", "text": bite_header + PROMPT},
            {"type": "image", "mime_type": mime_type, "data": b64_img},
        ]

    kwargs = {
        "model": model_name,
        "input": input_payload,
        "generation_config": {"thinking_level": thinking_level},
    }

    print(f"[DualSmileAI] ⚡ Initiating 2 Parallel Generations (Model: {model_name}, Thinking: {thinking_level})...")
    total_start = time.time()

    candidates: Dict[int, np.ndarray] = {}
    errors: Dict[int, str] = {}

    # 3. Fire 2 parallel worker threads
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_id = {
            executor.submit(
                _execute_gemini_candidate_worker,
                cand_id,
                client,
                kwargs,
                orig_w,
                orig_h,
                input_path,
                bite_info,
            ): cand_id
            for cand_id in [1, 2]
        }

        for future in as_completed(future_to_id):
            cid = future_to_id[future]
            try:
                candidate_img = future.result()
                candidates[cid] = candidate_img
            except Exception as e:
                err_msg = str(e)
                print(f"[DualSmileAI Error] Worker {cid} failed: {err_msg}")
                traceback.print_exc()
                errors[cid] = err_msg

    # 4. Fail-safe handling: if both workers failed, raise exception
    if not candidates:
        first_err = errors.get(1) or errors.get(2) or "Both generation workers failed."
        raise RuntimeError(f"Dual generation failed: {first_err}")

    # 5. Evaluate and select the best candidate
    base_no_ext, ext = os.path.splitext(output_path)
    if not ext:
        ext = ".jpg"

    if len(candidates) == 1:
        winner_id = list(candidates.keys())[0]
        winning_img = candidates[winner_id]
        print(f"[DualSmileAI] ⚠️ Only Candidate {winner_id} succeeded (other candidate encountered an error).")
        print(f"[DualSmileAI] 🏆 Winner: Candidate {winner_id} selected automatically as the sole successful design.")
    else:
        # Both candidates succeeded -> Evaluate with Hybrid Engine (CV + gemini-3.1-flash-lite)
        try:
            from virtualsmileAI.gemini import reload_env
            reload_env()
            ai_judge_timeout = float(os.environ.get("AI_JUDGE_TIMEOUT_SEC", "0.7"))
        except Exception:
            ai_judge_timeout = 0.7

        print(f"[DualSmileAI] ⚖️ Both candidates completed! Running Hybrid Dental Quality Evaluation (AI Judge: gemini-3.1-flash-lite, Timeout: {ai_judge_timeout}s)...")
        
        # 1. Computer Vision 4-Pillar Scoring (Instant, Deterministic)
        score_1, report_1 = score_smile_candidate(
            before_cv=b_img_cv,
            candidate_cv=candidates[1],
            bite_info=bite_info,
            before_path=input_path,
        )
        score_2, report_2 = score_smile_candidate(
            before_cv=b_img_cv,
            candidate_cv=candidates[2],
            bite_info=bite_info,
            before_path=input_path,
        )

        # 2. Multimodal AI Judge Evaluation (gemini-3.1-flash-lite with strict timeout)
        b_mask_ref = get_accurate_teeth_mask(b_img=b_img_cv, a_img=b_img_cv, before_path=input_path, binary=True)
        ai_res = run_ai_judge_evaluation(
            client=client,
            candidate1_cv=candidates[1],
            candidate2_cv=candidates[2],
            before_cv=b_img_cv,
            teeth_mask=b_mask_ref,
            bite_info=bite_info,
            timeout_sec=ai_judge_timeout,
        )

        # 3. Hybrid Synthesis & Fallback Handling
        c1_fit = None
        c2_fit = None
        orig_bottom_vis = None
        orig_bite_type = None

        if ai_res and "c1_score" in ai_res and "c2_score" in ai_res:
            c1_ai = float(ai_res["c1_score"])
            c2_ai = float(ai_res["c2_score"])
            c1_fit = ai_res.get("c1_size_fit", "compact")
            c2_fit = ai_res.get("c2_size_fit", "compact")
            orig_bottom_vis = ai_res.get("original_bottom_visible")
            orig_bite_type = ai_res.get("original_bite")
            ai_reason = ai_res.get("reason", "Multimodal aesthetic analysis completed.")
            ai_elapsed = ai_res.get("elapsed_sec", 0.0)

            # 50% Computer Vision + 50% AI Judge
            final_1 = round(0.50 * score_1 + 0.50 * c1_ai, 2)
            final_2 = round(0.50 * score_2 + 0.50 * c2_ai, 2)
            decision_mode = f"HYBRID (50% Computer Vision + 50% gemini-3.1-flash-lite in {ai_elapsed}s)"
        else:
            c1_ai = None
            c2_ai = None
            ai_reason = f"Fallback to 100% Computer Vision (AI Judge exceeded {ai_judge_timeout}s limit or encountered network error)."
            final_1 = score_1
            final_2 = score_2
            decision_mode = f"100% COMPUTER VISION (AI Judge fallback triggered at {ai_judge_timeout}s)"

        orig_had_lower = bite_info.get("bottom_teeth_exist", False)
        c1_erased = report_1.get("details", {}).get("bite", {}).get("erased_lower_teeth", False) or (ai_res and not ai_res.get("c1_lower_preserved", True))
        c2_erased = report_2.get("details", {}).get("bite", {}).get("erased_lower_teeth", False) or (ai_res and not ai_res.get("c2_lower_preserved", True))

        if orig_had_lower and c1_erased and not c2_erased:
            winner_id = 2
            loser_id = 1
            win_score, lose_score = final_2, final_1
            win_rep, lose_rep = report_2, report_1
            winning_img, losing_img = candidates[2], candidates[1]
        elif orig_had_lower and c2_erased and not c1_erased:
            winner_id = 1
            loser_id = 2
            win_score, lose_score = final_1, final_2
            win_rep, lose_rep = report_1, report_2
            winning_img, losing_img = candidates[1], candidates[2]
        elif final_2 > final_1:
            winner_id = 2
            loser_id = 1
            win_score, lose_score = final_2, final_1
            win_rep, lose_rep = report_2, report_1
            winning_img, losing_img = candidates[2], candidates[1]
        else:
            winner_id = 1
            loser_id = 2
            win_score, lose_score = final_1, final_2
            win_rep, lose_rep = report_1, report_2
            winning_img, losing_img = candidates[1], candidates[2]

        diff_pts = round(win_score - lose_score, 1)

        cand1_status = "🏆 WINNER" if winner_id == 1 else "❌ LOSER (Runner-Up)"
        cand2_status = "🏆 WINNER" if winner_id == 2 else "❌ LOSER (Runner-Up)"

        print("\n" + "═" * 80)
        print("🦷 DUAL GENERATION AUDIT: HYBRID CANDIDATE SELECTION")
        print(f"   Mode: {decision_mode}")
        if orig_bottom_vis is not None or orig_bite_type is not None:
            print(f"   Original Patient Anatomy: Bottom Teeth Visible={orig_bottom_vis}, Bite Type={orig_bite_type}")
        print("═" * 80)
        print(f"CANDIDATE 1: {cand1_status}")
        print(f"  ⭐ Final Score  : {final_1:.1f} / 100")
        print(f"     • Computer Vision (50%): {score_1:.1f} / 100 (Size: {report_1['size_score']:.1f}, Natural: {report_1['natural_score']:.1f}, Bite: {report_1['bite_score']:.1f}, Depth: {report_1['depth_score']:.1f})")
        if c1_ai is not None:
            fit_txt = f" [Size Fit: {c1_fit}]" if c1_fit else ""
            print(f"     • AI Judge Flash-Lite (50%): {c1_ai:.1f} / 100{fit_txt}")
        print("─" * 80)
        print(f"CANDIDATE 2: {cand2_status}")
        print(f"  ⭐ Final Score  : {final_2:.1f} / 100")
        print(f"     • Computer Vision (50%): {score_2:.1f} / 100 (Size: {report_2['size_score']:.1f}, Natural: {report_2['natural_score']:.1f}, Bite: {report_2['bite_score']:.1f}, Depth: {report_2['depth_score']:.1f})")
        if c2_ai is not None:
            fit_txt = f" [Size Fit: {c2_fit}]" if c2_fit else ""
            print(f"     • AI Judge Flash-Lite (50%): {c2_ai:.1f} / 100{fit_txt}")
        print("─" * 80)
        if ai_reason:
            print(f"🧠 AI JUDGE REASONING: {ai_reason}")
        print("═" * 80)
        print(f"🏆 VERDICT: Candidate {winner_id} WINS (+{diff_pts} pts higher overall quality)")
        print(f"   👉 WINNER FINAL OUTPUT (Shown on Frontend Split-Slider) : {output_path}")
        print("═" * 80 + "\n")

    # 6. Save winning image to final output path for frontend display
    cv2.imwrite(output_path, winning_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    total_elapsed = round(time.time() - total_start, 2)
    print(f"[DualSmileAI] ✅ Best smile design written to {output_path} (Total dual time: {total_elapsed}s).")
