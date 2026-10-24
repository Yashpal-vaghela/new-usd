import os
import base64
from typing import Optional
from PIL import Image, ImageDraw
from django.conf import settings
from google import genai

# ------------------------------------------------------------------
# Google Gemini official Interactions API configuration
# (Based on official documentation: https://ai.google.dev/gemini-api/docs/image-generation)
#
# Model: gemini-nano-banana-2.1 (Nano Banana 2.1) - pure model without fallback models
# Thinking Level: minimal (Pure minimal thinking without fallback thinking)
# ------------------------------------------------------------------
GEMINI_MODEL_DEFAULT = "gemini-nano-banana-2.1"
GEMINI_THINKING_LEVEL_DEFAULT = "minimal"


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
    Returns 'gemini-nano-banana-2.1' (Nano Banana 2.1) - pure model without fallback models.
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
    name = (raw_name or "").strip().lower().strip('"\'')
    if "banana" in name or "2.1" in name or "nano" in name:
        return "gemini-nano-banana-2.1"
    # Pure gemini-nano-banana-2.1 without fallback models
    return "gemini-nano-banana-2.1"


def get_thinking_level() -> str:
    """
    Returns 'minimal' - pure minimal thinking without fallback thinking.
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
    if level == "minimal":
        return "minimal"
    # Pure minimal thinking without fallback thinking
    return "minimal"
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
# ===================================================================================================
# ===================================================================================================
# 💡 KEY AESTHETIC DIRECTIVES:
# - Exact Tooth Size Lock    : KEEP TEETH SIZE AS IT IS WHICH ORIGINAL INPUT CONTAINS! DO NOT MAKE TEETH WIDE OR TALL! Preserve exact original tooth height and width!
# - Scope Limit             : ONLY refine visible tooth enamel and visible gums (if visible) — DO NOT change the rest of the mouth!
# - Strict Gum Protocol     : IF GUM IS VISIBLE THEN ONLY CHANGES! Refine visible gums into healthy coral-pink scalloped margins. If gums are NOT visible, NEVER generate or reveal any gums!
# - Preserve Mouth Interior : Keep tongue, lower teeth, and natural oral depth 100% unchanged
# - Bottom Teeth Visibility : If bottom teeth are NOT visible in the input photo, DO NOT GENERATE THEM! Zero bottom teeth!
# - Strict Bottom Teeth Lock: When bottom teeth ARE visible, they MUST NEVER drop down, sink, or be pushed too much to the bottom! Keep bottom teeth standing tall at their authentic vertical baseline—never enlarge the gap or replace bottom teeth with tongue!
# - Connected Whole Smile   : If there is any gap between top and bottom bite line, FILL IT! Even if only two teeth attach, count as a connected WHOLE SMILE with both arches treated and beautifully aligned!
# - Protect Bottom Teeth    : When visible, keep authentic forward scale, vertical height, and full visibility! When not visible, DO NOT DRAW ANY!
# - Radiant Natural Shine   : MAXIMUM natural wet ceramic shininess! Dynamic, glistening specular highlights & liquid glaze! Enamel must gleam and catch light dynamically!
# - Lifelike Translucency   : PRONOUNCED glassy 3D incisal depth, incisal halo effect & natural light transmission! NEVER opaque flat white!
# - Organic Micro-Texture   : Fine anatomical vertical developmental lobes, gentle micro-ridges & perikymata! NEVER flat smooth plastic!
# - Authentic Dental Arch   : Faithfully follow patient's real dental curvature & alignment ('dent') — NEVER flat bar!
# - Flush In-Line Arch      : Front 2 teeth MUST NOT stick out forward or look outside the other teeth! Central incisors sit flush in-line with lateral incisors along one continuous arch!
# - Lighting & Warmth Match : 100% match face's ambient lighting & warmth — ZERO blue/cool tint!
# - Slender-Curvy Proportions: Delicate, slightly narrower width (NEVER extra wide, NEVER slightly big!)
# - Buccal Corridors & Cheeks: Never touch side cheeks or lip corners, keep natural spaces (in CRITICAL DIRECTIVE 3)
# ===================================================================================================
# --------------------------------------------------New updated Prompt for AI created by Nikhil (08-10-2026)-----------------------------------------------------------------------------------
PROMPT = r"""In-place photo edit: cosmetic smile makeover. Change ONLY the tooth enamel already visible in the photo.

GEOMETRY (most important):
- Same framing, zoom, crop, aspect ratio and dimensions as the input. Do not shift, rescale or re-center anything.
- Every tooth stays at its exact current pixel position: same upper incisal edge height, same lower tooth position, same arch width.
- Upper teeth never move up: their gum-side top edge stays tucked under the upper lip exactly as in the input, keeping the same soft shadow under the lip.
- Fill the entire visible mouth opening with the new teeth exactly as the original teeth fill it: same top edge, same bottom edge, same left/right extent. Do not move teeth up or down.
- Teeth stay strictly inside the existing mouth opening. Lips, lip line, mouth corners, gums, tongue, skin, beard and background stay pixel-identical. Do not open the mouth wider, raise the upper lip, lower the lower lip (including at the left and right corners), or reveal new gums. Lip thickness and shape stay exactly the same.

TEETH:
- Keep each tooth's original size and slender width. No enlarged, wide, or protruding teeth; front two incisors at original length.
- Straighten slightly, close gaps between neighbouring teeth, remove dark spots and black triangles, repair chips within the original outline.
- Shade: NATURAL healthy teeth, Vita A1-A2 soft ivory with slight natural colour variation (canines a touch warmer). NOT bleach white, NOT paper/chalk white, NOT Hollywood veneers. Matched to the photo's lighting (dimmer in dark photos).
- Individual teeth with natural 3D contours and high-gloss wet enamel: clear specular reflections and highlight streaks on the curved face of every tooth, following the photo's light direction, like a professional dental photo. Gloss on teeth only.
- Natural incisal edge: only the last ~1 mm of each front tooth's biting edge is translucent with a very faint bluish-grey tint, fading into the ivory body. The rest of the tooth is ivory, not blue. Never a hard line or stripe.
- Teeth sit INSIDE the mouth, recessed behind the lips: upper teeth do not protrude forward and are not enlarged; the upper lip slightly overlaps their top with a soft shadow; teeth follow the curved arch, getting smaller and darker toward the mouth corners.
- If lower teeth are visible, refine them the same way at their current position.

