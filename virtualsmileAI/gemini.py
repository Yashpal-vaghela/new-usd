import os
import base64
import requests
from typing import Optional
from PIL import Image, ImageDraw
from django.conf import settings
from google import genai

# ------------------------------------------------------------------
# Google Gemini official Interactions API configuration
# (Based on official documentation: https://ai.google.dev/gemini-api/docs/image-generation)
#
# Available Image Editing Models:
#   - gemini-nano-banana-2.1    (Nano Banana 2.1 - default, thinking-capable)
#   - nano-banana-pro-preview   (Nano Banana Pro preview)
#   - gemini-3.1-flash-image    (Gemini 3.1 Flash Image)
#   - gemini-3.1-flash-lite-image
#   - gemini-3-pro-image
#   - gemini-2.5-flash-image
#
# Thinking Level Options:
#   - "high"    (Required for strict dental boundary & lip-lock adherence)
#   - "medium"  (Google's default for Nano Banana 2.1)
#   - "minimal" (Faster, but can move lips and rush negative constraints)
# ------------------------------------------------------------------
# ------------------------------------------------------------------
# Direct Environment Configuration (.env driven)
# Changing GEMINI_MODEL_NAME or GEMINI_THINKING_LEVEL in .env will
# immediately update the flow at runtime without touching this code.
# ------------------------------------------------------------------
GEMINI_MODEL_DEFAULT = os.environ.get("GEMINI_MODEL_NAME", "gemini-nano-banana-2.1")
GEMINI_THINKING_LEVEL_DEFAULT = os.environ.get("GEMINI_THINKING_LEVEL", "medium")


def reload_env() -> None:
    """
    Dynamically re-reads .env from the project root on every request so any
    update made directly in .env immediately updates the runtime flow without
    needing a server restart or file edit.
    """
    try:
        from dotenv import load_dotenv
        base_dir = getattr(settings, "BASE_DIR", None) or os.getcwd()
        env_file = os.path.join(base_dir, ".env")
        if os.path.isfile(env_file):
            load_dotenv(env_file, override=True)
    except Exception:
        pass


def get_api_key() -> Optional[str]:
    """Read GEMINI_API_KEY from environment or Django settings, reloaded dynamically."""
    reload_env()
    return (
        os.environ.get("GEMINI_API_KEY")
        or getattr(settings, "GEMINI_API_KEY", None)
        or os.environ.get("GEMINI_API_KEY_NEW")
        or getattr(settings, "GEMINI_API_KEY_NEW", None)
    )


def get_model_name() -> str:
    """
    Get the normalized Google Gemini model identifier directly from .env.
    Dynamically re-reads .env so changing .env updates the active flow immediately.
    """
    reload_env()
    raw_name = (
        os.environ.get("SMILE_GEMINI_MODEL_NAME")
        or os.environ.get("GEMINI_MODEL_NAME")
        or os.environ.get("GEMINI_MODEL")
        or getattr(settings, "GEMINI_MODEL_NAME", None)
        or GEMINI_MODEL_DEFAULT
    )
    name = (raw_name or "").strip().strip('"\'')
    if name in ["nano-banana-2.1", "gemini-nano-banana-2.1"]:
        return "gemini-nano-banana-2.1"
    if name in ["nano-banana-pro", "nano-banana-pro-preview"]:
        return "nano-banana-pro-preview"
    if name in ["3.1-flash-image", "gemini-3.1-flash-image"]:
        return "gemini-3.1-flash-image"
    if name in ["3.1-flash-lite-image", "gemini-3.1-flash-lite-image"]:
        return "gemini-3.1-flash-lite-image"
    if name in ["3-pro-image", "gemini-3-pro-image"]:
        return "gemini-3-pro-image"
    if name in ["2.5-flash-image", "gemini-2.5-flash-image"]:
        return "gemini-2.5-flash-image"
    return name


def get_thinking_level() -> str:
    """
    Get thinking level directly from .env: 'high', 'medium', or 'minimal'.
    Dynamically re-reads .env so changing .env updates the active flow immediately.
    """
    reload_env()
    raw = (
        os.environ.get("SMILE_GEMINI_THINKING_LEVEL")
        or os.environ.get("GEMINI_THINKING_LEVEL")
        or os.environ.get("THINKING_LEVEL")
        or getattr(settings, "GEMINI_THINKING_LEVEL", None)
        or GEMINI_THINKING_LEVEL_DEFAULT
    )
    level = (raw or "").strip().lower().strip('"\'')
    if level in ["high", "medium", "minimal"]:
        return level
    return "medium"
# --------------------------------------------------Prompt for Ai 1----------------------------------------------------------------------------------- 
# PROMPT = r"""
# TASK: Using [INPUT_IMAGE], perform a high-end cosmetic dentistry digital smile design. Only modify the visible teeth – all other features must remain unchanged.

# ⚠️ Non-Negotiable Constraints

# Facial Integrity: Do not alter any part of the face (this includes lips, gums, skin, beard, hair, eyes, or facial expression). The subject’s smile and expression should remain natural – no forced smiles or lip adjustments.
# Background & Lighting: Preserve the original background, lighting, and shadows exactly as they are. Do not change, blur, or stylize any area outside the mouth. Everything around the face and in the environment must remain identical to the input.
# Framing & Perspective: Maintain the same camera angle, framing, and crop as the original image. No zooming, cropping, or re-centering is allowed. The output should align perfectly with the input image in perspective and composition.
# Strict Tooth Boundary Lock: The veneers must remain fully or pariallty as per smile inside the original tooth silhouettes as seen in the input photo. Do not expand beyond the original tooth edges (top, bottom, left, right). No scaling up, no widening, no lengthening.
# No Smile Expansion: Do not increase the amount of visible teeth or show additional teeth. Keep the same number of visible teeth and the same exposure.

# 😁 Smile Design (Teeth Only)
# Transformation Scope: Replace only the visible teeth with high-end, beautifully crafted e.max veneers. The new teeth should be symmetrical and naturally aligned, following the exact layout of the original teeth (do not reveal more teeth than are originally visible, and do not alter the gum line). Each veneer should sit precisely where the original tooth is.
# Shade & Harmony: Select the veneer shade dynamically based on the subject’s natural skin tone to ensure realism and harmony:
# Darker skin tones: Use shade A3 (a warm, natural white with depth that complements deeper complexions).
# Medium or wheatish skin tones: Use shade A2 (a balanced, soft natural white).
# Fair or light skin tones: Use shade A1 (a bright yet realistic white).
# Avoid any overly bleached, chalky look – the veneers should be clean and bright but still believable for the individual’s complexion. They must appear healthy and premium in color, without looking fake.
# Color Consistency: Ensure the new teeth have even, consistent coloration with no spots, streaks, or discoloration. The enamel shade should transition naturally from the slightly warmer tone near the gum to a subtle translucency at the tips, mimicking real teeth. There should be no staining or blotches – the veneers must look impeccably clean and evenly shaded (while still showing gentle gradation like natural teeth). This aligns with the ideal that a tooth shade should harmonize with one’s appearance and stay free of discoloration over time.
# Anatomical Realism: The veneers must have realistic dental anatomy and texture:
# Tooth Separation: Each tooth should be clearly individually defined with a natural outline. Do not let veneers merge or blur together – there should be subtle, clean lines or slight gaps where teeth meet, just like real teeth.
# Translucency & Texture: Incorporate subtle enamel translucency towards the incisal edges (the biting tips of the teeth) – a slight see-through quality at the edges that real enamel often has. Also include natural surface textures and micro-details (fine textures or luster) so they catch light realistically, rather than looking flat.
# Micro-Asymmetry: Introduce very slight, natural variations in tooth shape or positioning (for example, a tiny variation in the contour or angle of a tooth) to avoid a “cookie-cutter” appearance. Real smiles have minor asymmetries that give them character. The veneers should not look unnaturally identical or overly uniform – they should be perfectly aligned and proportional yet with a touch of individuality for realism.
# Lip & Mouth Integration: The new teeth must fit seamlessly into the existing mouth without altering any surrounding tissues:
# The veneers should sit under the existing lip line exactly. Do not change the position or shape of the lips or the amount of gums showing. The lips in the image should look untouched and naturally draped over the teeth as they originally were.
# Maintain Original Tooth Size: Keep each tooth’s height and width the same as in the original image. Do not make the teeth longer, wider, or bulkier than they originally appear. This ensures the veneers do not look too large or out-of-place. The overall smile line (the curve of the teeth as it follows the lip) should remain unchanged.
# Ensure the gumline and teeth junction is clean and natural. Do not alter the gums’ color or shape. There should be no dark edges or obvious lines at the gum-teeth interface – the veneers should appear to emerge naturally from the gums.
# Tooth Size & Proportion: Veneers must strictly match the original visible tooth dimensions. Do not increase height or width beyond what is naturally present in the input image.
# Teeth should never appears with too wider and longer than input image. The design must preserve the subject’s natural smile curve.
# Slight improvements for symmetry are allowed. Always prioritize natural realism over geometric correction.
# Veneers must fit entirely within the original tooth contour – no extension past gumline, lips, or spacing.
# The smile should look harmonious and balanced, not artificial or “overdone.”
# Lighting Consistency: The replaced teeth must match the lighting of the original photo perfectly:
# Retain the same highlights and shadows on the teeth that would be present given the scene’s lighting. For example, if the light in the original image comes from above or one side, the veneers should show corresponding gentle highlights on that side and soft shadows where appropriate, just like real teeth under those conditions.
# The reflection and shine on the veneers should mirror what real teeth would reflect in that environment (no excessive gloss beyond what the original lighting suggests).
# Do not introduce any new light sources or unnatural glare. The goal is that the new teeth appear as if they were always part of the original image, with coherent lighting and shadowing around the mouth. All ambient shadows and lighting on the face remain unchanged, and the teeth should blend into that light seamlessly.
# Flawless Final Result: The final smile should look impeccably realistic and aesthetically stunning:
# The veneers must be high-end and flawless – as if a top cosmetic dentist did the work. They should show no imperfections like chips, cracks, or rough edges. Each tooth’s edges should be smooth and well-defined (unless the original had a certain unique edge shape that should be preserved).
# Use e.max veneers for their renowned quality – they are ultra-thin and have life-like translucency, enabling a very natural look. This means the new teeth should exhibit the slight glassy depth that real enamel has, enhancing realism.
# There should be no artifacts or errors from the editing process: no double exposure of teeth, no blurred areas, no mismatched colors. Everything about the teeth should look deliberate and naturally photographical.
# Overall, the outcome must radiate a premium yet natural smile. It should look like the person simply has perfect, healthy teeth. Anyone viewing the image should not detect it was digitally altered – it should look like a real, high-quality photograph of a person with a beautiful, naturally harmonious smile.
# """