Output one photo only, no text or borders.
"""


LEGACY_PROMPT_2026_10_08 = r"""TASK
Create a natural cosmetic dental refinement of the supplied photograph. Edit all visible teeth across both upper and lower rows. Strictly preserve whether the smile is ATTACHED (upper and lower teeth touching with zero black gap) or OPEN (separated by a gap). Lock the top teeth in their exact original position (DO NOT MOVE TOP TEETH); keep upper teeth at their original compact short height and exact original front-two tooth size (NO RABBIT TEETH); if original teeth are small and do not fill the whole mouth, KEEP THEM SMALL (never generate big teeth or widen them across the mouth!); match the proportional size of top and bottom teeth, with top teeth only ~0.1mm larger than bottom teeth (almost equal in size); teeth must NOT be wide (slender vertical proportions are natural and acceptable, but NEVER widen teeth horizontally into wide chiclets); all teeth must sit naturally recessed strictly INSIDE the mouth corridor behind the lips so they fit perfectly within the protective lip blending mask without weird clipping; ELEVATE BOTTOM TEETH HIGH INSIDE THE MOUTH CAVITY — NEVER PUSH BOTTOM TEETH DOWN: The entire visible lower dental arch must be generated elevated and standing tall HIGH inside the mouth opening, immediately under the upper teeth — NEVER push bottom teeth down towards or into the lower lip! Because our post-processing pipeline applies a protective lower-lip mask, pushing bottom teeth down causes the mask to cover them up so only a tiny sliver is visible. Keeping bottom teeth elevated high inside the mouth aperture ensures their full crowns are 100% visible and beautifully exposed above the lower lip; fill the lower row with refined lower teeth touching the upper teeth when attached; close 100% of horizontal side-by-side gaps; remove all black dots between teeth; render rich natural wet-ceramic shininess across the tooth faces (strictly on teeth, zero on gums); and visibly generate a delicate, glass-like 0.5mm natural translucent edge strictly along the bottom horizontal cutting edges of the teeth (never in the center).

The source photograph is the sole authority for identity, lip boundaries, attached vs. open bite contact, small tooth scale, and perspective.

PRIORITY ORDER
When requirements conflict, apply this order:
1. Preserve non-dental anatomy, identity, lip boundaries, expression, and framing.
2. Preserve ATTACHED vs. OPEN bite exactly: if teeth touch with no black space in the source photo, keep upper and lower teeth 100% attached and touching with ZERO invented black gap above the lower lip.
3. Lock top teeth in their exact original position (DO NOT MOVE TOP TEETH) at their original compact height and front-two tooth size (ABSOLUTELY NO RABBIT/BUCK TEETH); if original teeth are small, KEEP THEM SMALL (NEVER generate big teeth across the whole mouth); match the size of top and bottom teeth, with top teeth only ~0.1mm larger than bottom teeth (almost equal in size); teeth must NOT be wide horizontally (slender vertical proportions are fine, but never wide); all teeth must sit strictly INSIDE the mouth opening so they fit seamlessly within the protective lip mask without weird clipping; LOWER TEETH MUST BE ELEVATED HIGH INSIDE THE MOUTH CAVITY (never pushed down towards or beneath the lower lip where the protective lower-lip mask would hide them, leaving only a tiny sliver — keep bottom teeth lifted high so 100% of their visible crowns remain clearly exposed above the lower lip); render visible lower teeth directly underneath them; close 100% of side-by-side horizontal gaps and remove all black interdental dots.
4. Keep the center/middle of every tooth 100% solid pearlescent white with rich natural wet shininess (strictly on teeth enamel, zero on gums), and visibly generate a delicate, glass-like 0.5mm micro-edge along the cutting tips (0.5mm ultra-thin micro-veneers, NOT bulky veneers).

1. PROTECTED IMAGE CONTENT
Keep all content outside the authorized dental edit 100% unchanged:
- Lips, lip borders, mouth corners (commissures), and mouth opening size.
- Cheeks, smile folds, skin tone, skin texture, and facial hair.
- Gums, tongue, and unrelated oral-cavity content.
- Eyes, glasses, hair, clothing, background, and composition.

Do not lift the upper lip, lower the lower lip, widen the smile, alter the expression, or reveal additional anatomy.
🚫 ZERO GUMS GENERATION — DO NOT GENERATE GUMS (STRICT UPPER LIP LOCK): Under NO circumstance should you generate, paint, or reveal new gums or expand the gumline upward! The upper teeth must terminate cleanly beneath the patient's existing natural upper lip contour. Do NOT push the upper lip up, do NOT alter the upper lip curve, and do NOT expose pink gums above the teeth. If gums are hidden in the source photo, keep them 100% hidden! Lips must remain 100% FROZEN in their exact original shape, thickness, and position.
Preserve the natural spaces at the extreme outer mouth corners (buccal corridors) without expanding the arch width into the cheeks.

2. ATTACHED SMILE vs. OPEN GAP RULE (CRITICAL — ZERO FAKE BLACK GAPS)
Match the vertical contact between upper and lower teeth 100% to the source photograph:

- CASE 1: IF TEETH ARE ATTACHED / TOUCHING IN THE SOURCE PHOTO (CLOSED BITE):
  * MAKE AN ATTACHED SMILE: When the upper and lower teeth touch or fill the vertical space between the upper and lower lips with no black gap in the source photo, they MUST remain 100% attached and touching in the output!
  * NEVER CREATE A BLACK GAP ABOVE THE LOWER LIP: Do NOT erase the lower teeth and do NOT paint a black space, dark void, or open gap between the upper teeth and the lower lip.
  * FILL THE LOWER ROW WITH TOUCHING LOWER TEETH: Keep the upper teeth at their original short height, and fill the space directly beneath the upper teeth (above the lower lip) with the visible lower teeth touching the bottom edge of the upper teeth—separated only by a fine, clean horizontal tooth-contact line.