# --------------------------------------------------New updated last use Prompt for Ai 2(30-04) yashpal-----------------------------------------------------------------------------------    
# PROMPT = r"""
# TASK: Using [INPUT_IMAGE], perform a high-end cosmetic dentistry digital smile design. Only modify the visible teeth – all other features must remain unchanged.

# ⚠️ Non-Negotiable Constraints

# Facial Integrity: Do not alter any part of the face (this includes lips, gums, skin, beard, hair, eyes, or facial expression). The subject’s smile and expression should remain natural – no forced smiles or lip adjustments.
# Background & Lighting: Preserve the original background, lighting, and shadows exactly as they are. Do not change, blur, or stylize any area outside the mouth. Everything around the face and in the environment must remain identical to the input.
# Framing & Perspective: Maintain the same camera angle, framing, and crop as the original image. No zooming, cropping, or re-centering is allowed. The output should align perfectly with the input image in perspective and composition.
# Strict Tooth Boundary Lock: The veneers must remain fully or pariallty as per smile inside the original tooth silhouettes as seen in the input photo. Do not expand beyond the original tooth edges (top, bottom, left, right). No scaling up, no widening, no lengthening.
# No Smile Expansion: Do not increase the amount of visible teeth or show additional teeth. Keep the same number of visible teeth and the same exposure.

# 😁 Smile Design (Teeth Only)
# Transformation Scope: Replace only the visible teeth with high-end, beautifully crafted e.max veneers. The new teeth should be symmetrical and naturally aligned, following the exact layout of the original teeth (do not reveal more teeth than are originally visible, and do not alter the gum line). Each veneer should sit precisely where the original tooth is.
# Shade & Harmony: Select the veneer shade dynamically based on the subject’s natural skin tone to ensure realism and harmony:
# Set shade according to skin tone not make too much white or too dull.
# Select veneer shades that complement the subject’s complexion – warm ivory tones (A1, B1) suit medium/olive skin, while brighter yet natural shades (BL1, B1 or A2) flatter deeper complexions.
# Avoid any overly bleached, chalky look – the veneers should be clean and bright but still believable for the individual’s complexion. They must appear healthy and premium in color, without looking fake.
# Color Consistency: Ensure the new teeth have even, consistent coloration with no spots, streaks, or discoloration. The enamel shade should transition naturally from the slightly warmer tone near the gum to a subtle translucency at the tips, mimicking real teeth. There should be no staining or blotches – the veneers must look impeccably clean and evenly shaded (while still showing gentle gradation like natural teeth). This aligns with the ideal that a tooth shade should harmonize with one’s appearance and stay free of discoloration over time.
# Anatomical Realism: The veneers must have realistic dental anatomy and texture:
# Tooth Separation: Each tooth should be clearly individually defined with a natural outline. Do not let veneers merge or blur together – there should be subtle, clean lines or slight gaps where teeth meet,no wider and longer veneer of front two center teeth just like real teeth.
# Translucency & Texture: Incorporate subtle enamel translucency towards the incisal edges (the biting tips of the teeth) – a slight see-through quality at the edges that real enamel often has. Also include natural surface textures and micro-details (fine textures or luster) so they catch light realistically, rather than looking flat.
# Incorporate refined enamel translucency at the incisal edges, paired with natural surface textures and micro-details, ensuring each tooth interacts with light to deliver a lifelike depth, brilliance, and premium aesthetic.
# Micro-Asymmetry: Introduce very slight, natural variations in tooth shape or positioning (for example, a tiny variation in the contour or angle of a tooth) to avoid a “cookie-cutter” appearance. Real smiles have minor asymmetries that give them character. The veneers should not look unnaturally identical or overly uniform – they should be perfectly aligned and proportional yet with a touch of individuality for realism.
# Lip & Mouth Integration: The new teeth must fit seamlessly into the existing mouth without altering any surrounding tissues:
# The veneers should sit under the existing lip line exactly. Do not change the position or shape of the lips or the amount of gums showing. The lips in the image should look untouched and naturally draped over the teeth as they originally were.
# Maintain Original Tooth Size: Keep each tooth’s height and width the same as in the original image. Do not make the teeth longer, wider, or bulkier than they originally appear. This ensures the veneers do not look too large or out-of-place. The overall smile line (the curve of the teeth as it follows the lip) should remain unchanged.
# Ensure the gumline and teeth junction is clean and natural. Do not alter the gums’ color or shape. There should be no dark edges or obvious lines at the gum-teeth interface – the veneers should appear to emerge naturally from the gums.
# Tooth Size & Proportion: Veneers must strictly match the original visible tooth dimensions. Do not increase height, width, and length beyond what is naturally present in the input image.
# Teeth should never appears with too wider and longer than input image. Also Teeth color shade match with skin tone.The design must preserve the subject’s natural smile curve.
# Slight improvements for symmetry are allowed. Always prioritize natural realism over geometric correction.
# Veneers must fit entirely within the original tooth contour – no extension past gumline, lips, or spacing.
# The smile should look harmonious and balanced, not artificial or “overdone.”
# Lighting Consistency: The replaced teeth must match the lighting of the original photo perfectly:
# Retain the same highlights and shadows on the teeth that would be present given the scene’s lighting. For example, if the light in the original image comes from above or one side, the veneers should show corresponding gentle highlights on that side and soft shadows where appropriate, just like real teeth under those conditions.
# The reflection and shine on the veneers should mirror what real teeth would reflect in that environment (no excessive gloss beyond what the original lighting suggests).
# Do not introduce any new light sources or unnatural glare. The goal is that the new teeth appear as if they were always part of the original image, with coherent lighting and shadowing around the mouth. All ambient shadows and lighting on the face remain unchanged, and the teeth should blend into that light seamlessly.
# Flawless Final Result: The final smile should look impeccably realistic and aesthetically stunning:
# The veneers must be high-end and flawless – as if a top cosmetic dentist did the work. They should show no imperfections like chips, cracks, or rough edges. Each tooth’s edges should be smooth and well-defined (unless the original had a certain unique edge shape that should be preserved).
# Use e.max veneers for their renowned quality – they are ultra-thin and have life-like translucency, enabling a very natural look. This means the new teeth should exhibit the slight glassy depth that real enamel has, enhancing realism.
# There should be no artifacts or errors from the editing process: no double exposure of teeth, no blurred areas, no mismatched colors. Everything about the teeth should look deliberate and naturally photographical.
# Overall, the outcome must radiate a premium yet natural smile. It should look like the person simply has perfect, healthy teeth. Anyone viewing the image should not detect it was digitally altered – it should look like a real, high-quality photograph of a person with a beautiful, naturally harmonious smile.
# """
# --------------------------------------------------New updatedPrompt for Ai craete by nikhil (12-09-2026)-----------------------------------------------------------------------------------

# PROMPT = r"""TASK:Create a conservative, photorealistic cosmetic smile preview by editing ONLY the visible tooth enamel inside the existing mouth opening.

# Use the input photograph as the absolute source of truth. The result must look like the EXACT same photograph with subtle, clean tooth improvements—not a newly generated face, not an altered expression, and not an enlarged smile.

# 🚨 NEVER OPEN UP THE MOUTH - STRICT APERTURE LOCK (HIGHEST PRIORITY):
# - DO NOT OPEN THE MOUTH. DO NOT INCREASE THE GAP OR DISTANCE BETWEEN THE LIPS UNDER ANY CIRCUMSTANCE.
# - If the mouth in the input photograph has a small, narrow, or subtle opening, KEEP THAT EXACT SMALL OPENING.
# - DO NOT PULL, DROP, ROLL, OR SHIFT THE LOWER LIP DOWNWARD. The lower lip must remain 100% frozen in its exact position.
# - DO NOT DROP THE JAW OR ELONGATE THE MOUTH OPENING VERTICALLY OR HORIZONTALLY.
# - The vertical distance (opening height) between the upper lip and lower lip must remain pixel-identical to the input image.
# - TEETH MUST BE CONSERVATIVE AND SHORT: The lower cutting edges (incisal edges) of the upper teeth must NOT extend downward below the original tooth line.
# - If the original teeth only show a 2mm to 4mm strip of enamel height, the new teeth MUST ONLY BE 2mm to 4mm TALL.
# - NEVER open the mouth or drop the bottom lip to fit standard-sized teeth. Fit small, low-profile teeth strictly inside the existing opening.
# - The upper boundary of the lower lip is an immovable barrier: teeth must stop immediately above the lower lip and never push it downward.

# 🚨 ZERO COLOR GRADING - 100% NORMAL ORIGINAL COLORS:
# - DO NOT APPLY ANY COLOR GRADING, COLOR FILTER, WARM TINT, SEPIA, OR TONE ADJUSTMENT TO ANY PART OF THE IMAGE.
# - The overall color palette, color temperature, white balance, contrast, and exposure must remain 100% NORMAL and pixel-identical to the original input photograph.
# - Skin tone, lip color, mustache/beard, eyes, hair, clothing, and background must have ZERO color grading, ZERO saturation boost, and ZERO warmth added.
# - The photograph must look raw, completely natural, and unedited—NOT like a photo that had a warm filter or color grading preset applied.

# 🚨 ABSOLUTE ZERO LIP MODIFICATION - STRICT LOCK:
# - DO NOT MOVE, WIDEN, STRETCH, RAISE, LOWER, OR RESHAPE THE LIPS.
# - DO NOT CHANGE LIP COLOR, TONE, SHADE, TEXTURE, OR CONTOURS UNDER ANY CIRCUMSTANCE.
# - If gums are not showing in the input image, GUMS MUST REMAIN 100% HIDDEN. NEVER push the upper lip up to reveal gums or full-height crowns.
# - Both upper and lower lips act as an impenetrable, frozen frame. Only modify the small visible enamel surface exposed between the lips.

# SMALL-TEETH SIZING & BOUNDARY LOCK - CRITICAL:
# - Match the exact visible height, width, and exposure of the original teeth.
# - If the original teeth are small, short, or partially hidden behind the lips, KEEP THEM SMALL AND SHORT.
# - If the upper lip drapes over the upper part of the teeth, KEEP IT DRAPED. Do NOT raise the lip or attempt to show full-height crowns. The upper teeth must remain naturally tucked beneath the upper lip.
# - Do NOT make teeth wider, longer, or bulkier. No oversized veneers.
# - Teeth must remain strictly behind the unchanged original lips.

# HEAD POSE AND DENTAL-PLANE MATCH - CRITICAL:
# - Infer the exact 3D head pose and dental orientation from the original nose, lips, jaw, and visible teeth. Match the original pitch, yaw, roll, and camera perspective.
# - All visible crowns must belong to the same 3D perspective as the head and rotate naturally with the face.
# - If the camera views the mouth from slightly below or above, respect that exact angle without forcing a straight-on dental view.