- CASE 2: IF TEETH HAVE AN OPEN VERTICAL GAP IN THE SOURCE PHOTO (OPEN BITE):
  * KEEP OPEN ONLY WHEN ORIGINALLY OPEN: Only if the source photograph clearly shows an open dark space or separation between the upper and lower teeth, preserve that exact open gap without fusing the arches together.

3. STRICT SIZE LOCK — LOCK TOP TEETH, NO WIDE TEETH, ALMOST EQUAL TOP/BOTTOM SIZE (~0.1mm), & SEAMLESS MASK FIT
- ANCHOR TOP TEETH IN EXACT ORIGINAL POSITION (DO NOT MOVE TOP TEETH): The top teeth must NOT move! Never shift, raise, push down, displace forward, or alter the position of the upper teeth or upper arch! Keep the upper teeth firmly anchored at their exact original gumline, root positions, and horizontal coordinates from the source photograph.
- TEETH MUST NOT BE WIDE (SLENDER VERTICAL PROPORTIONS — OK IF SLIGHTLY LONG, BUT NEVER WIDE): Teeth must NEVER be wide, broad, or inflated horizontally! Do NOT widen teeth across the mouth and do NOT turn them into wide chiclets, wide blocks, or broad horse-like veneers. Slender, slightly long vertical proportions are completely natural and acceptable, but they must NOT be wide! Maintain narrow, slender individual tooth widths matching the subject's natural teeth. Preserve the natural dark negative space (buccal corridors) on both cheek sides.
- IF TEETH ARE SMALL & NOT IN WHOLE MOUTH — KEEP THEM SMALL (NEVER GENERATE BIG TEETH): If the patient's natural teeth are small, or if the smile shows small teeth that do not occupy the entire mouth opening, DO NOT generate big teeth! Never inflate small teeth into large chiclets, oversized crowns, or wide horse-like veneers. If the teeth are small in the source photo, keep them small, refined, narrow, and compact!
- MATCH PROPORTIONAL SIZE OF TOP & BOTTOM TEETH (TOP TEETH ONLY ~0.1mm LARGER — ALMOST EQUAL SIZE): Harmonize and match the proportional size and scale between the top and bottom teeth. Top teeth should be almost equal in size to bottom teeth, with top teeth only subtly larger by an anatomical margin of approximately 0.1mm, creating a balanced, authentic dental arch. NEVER generate huge upper teeth over small bottom teeth!
- ABSOLUTELY NO RABBIT / BUCK TEETH: The two front central incisors must NEVER look like rabbit teeth, beaver teeth, or buck teeth! They must NOT be elongated downward past adjacent teeth and must NOT flare forward.
- KEEP FRONT TWO TEETH AT EXACT ORIGINAL NATURAL SIZE: Preserve the exact original crown height and narrow width of the front two central incisors from the source photograph. Keep their bottom cutting edges level and harmonious with the adjacent lateral incisors.
- TEETH MUST SIT "INSIDE" THE MOUTH, NOT "OUTSIDE" (PERFECT FIT ON BLENDING MASK): Teeth must feel completely natural and recessed INSIDE the oral cavity, tucked comfortably behind the lips within the natural dental arch! NEVER make teeth feel like they are sitting outside the mouth or bulging forward against the lips! Our system applies a protective blending mask over the lips and facial skin: generating teeth strictly inside the mouth cavity ensures the mask fits seamlessly without clipping teeth or looking weird!
- ELEVATE BOTTOM TEETH HIGH INSIDE MOUTH (PREVENT TEETH GOING DOWN — FULL CROWN VISIBILITY ABOVE LOWER LIP MASK): Bottom teeth must NEVER be pushed downwards towards, into, or behind the lower lip! In our post-processing pipeline, the patient's real lower lip is strictly preserved and masked over the bottom of the mouth opening. If you render bottom teeth too low or pushed down, the lower lip mask will hide them and only a tiny sliver will be visible! You MUST generate the entire bottom row ELEVATED and standing tall HIGH inside the mouth aperture, right beneath the top teeth. Ensure 100% of the visible bottom teeth crowns sit comfortably ABOVE the lower lip inner border, fully exposed and visible without being cut off by the lip!
- 🚫 ABSOLUTE MOUTH BOUNDARY RULE — ALL TEETH GENERATED STRICTLY INSIDE THE MOUTH OPENING: Every single pixel of every generated tooth crown (upper AND lower) must be rendered STRICTLY within the interior of the visible mouth opening — the dark space bounded by the upper lip on top and the lower lip on the bottom. DO NOT generate ANY part of any tooth outside this boundary. ZERO tooth enamel should appear overlapping or touching the lip vermillion, the outer lip skin, or the surrounding facial skin. The bottom teeth base must terminate cleanly ABOVE the inner border of the lower lip — never pushed down onto or behind the lower lip. The upper teeth must not extend above the inner border of the upper lip. Think of the mouth opening as a strict container: every tooth must be drawn entirely inside this container with zero pixels spilling outside.
- NO BULKY OR THICK VENEERS (0.5mm ULTRA-THIN MICRO-VENEER LOOK): Do NOT create thick, bulky, or blocky veneers! The teeth must look like ultra-thin 0.5mm minimal-prep porcelain veneers with delicate, slender contours.
- PRESERVE AND REFINE LOWER TEETH IN PLACE: Whenever lower teeth sit between the upper teeth and the lower lip (even a thin or partial row), keep 100% of those lower teeth visible, standing tall against the upper teeth, and refine, align, and whiten them to match the upper row.
- SLENDER, COMPACT WIDTHS: Keep every upper and lower tooth at its original small, slender, compact width (never wide).

4. 100% SIDE-BY-SIDE GAP CLOSURE, BLACK-DOT REMOVAL & CHIP REPAIR AND DETAILED LOWER ARCHITECTURE
- CLOSE ALL SIDE-BY-SIDE HORIZONTAL GAPS: Close 100% of horizontal gaps and midline diastemas between adjacent side-by-side teeth within the same row at compact scale, without inflating tooth size.
- REMOVE ALL BLACK DOTS & DARK TRIANGLES BETWEEN TEETH:
  * Completely remove and fill every small black dot, dark pinhole, interproximal stain, and dark triangular pocket ("black triangle") between adjacent teeth or along the contact line between upper and lower teeth.
  * Replace dark interdental dots with clean, flush pearlescent enamel so zero black dots remain anywhere between the teeth.