# 🚨 ONLY GENERATE TOP TEETH - NEVER INVENT BOTTOM TEETH (CRITICAL):
# - IF ONLY TOP TEETH ARE VISIBLE IN THE INPUT PHOTO, ONLY GENERATE AND ENHANCE THE TOP TEETH!
# - ABSOLUTELY NO NEED TO GENERATE BOTTOM TEETH.
# - DO NOT INVENT, FABRICATE, OR ADD A ROW OF BOTTOM TEETH.
# - DO NOT PULL DOWN, ROLL, STRETCH, OR MOVE THE BOTTOM LIP TO FIT OR REVEAL BOTTOM TEETH.
# - The space beneath the upper teeth must remain natural, dark oral cavity shadow, exactly as in the input photograph.
# - If bottom teeth are not clearly showing in the original photograph, ZERO bottom teeth must be drawn in the output.

# NATURAL TEETH ENAMEL & COLOR:
# - Clean, natural, healthy tooth enamel in a neutral, realistic dental shade that seamlessly matches the natural ambient lighting of the original photograph.
# - NO artificial yellow/warm color grading on the teeth.
# - NO unnatural bluish, chalky, or glowing whiteness. Just clean, healthy, natural teeth as seen in normal real-world lighting.
# - Render each visible tooth with subtle, natural human asymmetry, gentle alignment, and anatomically credible proportions.
# - Central incisors must NOT be enlarged, elongated, or made dominant.
# - Side teeth must not be widened or crowded into the corners of the mouth.

# REJECT THESE ARTIFACTS:
# - REJECT inventing or adding bottom teeth when only top teeth were visible in the input.
# - REJECT moving, pulling down, or altering the bottom lip to show bottom teeth.
# - REJECT opening up the mouth, dropping the jaw, or moving the lower lip downward.
# - REJECT any color grading, warm tint, color cast, or filter across the face or image.
# - REJECT any movement or shape alteration of the lips.
# - REJECT enlarged, lengthened, or widened teeth. If teeth are small in the input, they must stay small.
# - REJECT raising the upper lip to expose gums or full crowns when gums were not visible in the input.
# - REJECT oversized veneers, fake symmetry, or cartoonish whiteness.

# Before returning the image, verify:
# 1. If only top teeth were visible in the input, did you ONLY generate top teeth without adding any bottom teeth? (YES required - do not add bottom teeth).
# 2. Is the bottom lip 100% frozen in position, shape, and thickness, with zero movement to reveal bottom teeth? (YES required).
# 3. Did the mouth open up or did the lower lip move downward? (NO - mouth opening height and lower lip position MUST be identical to the input).
# 4. Are the new teeth short and confined strictly inside the original mouth opening without extending downward? (YES required).
# 5. Is the color grading completely normal, matching the exact original input image with NO color filter or warm tint? (YES required).
# 6. Are the lips 100% identical in position, width, height, shape, and color? (YES required).
# 7. Did any gums appear that were hidden before? (NO allowed).