- DETAILED LOWER ARCH ARCHITECTURE (IF VISIBLE): If the bottom teeth are visible in any amount, they MUST be fully generated and refined beneath the upper arch. Ensure they match the top teeth's natural size and spacing, and avoid any flat, fused "bar" or monolithic zipper look on the lower arch. Inspect and restore the natural 3D anatomical contours of every individual lower tooth. Sculpt each lower incisor and canine with its own distinct incisal edge, curved boundary, fine vertical developmental lines, mamelon-derived micro-ridges, and dark interproximal separation lines so they have authentic 3D structure, depth, and character matching the upper arch.
- SUBTLE 3D CONTOUR DEFINITION: Define individual teeth and the horizontal contact line between attached upper and lower rows using smooth, natural 3D enamel contours rather than black gaps or dark holes.
- CHIP REPAIR: Rebuild chipped or worn tooth edges smoothly within their original compact silhouettes.

5. NATURAL ORGANIC ENAMEL TRANSLUCENCY (INTEGRATED INSIDE TOOTH ANATOMY — NEVER A BLUE LINE OR BORDER STRIPE)
- AUTHENTIC HIGH-END CERAMIC VENEER TRANSLUCENCY: Teeth must look 100% natural, lifelike, and organic. Real enamel has subtle, natural light transmission through the internal 3D ceramic structure of the tooth crown.
- INTEGRATED 3D TRANSLUCENCY INSIDE ENAMEL (ZERO BLUE LINES): Translucency must be a smooth, natural, volumetric depth transition INSIDE the enamel body—NEVER an artificial blue line, NEVER a border stripe, and NEVER a colored edge drawn across teeth! The tooth crowns must retain their pure, natural pearlescent ivory tone (Vita A1/BL2) from root to tip.
- ZERO ARTIFICIAL BORDER STRIPES OR COLOR TINTS: Under NO circumstance should there be a blue, cyan, grey, or dark line running horizontally across the teeth or along the contact line between upper and lower rows! The upper and lower rows must meet naturally with clean, individually delineated enamel edges, completely free of any colored line or synthetic border.
- ZERO TRANSLUCENCY ON GUMS, LIPS, OR SURROUNDINGS: Keep teeth clean and natural; gums remain matte coral-pink; lips remain 100% frozen.

6. NATURAL ENAMEL WET SHININESS AND SPECULAR HIGHLIGHTS (STRICTLY ON TEETH — ZERO ON GUMS)
- VIBRANT NATURAL LIQUID SHININESS: Coat 100% of visible tooth enamel in a natural, glistening wet saliva glaze (healthy hydrated dental enamel sheen). The enamel surface must gleam with attractive, realistic specular shine!
- CRISP NATURAL SPECULAR HIGHLIGHTS ACROSS TOOTH FACES: Render crisp, bright specular light reflections, natural highlight ribbons, and glistening micro-glints across the vertical developmental ridges and curved facial lobes of both upper and lower visible teeth. The enamel must catch ambient lighting with lively, authentic specular contrast so teeth look authentically wet, hydrated, and alive.
- SUBTLE NATURAL OPTICAL DEPTH: The bottom 0.5mm cutting edge displays subtle, natural ceramic optical depth against the oral cavity background.
- STRICT MANDATORY EXCLUSION (TEETH ENAMEL ONLY — ZERO ON GUMS OR SURROUNDINGS): Apply wet shine, specular highlights, and gloss STRICTLY AND EXCLUSIVELY to tooth enamel crowns! DO NOT apply shine, specular highlights, or gloss to gums, lips, beard, skin, tongue, or oral mucosa! Gums must remain 100% natural matte coral-pink with natural gingival stippling texture. Lips must retain their exact original soft matte texture.
- NATURAL MOUTH DEPTH & CAMERA BLEND: Allow the lower row and posterior side teeth to carry subtle, natural oral shading while sharing the same wet gloss, clean ivory tone, and detailed anatomical architecture. Match the source photo's ambient color temperature, focus softness, and sensor grain seamlessly.

7. FINAL SOURCE COMPARISON
Before returning the result, verify all conditions:
- If bottom teeth are visible in the original photo, are they fully generated, refined, and matching the upper arch directly underneath them, while keeping original bite contact attached (zero black gap)?
- Are all visible bottom teeth elevated high enough inside the mouth opening so their full crowns are completely visible and NOT pushed down into the lower lip where the lip mask covers them?
- Did the top teeth remain locked in their exact original position without moving or shifting?
- Are the teeth slender and NOT wide (slender vertical proportions are fine, but zero wide chiclets or bulky blocks)?
- If the original teeth are small and not occupying the whole mouth, did you keep them small rather than generating big teeth across the mouth?
- Are the top and bottom tooth sizes harmoniously matched, with top teeth only ~0.1mm larger than bottom teeth (almost equal in size)?
- Do the front two central incisors preserve their exact original natural size without any rabbit/buck tooth elongation?
- Do all teeth sit naturally INSIDE the mouth opening behind the lips, with zero unnatural forward protrusion or bulging outside, so the protective lip mask fits seamlessly without clipping or looking weird?
- Are ALL lower teeth cutting edges positioned ABOVE the lower lip inner border with a visible gap, so no tooth appears chopped off or pushed into the lip?
- Are the veneers slender and delicate (0.5mm ultra-thin minimal scale) rather than thick or bulky?
- Do the teeth look 100% natural, lifelike, and organic (authentic high-end dental ceramic veneer aesthetic—never artificial, chalky, or plastic)?
- Is there a delicate, natural semi-translucent 0.5mm incisal cutting edge along the tips with realistic optical depth, without blue, grey, or dark-colored bands or any center translucency?
- Do the teeth display rich, natural liquid wet specular shininess across both arches, while gums and lips remain completely matte and 100% natural?
- Are 100% of horizontal gaps and dark dots between teeth closed at compact scale?
- Are the lips, mouth opening, skin, and expression 100% unchanged?

OUTPUT
Return only one final edited photograph.
Preserve the source aspect ratio, framing, and dimensions.
No added text, watermark, border, collage, or before-and-after layout.
"""

PROMPT_CHAR_COUNT = len(PROMPT)

# Strength of the post-process enamel shine/reflection (1.0 = previous look). Override with SMILE_SHINE_GAIN.
SHINE_GAIN = float(os.environ.get("SMILE_SHINE_GAIN", "2.0"))
# Strength of the post-process incisal edge translucency (0 disables). Override with SMILE_EDGE_TRANSLUCENCY.
EDGE_TRANSLUCENCY = float(os.environ.get("SMILE_EDGE_TRANSLUCENCY", "1.0"))


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



def match_teeth_blur_and_whiteness(
    before_path: str,
    after_path: str,
    output_path: Optional[str] = None,
    bite_info: Optional[dict] = None,
) -> bool:
    """
    Measures the optical blur / softness and ambient luminance of the input photograph
    and adaptively matches the generated teeth to that exact blurriness and lighting.

    1. Optical Blur Matching (Resolves 'photo is low-res but teeth are HD'):
       If the input photo is soft or blurry (e.g. mobile camera, motion blur, webcam softness),
       hyper-crisp HD teeth look pasted-on. This function measures the input photo's facial
       softness and applies matching Gaussian blur to the teeth so their optical sharpness
       matches the photograph exactly.

    2. Adaptive Whiteness Balancing (Resolves 'teeth still look too white in some outputs'):
       Prevents teeth from looking unnaturally stark white, chalky, or fluorescent in dim
       or medium-lit photos. Compresses excessive luminance in CIELAB space to harmonize with
       the scene's ambient lighting while preserving enamel contrast, specular shine, and natural translucency.
    """
    if output_path is None:
        output_path = after_path

    try:
        import cv2
        import numpy as np

        if not os.path.isfile(before_path) or not os.path.isfile(after_path):
            return False

        b_img = cv2.imread(before_path)
        a_img = cv2.imread(after_path)
        if b_img is None or a_img is None:
            return False

        h, w = b_img.shape[:2]
        if a_img.shape[:2] != (h, w):
            a_img = cv2.resize(a_img, (w, h), interpolation=cv2.INTER_LANCZOS4)

        # 1. Retrieve oral aperture and YOLO enamel masks directly from seamless_blend.py
        from virtualsmileAI.seamless_blend import get_accurate_teeth_mask, _get_mask_from_yolo
        if bite_info and bite_info.get("cached_mask") is not None:
            mask = bite_info["cached_mask"]
            if mask.shape[:2] != (h, w):
                mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
        else:
            mask = get_accurate_teeth_mask(b_img=b_img, a_img=a_img, before_path=before_path, binary=True)

        if mask is None or np.sum(mask) == 0:
            print("[SmileAI BlurMatch] No mouth mask detected; skipping post-blur/whiteness match.")
            return False

        # Accurate teeth enamel mask for texture, shine, and shade enhancement
        yolo_teeth = _get_mask_from_yolo(a_img, conf=0.15)
        if yolo_teeth is not None and np.sum(yolo_teeth > 0) > 50:
            enamel_mask = yolo_teeth
        else:
            enamel_mask = mask

        # 2. Perioral Skin & Aperture Boundary Isolation
        skin_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (35, 35))
        dilated_mask = cv2.dilate(mask, skin_kernel)
        skin_mask = (dilated_mask > 0) & (mask == 0)

        b_gray = cv2.cvtColor(b_img, cv2.COLOR_BGR2GRAY)
        a_gray = cv2.cvtColor(a_img, cv2.COLOR_BGR2GRAY)

        # 3. Optical Blur / Softness Matching: Measure camera softness to match at final output pass
        orig_teeth_var = float(np.var(cv2.Laplacian(b_gray, cv2.CV_64F)[mask > 0]))
        curr_teeth_var = float(np.var(cv2.Laplacian(a_gray, cv2.CV_64F)[mask > 0]))
        target_var = max(5.0, orig_teeth_var * 1.08)

        # If AI teeth are noticeably sharper than the input photo, calculate matching Gaussian blur sigma
        best_sigma = 0.0
        if curr_teeth_var > target_var * 1.10:
            for s in np.arange(0.2, 3.0, 0.1):
                bl_gray = cv2.GaussianBlur(a_gray, (0, 0), s)
                v = float(np.var(cv2.Laplacian(bl_gray, cv2.CV_64F)[mask > 0]))
                if v <= target_var:
                    best_sigma = float(s)
                    break
        # Old cap of 0.30 never matched soft phone photos (teeth stayed ~6x sharper = "HD" look)
        best_sigma = min(2.5, best_sigma)

        print(f"[SmileAI BlurMatch] Input teeth var: {orig_teeth_var:.1f}, AI teeth var: {curr_teeth_var:.1f}, Target var: {target_var:.1f} -> best_sigma: {best_sigma:.1f}")

        # 4. Whiteness, Lighting & Ambient Luminance Balancing
        b_lab = cv2.cvtColor(b_img, cv2.COLOR_BGR2LAB)
        a_lab = cv2.cvtColor(a_img, cv2.COLOR_BGR2LAB)
        b_L = b_lab[:, :, 0]
        a_L = a_lab[:, :, 0].astype(np.float32)

        skin_L_90 = float(np.percentile(b_L[skin_mask], 90)) if np.sum(skin_mask) > 100 else 150.0
        orig_teeth_L_90 = float(np.percentile(b_L[mask > 0], 90))
        curr_teeth_L_80 = float(np.percentile(a_L[mask > 0], 80))

        # Target diffuse body luminance - Dynamically scales with face ambient lighting
        # Bright studio/daylight (skin_L_90 >= 140) -> 224.0 (crisp Vita A1/BL2 porcelain)
        # Normal indoor (skin_L_90 ~ 110) -> ~185.0 - 205.0
        # Dim/dark/night (skin_L_90 < 80) -> scales naturally down to 115.0 - 150.0 so teeth never glow like neon bulbs in the dark!
        ambient_scale = float(np.clip((skin_L_90 - 30.0) / 100.0, 0.0, 1.0))
        # Natural ivory, not bleach white: brightest-light cap is 208 (was 224)
        target_max_body_L = float(np.clip(115.0 + ambient_scale * (208.0 - 115.0), 115.0, 210.0))
        # Natural whitening is ~+30 L over the patient's own teeth; never far brighter than the face
        natural_cap = max(orig_teeth_L_90 + 30.0, skin_L_90 + 40.0)
        target_max_body_L = min(target_max_body_L, natural_cap)

        print(f"[SmileAI LightingMatch] Skin 90th L: {skin_L_90:.1f}, Orig teeth L: {orig_teeth_L_90:.1f}, Current teeth 80th L: {curr_teeth_L_80:.1f}, Target Lighting L: {target_max_body_L:.1f}")

        if curr_teeth_L_80 > target_max_body_L:
            diff = curr_teeth_L_80 - target_max_body_L
            print(f"[SmileAI LightingMatch] Harmonizing diffuse body lighting by {diff:.1f} points to match environment.")
            ratio = target_max_body_L / max(curr_teeth_L_80, 1.0)
            threshold = target_max_body_L * 0.90
            teeth_pixels = (mask > 0) & (a_L > threshold)
            if np.any(teeth_pixels):
                excess = (a_L[teeth_pixels] - threshold) / max(curr_teeth_L_80 - threshold, 1.0)
                excess = np.clip(excess, 0.0, 1.0)
                diffuse_factor = 1.0 - (1.0 - ratio) * excess
                a_L[teeth_pixels] = a_L[teeth_pixels] * diffuse_factor
                a_lab[:, :, 0] = np.clip(a_L, 0, 255).astype(np.uint8)

        # 5. Natural Pearlescent Ivory Shade Balancing (Vita A1 / Bleach BL2)
        # Avoids dingy yellow stain without artificial cyan tint
        kernel_3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        inner_enamel = cv2.erode((enamel_mask > 0).astype(np.uint8) * 255, kernel_3)
        feathered_weight = cv2.GaussianBlur(inner_enamel.astype(np.float32) / 255.0, (5, 5), 1.0)

        enamel_bool = feathered_weight > 0.05
        if np.sum(enamel_bool) > 50:
            a_B = a_lab[:, :, 2].astype(np.float32)
            mean_B = float(np.mean(a_B[enamel_bool]))

            # Natural shade = patient's own tooth warmth minus stain (b* 136-141): white, not bleach/blue.
            # Gemini's own strong blue patches (blue bands on the front teeth) -> lift to near neutral
            a_B = np.where(enamel_bool & (a_B < 133.0), a_B + (133.0 - a_B) * 0.8 * feathered_weight, a_B)
            mean_B = float(np.mean(a_B[enamel_bool]))

            orig_B = float(np.median(b_lab[:, :, 2][mask > 0]))
            target_B = float(np.clip(orig_B - 9.0, 136.0, 141.0))  # clean white, still a natural hint of ivory
            delta_B = target_B - mean_B
            if abs(delta_B) > 1.0:
                L_norm = np.clip(a_L / 200.0, 0.3, 1.0)
                a_B = np.clip(a_B + delta_B * L_norm * feathered_weight, 128.0, 255.0)
            a_lab[:, :, 2] = np.clip(a_B, 0, 255).astype(np.uint8)
            if abs(delta_B) > 1.0:
                print(f"[SmileAI Shade] Natural ivory: enamel b* {mean_B:.1f} -> {target_B:.1f} (original {orig_B:.1f}).")

        # 6. Automatic Lower-Lip Moisture & Specular Luster Sync
        lip_moisture_factor = 0.50
        try:
            from virtualsmileAI.seamless_blend import get_face_landmarker
            detector = get_face_landmarker()
            if detector is not None:
                import mediapipe as mp
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(b_img, cv2.COLOR_BGR2RGB))
                res = detector.detect(mp_img)
                if res.face_landmarks:
                    lms = res.face_landmarks[0]
                    lower_lip_indices = [14, 87, 178, 88, 95, 78, 61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317]
                    pts_lip = [[int(np.clip(lms[idx].x * w, 0, w - 1)), int(np.clip(lms[idx].y * h, 0, h - 1))] for idx in lower_lip_indices]
                    lip_poly = np.zeros((h, w), dtype=np.uint8)
                    cv2.fillPoly(lip_poly, [np.array(pts_lip, dtype=np.int32)], 255)
                    lip_pixels = b_L[lip_poly > 0]
                    if len(lip_pixels) > 50:
                        p95_lip = float(np.percentile(lip_pixels, 95))
                        p50_lip = float(np.percentile(lip_pixels, 50))
                        lip_spread = p95_lip - p50_lip
                        lip_moisture_factor = float(np.clip((lip_spread - 15.0) / 25.0, 0.25, 1.10))
                        print(f"[SmileAI LipMoisture] Lower-lip specular spread: {lip_spread:.1f} -> moisture factor: {lip_moisture_factor:.2f}")
        except Exception as e:
            print(f"[SmileAI LipMoisture Note]: {e}")

        # Combined Physical Luster Factor: 55% ambient skin lighting + 45% lower-lip moisture
        ambient_light_factor = float(np.clip((skin_L_90 - 80.0) / 100.0, 0.25, 1.0))
        env_factor = 0.55 * ambient_light_factor + 0.45 * lip_moisture_factor

        # 7. Environment-Adaptive Specular Shine & Glassiness (Strictly on Teeth Enamel — Zero on Gums)
        if np.sum(enamel_bool) > 50:
            a_L_channel = a_lab[:, :, 0].astype(np.float32)
            enamel_L = a_L_channel[enamel_bool]

            # High-pass filter for vertical developmental lobes & micro-ridges
            blur_lobe = cv2.GaussianBlur(a_L_channel, (0, 0), 1.2)
            lobe_detail = a_L_channel - blur_lobe

            # Morphological Top-Hat extracts crisp specular highlights & glints
            tophat_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            tophat = cv2.morphologyEx(a_L_channel.astype(np.uint8), cv2.MORPH_TOPHAT, tophat_kernel).astype(np.float32)

            # Lower percentile threshold to p70 so the shine covers natural curved highlights
            p70 = float(np.percentile(enamel_L, 70))
            specular_curve = np.clip((a_L_channel - p70) / max(255.0 - p70, 1.0), 0.0, 1.0) ** 1.4

            # In dark/dim lighting, scale specular and glint down so teeth don't shine overly in the dark
            ambient_shine_mult = float(np.clip((skin_L_90 - 35.0) / 95.0, 0.15, 1.0))

            # Natural wet enamel luster ribbons & micro-glints STRICTLY on enamel (feathered_weight = eroded enamel, 0.0 on gums)
            specular_boost = specular_curve * 12.0 * SHINE_GAIN * feathered_weight * ambient_shine_mult
            glint_boost = (tophat / 255.0) * specular_curve * 14.0 * SHINE_GAIN * feathered_weight * ambient_shine_mult
            lobe_boost = lobe_detail * 0.60 * feathered_weight

            # 3D optical depth across enamel gradient
            p25 = float(np.percentile(enamel_L, 25))
            shadow_depth = np.clip((p25 - a_L_channel) / max(p25, 1.0), 0.0, 1.0) * 3.5 * feathered_weight

            enhanced_L = a_L_channel + lobe_boost + specular_boost + glint_boost - shadow_depth
            a_lab[:, :, 0] = np.clip(enhanced_L, 0, 255).astype(np.uint8)
            print(f"[SmileAI SpecularShine] Applied natural wet shine strictly to enamel (specular=+{12.0*SHINE_GAIN*ambient_shine_mult:.1f}, glint=+{14.0*SHINE_GAIN*ambient_shine_mult:.1f}).")

        # 8. Incisal edge translucency: soft clear-enamel zone just above each upper biting edge.
        # Placed only where the enamel really ends over darkness below, so it can never become
        # a horizontal stripe across the teeth.
        if EDGE_TRANSLUCENCY > 0 and np.sum(enamel_bool) > 50:
            L_now = a_lab[:, :, 0].astype(np.float32)
            ys_e = np.where(enamel_bool)[0]
            arch_h = max(1, int(ys_e.max() - ys_e.min()))
            edge_px = int(np.clip(arch_h * 0.10, 4, 10))
            # Real darkness only (mouth cavity / contact line), not "anything that isn't enamel":
            # lower teeth meeting the lip must not get a translucent band
            dark = L_now < 0.6 * float(np.percentile(L_now[enamel_bool], 70))

            dist = np.full((h, w), edge_px + 1, dtype=np.float32)
            for k in range(edge_px, 0, -1):
                below = np.zeros_like(dark)
                below[:-k] = dark[k:]
                dist[below] = float(k)
            edge_w = np.clip(1.0 - (dist - 1.0) / edge_px, 0.0, 1.0) * enamel_bool

            # Upper arch only: lower teeth end in the lip at the bottom (never translucent there)
            if bite_info and bite_info.get("bottom_teeth_exist") and bite_info.get("valley_y") is not None:
                edge_w[int(bite_info["valley_y"]) + max(3, arch_h // 8):] = 0.0

            edge_w = cv2.GaussianBlur(edge_w.astype(np.float32), (0, 0), 1.0) * feathered_weight * EDGE_TRANSLUCENCY
            # Only bright enamel takes the tint: blue on the dark mouth cavity looks fake
            p70_L = float(np.percentile(L_now[enamel_bool], 70))
            edge_w *= np.clip((L_now - 0.6 * p70_L) / (0.3 * p70_L), 0.0, 1.0)
            # Soft blue-grey translucency fading into the ivory body (b* down = bluer)
            a_lab[:, :, 0] = np.clip(L_now * (1.0 - 0.10 * edge_w), 0, 255).astype(np.uint8)
            a_lab[:, :, 2] = np.clip(a_lab[:, :, 2].astype(np.float32) - 5.0 * edge_w, 0, 255).astype(np.uint8)
            print(f"[SmileAI EdgeTranslucency] Applied incisal translucency ({edge_px}px band, strength {EDGE_TRANSLUCENCY:.2f}).")

        a_img = cv2.cvtColor(a_lab, cv2.COLOR_LAB2BGR)

        # 9. Optical Camera Softness / Blur Matching (Final Lens Pass)
        if best_sigma > 0:
            print(f"[SmileAI BlurMatch] Applying optical blur (sigma={best_sigma:.1f}) to match camera lens softness.")
            feather_blur = cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (9, 9), 2.0)
            feather_blur_3 = np.repeat(feather_blur[:, :, np.newaxis], 3, axis=2)
            a_blurred = cv2.GaussianBlur(a_img, (0, 0), best_sigma)
            a_img = (a_blurred.astype(np.float32) * feather_blur_3 + a_img.astype(np.float32) * (1.0 - feather_blur_3)).astype(np.uint8)
            curr_post_var = float(np.var(cv2.Laplacian(cv2.cvtColor(a_img, cv2.COLOR_BGR2GRAY), cv2.CV_64F)[mask > 0]))
            print(f"[SmileAI BlurMatch] Post-blur teeth variance: {curr_post_var:.1f} (matched to original: {orig_teeth_var:.1f})")
        else:
            print("[SmileAI BlurMatch] Input image is crisp; preserving 100% sharp texture.")

        # 10. Camera grain: Gemini's teeth are noise-free, the photo is not. Add matching
        # luminance grain inside the mouth so the teeth belong to the same photo.
        b_gray_f = b_gray.astype(np.float32)
        a_gray_f = cv2.cvtColor(a_img, cv2.COLOR_BGR2GRAY).astype(np.float32)
        orig_noise = float(np.std((b_gray_f - cv2.GaussianBlur(b_gray_f, (0, 0), 1.5))[mask > 0]))
        curr_noise = float(np.std((a_gray_f - cv2.GaussianBlur(a_gray_f, (0, 0), 1.5))[mask > 0]))
        if orig_noise > curr_noise + 0.3:
            grain_std = float(np.sqrt(orig_noise ** 2 - curr_noise ** 2))
            rng = np.random.default_rng(0)
            grain = rng.normal(0.0, grain_std, (h, w)).astype(np.float32)
            grain = cv2.GaussianBlur(grain, (0, 0), 0.6) * 1.6  # soft, sensor-like grain
            mask_f = cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (9, 9), 2.0)
            a_img = np.clip(a_img.astype(np.float32) + (grain * mask_f)[:, :, np.newaxis], 0, 255).astype(np.uint8)
            print(f"[SmileAI Grain] Added camera grain to teeth (std {grain_std:.1f}; photo {orig_noise:.1f}, AI {curr_noise:.1f}).")

        cv2.imwrite(output_path, a_img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        return True

    except Exception as e:
        print(f"[SmileAI Warning] Optical blur/whiteness matching error: {e}")
        return False


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
        # Optimize image for Gemini API (max 1024px longest edge for fast upload & vision encoding)
        max_dim = max(orig_w, orig_h)
        if max_dim > 1024:
            scale = 1024.0 / max_dim
            send_w, send_h = int(orig_w * scale), int(orig_h * scale)
            optimized_img = orig_img.resize((send_w, send_h), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            if optimized_img.mode in ("RGBA", "P"):
                optimized_img = optimized_img.convert("RGB")
            optimized_img.save(buf, format="JPEG", quality=95, optimize=True)
            img_bytes = buf.getvalue()
            mime_type = "image/jpeg"
            print(f"[SmileAI] Optimized API payload: {orig_w}x{orig_h} -> {send_w}x{send_h} ({len(img_bytes)} bytes)")
        else:
            with open(input_path, "rb") as f:
                img_bytes = f.read()
            mime_type = "image/png" if input_path.lower().endswith(".png") else "image/jpeg"

    print(f"[SmileAI] Model endpoint  : {model_name}")
    print(f"[SmileAI] Thinking level  : {thinking_level}")
    print(f"[SmileAI] Original size   : {orig_w}x{orig_h}")
    print(f"[SmileAI] Prompt length   : {len(PROMPT)} chars")

    b64_img = base64.b64encode(img_bytes).decode("utf-8")

    client = genai.Client(api_key=api_key)

    # 1. Computer Vision Bite & Arch Pre-Scan
    import cv2
    import numpy as np
    from virtualsmileAI.seamless_blend import detect_bite_space_line

    b_img_cv = cv2.imread(input_path)
    bite_info = detect_bite_space_line(b_img_cv, before_path=input_path)

    if bite_info.get("has_space_line"):
        bite_header = "BITE (detected): both rows visible, OPEN - keep the existing dark gap between upper and lower teeth at exactly its current height; do not fill it and never make it bigger. Lower teeth stay fully visible at their current height and position.\n\n"
    elif bite_info.get("bottom_teeth_exist") or bite_info.get("is_touching_bite"):
        bite_header = "BITE (detected): both rows visible, TOUCHING - keep upper and lower teeth in contact exactly where they meet now; no new gap. Lower teeth stay at their current height and position.\n\n"
    else:
        bite_header = "BITE (detected): only upper teeth visible - do not add any lower teeth.\n\n"

    # 2. Reference Image for Incisal Translucency (translucency_reference.png)
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
            "- NATURAL TRANSLUCENCY REFERENCE: Emulate the natural incisal enamel natural translucency, internal mamelon depth, and delicate cutting edge halo shown in IMAGE 2 along the biting edges of visible teeth in IMAGE 1.\n"
            "- NATURAL ARCH & BITE INTEGRITY: Replicate ONLY the optical enamel natural translucency and mamelon texture from IMAGE 2. Do NOT copy IMAGE 2's single-arch layout, gumline, or tooth shape—IMAGE 1's authentic dual-arch geometry, bite space line, and full lower teeth MUST remain 100% intact!\n"
            "- FLAWLESS ENAMEL & RESTORATION: Rebuild any broken or chipped teeth with full solid enamel, with ZERO brown spots and zero residual defect. Obey all non-negotiable rules: freeze lips 100%, preserve authentic bite, zero extra teeth.\n"
            "Return ONLY the final edited photograph of IMAGE 1.\n\n"
        )
        input_payload = [
            {"type": "text", "text": ref_header + bite_header + PROMPT},
            {"type": "image", "mime_type": mime_type, "data": b64_img},
            {"type": "image", "mime_type": "image/png", "data": b64_ref},
        ]
        print("[SmileAI] Dental incisal natural translucency reference image active (IMAGE 2: translucency_reference.png).")
    else:
        ref_header = ""
        input_payload = [
            {"type": "text", "text": bite_header + PROMPT},
            {"type": "image", "mime_type": mime_type, "data": b64_img},
        ]

    kwargs = {
        "model": model_name,
        "input": input_payload,
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

    # 4. Match Optical Softness/Blurriness & Balance Whiteness to Input Photo
    try:
        match_teeth_blur_and_whiteness(
            before_path=input_path,
            after_path=output_path,
            output_path=output_path,
            bite_info=bite_info,
        )
    except Exception as e:
        print(f"[SmileAI Warning] Optical blur/whiteness matching note: {e}")

    # 5. Anatomical Lip-Lock & Space Line Shadow Guard
    try:
        from virtualsmileAI.seamless_blend import apply_seamless_lip_lock
        print("[SmileAI] Fetching and applying seamless lip-lock from seamless_blend.py...")
        blend_res = apply_seamless_lip_lock(
            before_path=input_path,
            after_path=output_path,
            output_path=output_path,
            bite_info=bite_info,
        )
        if blend_res:
            print("[SmileAI] Confirmed: Image successfully blended using seamless_blend.py")
        else:
            print("[SmileAI Warning] seamless_blend.py returned False, kept raw image.")
    except Exception as e:
        print(f"[SmileAI Warning] Seamless lip-lock post-process bypassed: {e}")

    print(f"[SmileAI] AI smile design successfully generated and saved to {output_path} (size: {orig_w}x{orig_h})")