# Return only the final edited photograph with no text, borders, or layout changes.
# """
# --------------------------------------------------New updatedPrompt for Ai craete by nikhil (08-10-2026)-----------------------------------------------------------------------------------
PROMPT = r"""TASK: In-place natural dental refinement of TEETH ONLY on the input photograph. Re-structure, align, and close gaps on visible teeth while strictly matching the original tooth color, natural matte/satin enamel finish, and ambient lighting with ZERO artificial shine or fake bleach look.

CRITICAL DIRECTIVE 1 — STRICT LIP & FACE LOCK (LIPS ARE OUTSIDE YOUR AREA):
- THE PATIENT'S LIPS MUST REMAIN 100% UNTOUCHED AND PIXEL-IDENTICAL TO THE ORIGINAL PHOTO.
- DO NOT FIX OR BEAUTIFY THE LIPS: Even if you think the lips look imperfect, crooked, uneven, asymmetrical, dry, thin, or not proper, DO NOT FIX, SMOOTH, OR ALTER THEM. The lips are strictly OUTSIDE of your editing area. Your sole task is inside the mouth on tooth enamel only.
- DO NOT TOUCH, RESHAPE, RECOLOR, THIN, THICKEN, PLUMP, OR ALTER THE LIPS IN ANY WAY.
- Preserve the exact upper lip drape, lower lip contour, lip corners (commissures), vermilion border, lip creases, and natural lip color/lipstick.
- DO NOT OPEN THE MOUTH WIDER, widen the smile, shift the mouth opening, or alter the facial expression.
- Keep the skin, facial hair, eyes, face, lighting, and background 100% UNTOUCHED and identical to the original photo.

CRITICAL DIRECTIVE 2 — LOCK TOP OF UPPER TEETH TO UPPER LIP (ZERO LINE OR GAP ABOVE TEETH):
- MAINTAIN NATURAL TOOTH HEIGHT: Do NOT pull down, lower, or unnaturally elongate the upper teeth downward into the mouth.
- The upper teeth must meet the bottom edge of the upper lip directly, leaving ZERO space, zero gap, zero border, and zero visible line between the top of the teeth and the upper lip.
- DO NOT DRAW A TOP BORDER OR CERVICAL OUTLINE ON THE UPPER TEETH: In the input photograph, the upper lip naturally overlaps the top of the teeth. Do NOT round off the top of the teeth crowns. The enamel must continue straight up into the upper lip drape, exactly matching the original photo.
- ABSOLUTELY ZERO GUM LINE ABOVE TOP TEETH: If no gumline is visible above the top teeth in the original photo, DO NOT generate or draw any line, margin, or tissue above them. The top contact boundary between teeth and upper lip must remain in the exact same vertical position as the original photo.

CRITICAL DIRECTIVE 3 — PRESERVE NATURAL ORAL CAVITY SHADOWS (DO NOT FILL THE MOUTH):
- RESPECT DARK MOUTH INTERIOR: The dark shadows, oral cavity depth, and empty space inside the mouth must remain 100% NATURAL DARK SHADOW.
- DO NOT FILL THE MOUTH WITH TEETH. Do NOT paint teeth across dark empty areas or into corners of the mouth where teeth were not visible.
- IF LOWER TEETH ARE NOT VISIBLE OR ARE IN SHADOW, DO NOT GENERATE LOWER TEETH. Leave the lower mouth in its original natural shadow.
- RESTRICT REFINEMENT STRICTLY TO THE EXISTING VISIBLE TOOTH FOOTPRINT: Only refine the exact teeth currently exposed. Do not expand the smile area or make the tooth display larger than in the original photo.

CRITICAL DIRECTIVE 4 — NO CARTOON FILTER OR STICKER OVERLAY:
- The teeth must NEVER look like a digital filter, sticker, or painted white overlay.
- In blurry, grainy, low-resolution, or dim webcam photos, the teeth MUST match the authentic photo texture, camera sensor noise, grain, low contrast, and lighting of the surrounding face.
- Do NOT draw high-contrast, opaque, glowing, or unnaturally sharp teeth over a grainy or dim photograph.
- The lighting on the teeth must be 100% consistent with the person's real facial lighting—dim in dim light, shadowed in shadow.

CRITICAL DIRECTIVE 5 — NO FAKE SHINE OR PLASTIC GLOSS:
- ABSOLUTELY ZERO FAKE HIGH-SHINE, SPECULAR HOT-SPOTS, OR GLOSSY PLASTIC HIGHLIGHTS.
- Real biological enamel has a soft, natural satin/semi-matte organic texture—it is NOT polished glass, wet plastic, or shiny acrylic.
- Do NOT add bright white shiny reflection spots on the front of each tooth.
- Teeth must look 100% authentic, organic, and real—NEVER like fake dentures, plastic teeth, or artificial veneers.

CRITICAL DIRECTIVE 6 — NARROW LIPS & SMALL VISIBLE TEETH (CROP NATURALLY):
- WHEN LIPS ARE NARROW OR TOOTH EXPOSURE IS SMALL:
  * Keep the narrow lips 100% UNCHANGED. Never widen, stretch, or pull open narrow lips to show more teeth.
  * No need to move teeth position or force full tall crowns.
  * If the narrow lips naturally crop or cut off the top or bottom of the teeth, THAT IS COMPLETELY FINE AND EXPECTED. Keep the teeth naturally cropped by the lips.
  * Simply refine whatever small visible enamel segments exist into a clean, structured, well-aligned, gap-free row of teeth within that exact narrow opening.
  * Make the small visible teeth neat, harmonious, and structured without changing their compact footprint or their natural framing by the lips.

CRITICAL DIRECTIVE 7 — PRESERVE VERTICAL GAP / SPACE BETWEEN TOP AND BOTTOM TEETH:
- IF THERE IS VERTICAL SPACE OR A CENTRAL GAP BETWEEN UPPER AND LOWER TEETH:
  * PRESERVE THAT EXACT GAP: If the top teeth and bottom teeth do not touch in the original photo, DO NOT force them together.
  * The output image MUST maintain the vertical space, open bite, and dark gap between the upper and lower teeth lines, exactly like the input photo.
  * Do NOT elongate teeth vertically to close the space between upper and lower arches.
  * Close only horizontal spaces between neighboring teeth (side-by-side gaps) — NEVER close the vertical opening between the top and bottom arches.
  * Lips must remain 100% unchanged.

CRITICAL DIRECTIVE 8 — NATURAL PROPORTIONS & SIZE LOCK (DO NOT MAKE TOP TEETH BIG OR OVERSIZED):
- STRICTLY FORBIDDEN: DO NOT MAKE THE TOP TEETH BIG, LONG, WIDE, OR BULKY. OVERSIZED TEETH RUIN NATURALNESS.
- KEEP NATURAL TOOTH SCALE: The new teeth must strictly maintain the patient's authentic, natural tooth size, height, and width from the input photo.
- CENTRAL INCISORS MUST NOT BE ENLARGED: Never make the front central teeth oversized, dominant, elongated, or horse-like.
- IF TEETH ARE SMALL OR COMPACT IN INPUT, KEEP THEM SMALL AND COMPACT: Do NOT enlarge the teeth. Refine them into a neat, beautiful, symmetrical shape strictly within their original compact footprint.
- NATURAL BIOLOGICAL PROPORTIONS (GOLDEN PROPORTIONS): Maintain genuine dental harmony. Lateral incisors must remain slightly narrower and shorter than central incisors; canines must have subtle natural distinction.
- DO NOT ELONGATE BITING EDGES DOWNWARD: Never extend or stretch the incisal biting edges downward into the mouth opening or oral cavity. Keep the natural smile curve graceful and proportional.
- NATURAL BEAUTY OVER BULK: The teeth should look clean, aesthetic, and naturally beautiful—like the patient's own healthy, perfect teeth—NEVER like oversized, fake, bulky chicklet veneers.

THE TOOTH TRANSFORMATION PROTOCOL:
1. COMPLETE SIDE-BY-SIDE GAP CLOSURE (PRESERVE VERTICAL ARCH GAP):
- Completely close 100% of visible horizontal gaps, midline diastemas, and spaces between adjacent neighboring teeth.
- CRITICAL: Do NOT close vertical space or an open bite between the top and bottom tooth rows. If the top teeth line and bottom teeth line have a gap or space between them in the input photo, KEEP THAT EXACT GAP OPEN between the arches.
- Close side-by-side gaps by properly structuring and distributing space across adjacent teeth: subtly widen contact edges so neighboring teeth meet seamlessly with delicate, natural incisal embrasures — NEVER fuse teeth into a solid bar.

2. FLAWLESS SURFACE RESTORATION (CLEAN, SMOOTH ORGANIC ENAMEL):
- Smooth rough, chipped, or uneven tooth edges into clean, healthy, aesthetic natural enamel surfaces without any fake shiny coating.
- Even out discoloration and dark marks into a balanced, natural baseline enamel shade.

3. SYMMETRICAL ANATOMY & NATURAL ALIGNMENT (NO OVERSIZING):
- Re-contour visible teeth into balanced, aesthetic proportions strictly within their existing natural footprint.
- Correct chipping, uneven wear, tilting, rotation, and crowding without increasing tooth height or width.
- Level and smooth the incisal biting edges into a clean, symmetrical dental arch that fits naturally behind the unchanged lips without looking bulky.

4. ONLY REFINE TEETH THAT ARE ACTUALLY VISIBLE:
- If only upper front teeth are visible (lower teeth hidden or shadowed), refine ONLY those upper front teeth. NEVER generate lower teeth if they are in dark shadow or concealed by lips.
- If lower teeth ARE clearly exposed, refine them cleanly with proper individual boundaries.
- If teeth are in side corners or in shadow, keep them in their natural shadow.

5. MATCH ORIGINAL TOOTH COLOR & NATURAL LIGHTING (NO ARTIFICIAL BLEACH):
- STRICT COLOR MATCH: Match the patient's ORIGINAL natural tooth color, temperature, and undertone from the input photo (e.g., natural warm ivory, soft cream, or off-white).
- Do NOT bleach the teeth into an unnatural stark paper-white or glowing bleach shade.
- Even out discoloration and stains into the person's clean natural baseline tooth shade.
- NATURAL AMBIENT LIGHTING & ORAL SHADOWS:
  * Do NOT light up the teeth artificially like lightbulbs.
  * Teeth deeper inside the mouth must sit naturally in the soft shadow of the oral cavity.
  * Tooth brightness must perfectly match the surrounding skin and photo exposure—if the photo is a webcam, indoor room, or dim lighting, teeth must stay completely natural in that exact light.

6. MATCH CAMERA BLUR, FOCUS & GRAIN (SEAMLESS RESOLUTION MATCH):
- STRICT BLUR & SHARPNESS MATCH: The restored teeth MUST match the exact amount of camera blur, lens softness, focal depth, grain, and sensor noise that the input photo contains.
- If the input photo is soft, slightly blurry, or has low-resolution/webcam softness, the generated teeth MUST have that EXACT same degree of blur and softness.
- Absolutely DO NOT render the teeth with hyper-crisp, razor-sharp, or ultra-HD definition if the surrounding face, lips, and image contain natural blur or softness.
- The optical focus, blur radius, pixel texture, and grain of the teeth must blend 100% seamlessly with the rest of the image so they never look artificially sharp or pasted in.

PRE-RETURN AUDIT:
- Are the LIPS 100% identical to the original photo with ZERO attempt to "fix", smooth, or reshape them (lips are outside editing area)? (YES, STRICTLY UNTOUCHED).
- Are the top teeth natural in size and proportion WITHOUT being enlarged, elongated, or made too big? (YES, PERFECT NATURAL HUMAN TOOTH SCALE).
- Do the teeth look like authentic, good-looking natural teeth rather than oversized veneers or bulky chicklets? (YES, AUTHENTIC NATURAL DENTAL ANATOMY).
- Is the dark mouth interior/oral cavity shadow preserved without being filled up with teeth? (YES).
- Was zero gum tissue generated where none existed in the input photo? (YES).
- Do the teeth blend with the authentic photo grain, blur, and lighting rather than looking like a cartoon filter or sticker? (YES).
- If lower teeth were hidden in shadow in the original, are they STILL in shadow with no fake lower teeth drawn? (YES).
- If the lips are narrow and tooth exposure is small, did the lips remain unchanged with small teeth cleanly structured and naturally cropped? (YES).
- If there was vertical space or a gap between top and bottom teeth in the input photo, is that gap between the arches preserved without forcing teeth to touch? (YES).
- Are 100% of visible horizontal gaps and spaces between adjacent visible teeth completely closed? (YES).
- Do the top teeth extend all the way up to meet the upper lip directly with ZERO line, border, or gap created above them? (YES).
- Is the tooth color an authentic match to the patient's original natural tooth tone rather than an artificial bleach white? (YES).
- Are the teeth free of fake shiny reflections, glossy plastic glare, and artificial bright spots? (YES, NATURAL SATIN ENAMEL).

OUTPUT: Return only the final edited photograph with no text, watermark, borders, or side-by-side layout.
"""

PROMPT_CHAR_COUNT = len(PROMPT)


class PromptTooLongError(RuntimeError):
    """Retained for backwards-compatibility."""
    pass


def add_logo_on_right(image_path: str, logo_path: str) -> None:
    """Overlays the clinic logo on the bottom right corner with a subtle gradient shadow."""
    base = Image.open(image_path).convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")

    base_w, base_h = base.size
    shadow_height = int(base_h * 0.18)

    gradient = Image.new("RGBA", (base_w, shadow_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)
    for y in range(shadow_height):
        alpha = int(255 * (y / shadow_height))
        draw.line([(0, y), (base_w, y)], fill=(0, 0, 0, alpha))

    base.paste(gradient, (0, base_h - shadow_height), gradient)

    target_w = int(base_w * 0.20)
    ratio = target_w / logo.width
    target_h = int(logo.height * ratio)
    logo = logo.resize((target_w, target_h), Image.LANCZOS)

    padding_x = int(base_w * 0.02)
    padding_y = int(base_h * 0.02)
    x = base_w - target_w - padding_x
    y = base_h - target_h - padding_y

    base.paste(logo, (x, y), logo)
    base.convert("RGB").save(image_path, "JPEG", quality=95)


def generate_smile_design(input_path: str, output_path: str) -> None:
    """
    Sends input photograph + dental clinical refinement prompt directly to Google's
    official Gemini Interactions API using the official google.genai SDK.
    Follows official Google documentation:
      - input: [ {"type": "text", ...}, {"type": "image", ...} ]
      - generation_config: { "thinking_level": "high" }
    Guarantees pixel-perfect before/after slider alignment by preserving and restoring
    original image dimensions.
    """
    import io

    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not configured. "
            "Set env var GEMINI_API_KEY or Django setting GEMINI_API_KEY."
        )

    model_name = get_model_name()
    thinking_level = get_thinking_level()

    # Capture exact original dimensions for pixel-perfect comparison alignment
    with Image.open(input_path) as orig_img:
        orig_w, orig_h = orig_img.size

    print(f"[SmileAI] Model endpoint  : {model_name}")
    print(f"[SmileAI] Thinking level  : {thinking_level}")
    print(f"[SmileAI] Original size   : {orig_w}x{orig_h}")
    print(f"[SmileAI] Prompt length   : {PROMPT_CHAR_COUNT} chars")

    with open(input_path, "rb") as f:
        img_bytes = f.read()

    mime_type = "image/png" if input_path.lower().endswith(".png") else "image/jpeg"
    b64_img = base64.b64encode(img_bytes).decode("utf-8")

    client = genai.Client(api_key=api_key)

    # Official Google Gemini Interactions API format (Text prompt first to condition attention, image second)
    input_payload = [
        {"type": "text", "text": PROMPT},
        {"type": "image", "mime_type": mime_type, "data": b64_img},
    ]

    kwargs = {
        "model": model_name,
        "input": input_payload,
        "system_instruction": (
            "You are a professional cosmetic dentistry digital smile design engine. "
            "All input photographs are clinical dental portraits for patient aesthetic smile design simulation. "
            "Perform digital cosmetic veneer refinement on visible tooth enamel only."
        ),
        "generation_config": {"thinking_level": thinking_level},
    }

    try:
        interaction = client.interactions.create(**kwargs)

    except Exception as e:
        raise RuntimeError(f"Google Gemini Interactions API call failed: {str(e)}") from e

    # Extract thought commentary if available
    if hasattr(interaction, "steps") and interaction.steps:
        for step in interaction.steps:
            if getattr(step, "type", "") == "thought":
                summary = getattr(step, "summary", None) or []
                for cb in summary:
                    if getattr(cb, "type", "") == "text" and hasattr(cb, "text"):
                        print(f"[SmileAI Thought]: {cb.text.strip()}\n")

    if getattr(interaction, "output_text", None):
        print(f"[SmileAI Commentary]: {interaction.output_text}")

    if not interaction.output_image or not interaction.output_image.data:
        status_val = getattr(interaction, "status", "unknown")
        errors_val = getattr(interaction, "errors", None)
        print(f"[SmileAI Warning] Gemini returned no image. Status: {status_val}, Errors: {errors_val}")
        if status_val == "BLOCKED" or "block" in str(status_val).lower():
            raise RuntimeError(
                "Google Gemini safety moderation flagged this image. "
                "Ensure the photo shows the full lower face with clear lighting and is not cropped too tightly on the lips."
            )
        raise RuntimeError(
            f"Gemini did not return an output image. Status: {status_val} (Errors: {errors_val})"
        )

    raw_bytes = base64.b64decode(interaction.output_image.data)
    rendered_img = Image.open(io.BytesIO(raw_bytes))

    # Resize back to exact original canvas dimensions so split-slider has 0 pixel jitter
    if rendered_img.size != (orig_w, orig_h):
        print(f"[SmileAI] Resizing {rendered_img.size} -> ({orig_w}, {orig_h}) with Lanczos for 100% frame alignment.")
        rendered_img = rendered_img.resize((orig_w, orig_h), Image.LANCZOS)

    rendered_img.convert("RGB").save(output_path, "JPEG", quality=95)

    print(f"[SmileAI] AI smile design successfully generated and saved to {output_path} (size: {orig_w}x{orig_h})")