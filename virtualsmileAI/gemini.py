import os
import base64
import requests
from typing import Optional
from PIL import Image, ImageDraw
from django.conf import settings
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
# --------------------------------------------------New updatedPrompt for Ai craete by nikhil (05-10-2026)-----------------------------------------------------------------------------------
PROMPT = r"""TASK: Create a conservative, photorealistic cosmetic smile preview by editing the supplied photograph.

Use the input photograph as the absolute source of truth. Replace only the visible enamel surfaces of teeth that already exist inside the original mouth opening. The result must look like the same unedited photograph with naturally improved teeth, not like a newly generated portrait or a generic set of veneers.

EDIT BOUNDARY - HIGHEST PRIORITY
- Keep the exact original mouth opening, lip contours, lip corners, expression, gumline, tongue, oral cavity, face, skin, hair, clothing, background, framing, focus, grain, and lighting.
- Teeth must remain behind the original lips and gums. Respect every original occlusion: anything hidden by a lip, gum, shadow, or another tooth stays hidden.
- Preserve upper and lower teeth independently. If even a small, partial patch of lower-tooth enamel is visible in the input, the lower teeth are considered visible and must remain visible in the result. Only when absolutely no lower enamel is visible may the lower arch remain hidden. Never expose a new tooth or complete a hidden dental arch.
- Keep the redesigned enamel within the original visible dental envelope. Do not widen the arch, enlarge the mouth, lower a lip, add gum, fill dark oral-cavity space, or extend white pixels into soft tissue.

HEAD POSE AND DENTAL-PLANE MATCH - CRITICAL
- First infer the exact 3D head pose and dental orientation from the original nose, lips, jaw, facial midline, and visible teeth. Match the original pitch, yaw, roll, occlusal plane, arch curvature, and camera elevation. Never default to a straight-on dental view.
- All generated crowns must belong to the same 3D perspective as the head. Their long axes, facial planes, side-to-side height, foreshortening, and incisal-edge curve must rotate naturally with the face and mouth.
- When the chin is raised or the camera views the mouth from below, render the upper teeth from that same slightly upward viewpoint: the crowns recede naturally upward and backward beneath the upper lip, with only anatomically appropriate subtle incisal thickness. Do not make the teeth face downward, hang vertically toward the camera, or look like a front-facing row pasted into an upward-tilted mouth.
- When the chin is lowered or the camera is above the mouth, apply the corresponding opposite perspective. Always copy the viewpoint demonstrated by the original visible teeth rather than inventing a new one.

UPPER ATTACHMENT AND FULL-CROWN CONTINUITY - CRITICAL
- Every upper crown must begin at its anatomically correct cervical origin at the original gumline, or continue naturally behind the upper lip where the gumline is occluded. It must remain physically attached to the upper dental arch.
- Replace the intended visible crown as one continuous enamel surface from its cervical origin to its incisal edge. Complete the upper portion within the established tooth footprint; do not generate only the lower half of a crown.
- Leave no dark horizontal band, black pocket, unfilled strip, original-tooth remnant, seam, or floating space between an upper tooth and its gum or upper-lip occlusion boundary.
- Never solve attachment by painting enamel over visible pink gum or genuine oral-cavity space. The correct result is a full crown emerging naturally from the existing gumline or disappearing naturally behind the unchanged upper lip.

LOWER-TEETH PRESERVATION - CRITICAL
- Inspect the input specifically for small, short, partially occluded, shadowed, or irregular lower teeth. Any visible lower enamel, however small, is mandatory image content and must not disappear in the result.
- Preserve the same lower-tooth locations, visible count, exposure height, silhouette, spacing, perspective, and occlusion behind the unchanged lower lip. Redesign only their already visible enamel surfaces at their original size.
- Rerender every visible lower-enamel surface as part of the same dental treatment as the upper arch. Do not leave original yellow stains, discoloration, old enamel patches, doubled edges, or a source-tooth layer showing beneath the redesign.
- Upper and lower teeth must share one coherent healthy ivory shade and photographic material response, with natural small variations but no isolated yellow tooth or yellow patch, especially at the lower-right or lower-left edges.
- Never replace visible lower teeth with black oral cavity, tongue, shadow, or empty space. Never interpret a short lower tooth as a highlight or non-dental detail.
- Upper teeth must not extend downward over the lower-tooth region, close the bite, reduce the original inter-arch opening, or hide lower teeth that were visible in the input.
- Maintain the original spatial relationship between the upper and lower arches. Preserve the original vertical separation or overlap and keep both arches on the same head-pose perspective.
- If lower-tooth visibility is uncertain, preserve the original visible lower enamel rather than deleting it. Do not invent portions that are fully hidden behind the lip.

NATURAL DENTAL DESIGN
- Create a healthy, gently aligned smile tailored to this person's existing dental arch, facial proportions, mouth opening, and camera angle. Correct distracting staining, chips, irregular edges, crowding, or spacing only within the visible dental envelope.
- Render every visible tooth as a separate anatomical tooth, not a repeated template. Preserve subtle human asymmetry; the left and right sides should be harmonious but not mirrored clones.
- Use credible anterior-tooth proportions: upper central incisors are subtly dominant, lateral incisors slightly narrower and usually a little shorter, canines have modest cusp definition and stronger corner curvature, and posterior teeth progressively recede with the arch perspective.
- Follow one smooth, natural smile arc that relates to the lower-lip curve without touching or moving the lip. Side teeth should appear naturally foreshortened as they turn away from the camera, while every originally visible side-tooth surface remains continuous, clearly readable enamel.
- Form believable contact areas and small incisal embrasures that gradually open toward the canines. Separate teeth through crown shape and a narrow, subtle, low-contrast value transition, never through black outlines, black wedges, or uniform gaps.
- Give each crown realistic convex facial planes, restrained line angles, softly varied incisal edges, and anatomically plausible thickness. Avoid perfectly flat faces, identical widths, identical lengths, or ruler-straight edges.

SIDE-TOOTH INTEGRITY - CRITICAL
- Preserve the complete visible enamel footprint of every original canine, premolar, and other side tooth. Do not erase, cut into, shorten, or cover any visible side-tooth enamel with oral-cavity darkness.
- The dark buccal corridor may exist only outside the distal edge of the outermost visible tooth, exactly where it exists in the input. Do not enlarge it or move it inward across a tooth.
- Never create a black triangle, wedge, notch, hole, stripe, stain, void, or near-black shadow on a visible tooth surface or at its gum transition.
- Interproximal separation must be minimal and softly graded. Do not introduce any separator or contact shadow darker or wider than the corresponding separation in the input photograph.
- If a side-tooth boundary is uncertain, preserve the continuous visible enamel supported by the input; never resolve uncertainty by painting a black gap.

ENAMEL AND PHOTOGRAPHIC REALISM
- Use natural healthy enamel in a warm-neutral ivory shade matched to the photograph's white balance. Teeth may be attractively bright, but never pure white, blue-white, gray, glowing, or uniformly one color.
- Treat all visible enamel in both arches as one atomic replacement. The final image must contain a single clean dental layer, never newly generated crowns overlaid on top of visible original teeth.
- Enamel and its contact shadows must contain no green, cyan, blue, purple, or other foreign-color speck, reflection, stain, edge pixel, or masking remnant. Replace any such artifact with continuous locally matched enamel color and texture.
- Include subtle cervical warmth, gentle value variation between teeth, slight incisal translucency, realistic internal depth, restrained specular highlights, and very fine enamel texture. These details must remain subtle at the input image's resolution.
- Match the original light direction, highlight size, shadows, sharpness, depth of field, noise, compression, and reflections. Keep side-tooth shading gentle and continuous, with no abrupt dark patches. Preserve oral-cavity darkness only in genuine non-tooth areas so the teeth feel embedded rather than pasted on.
- Produce a seamless tooth-to-gum and tooth-to-shadow transition with no halos, cutout edges, double teeth, overlapping enamel layers, or leftover stained patches.

REJECT THESE ARTIFACTS
- No piano-key smile, continuous white band, fused teeth, cloned crowns, oversized central incisors, rabbit teeth, long rectangular veneers, flat dental arch, excessive symmetry, black separator lines, black triangular side artifacts, missing side-tooth enamel, missing visible lower teeth, floating teeth, invented teeth or dental rows beyond those visible in the input, artificial gums, plastic opacity, or over-sharpened CGI texture.

Before rendering, internally inspect the original head pitch, camera elevation, dental plane, cervical attachment, upper-tooth exposure, lower-tooth exposure, tooth count, arch perspective, occlusions, light direction, color, and image sharpness. Before returning the image, verify that the new teeth share the head's 3D viewpoint, every upper crown is continuously attached with no unfilled band above it, and every lower tooth visible in the input is still visible at the same exposure. Prioritize anatomical plausibility and photographic integration over perfect whiteness or perfect symmetry.

Return only the final edited photograph, with no text, labels, explanation, border, or comparison layout.
"""


def get_api_key() -> Optional[str]:
    return (
        getattr(settings, "GEMINI_API_KEY", None)
        or os.environ.get("GEMINI_API_KEY")
        or getattr(settings, "GEMINI_API_KEY_NEW", None)
        or os.environ.get("GEMINI_API_KEY_NEW")
    )

def get_model_name() -> str:
    raw_name = (
        getattr(settings, "SMILE_GEMINI_MODEL_NAME", None)
        or os.environ.get("SMILE_GEMINI_MODEL_NAME")
        or getattr(settings, "GEMINI_MODEL_NAME", None)
        or os.environ.get("GEMINI_MODEL_NAME")
        or "gemini-2.5-flash-image"   # default
    )
    name = raw_name.strip()
    # Normalize aliases to official Google Gemini API model identifier
    if name in ["3.1-flash-image-lite", "gemini-3.1-flash-image-lite", "3.1-flash-lite-image", "gemini-3.1-flash-lite-image", "3.1-flash-lite", "gemini-3.1-flash-lite"]:
        return "gemini-3.1-flash-lite-image"
    if name in ["3.1-flash-image", "gemini-3.1-flash-image", "3.1-flash", "gemini-3.1-flash"]:
        return "gemini-3.1-flash-image"
    if name in ["2.5-flash-image", "gemini-2.5-flash-image"]:
        return "gemini-2.5-flash-image"
    return name

def get_thinking_level() -> str:
    raw_level = getattr(settings, "GEMINI_THINKING_LEVEL", None) or os.environ.get("GEMINI_THINKING_LEVEL") or "HIGH"
    level = raw_level.strip().upper()
    return level if level in ["HIGH", "MINIMAL", "LOW", "MEDIUM"] else "HIGH"

def add_logo_on_right(image_path: str, logo_path: str) -> None:
    base = Image.open(image_path).convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")

    base_w, base_h = base.size

    shadow_height = int(base_h * 0.18)  

    gradient = Image.new("RGBA", (base_w, shadow_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)

    for y in range(shadow_height):
        alpha = int(255 * (y / shadow_height))  
        draw.line(
            [(0, y), (base_w, y)],
            fill=(0, 0, 0, alpha)
        )

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
    Sends input image + prompt to Gemini (e.g. gemini-3.1-flash-image) via REST API,
    logs thought/reasoning steps, and writes the resulting rendered image to output_path.
    """
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not configured. Set env var GEMINI_API_KEY or Django setting GEMINI_API_KEY.")

    model_name = get_model_name()
    thinking_level = get_thinking_level()
    print(f"[SmileAI] Generating smile design using model: {model_name} (Thinking Level: {thinking_level})")

    with open(input_path, "rb") as f:
        img_bytes = f.read()

    b64_img = base64.b64encode(img_bytes).decode("utf-8")
    mime_type = "image/png" if input_path.lower().endswith(".png") else "image/jpeg"

    # REST Endpoint for Google Generative Language API
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

    parts = [
        {"text": PROMPT},
        {
            "inline_data": {
                "mime_type": mime_type,
                "data": b64_img
            }
        }
    ]

    # gemini-2.5-flash-image does NOT support thinkingConfig — sending it causes a 400.
    # Only add thinkingConfig for models that explicitly support it.
    generation_config: dict = {
        "temperature": 0.5,
        "topP": 0.95,
    }
    supports_thinking = "2.5" not in model_name  # 2.5-flash-image has no thinking API
    if supports_thinking and thinking_level:
        generation_config["thinkingConfig"] = {
            "thinkingLevel": thinking_level,
            "includeThoughts": True,
        }

    payload = {
        "contents": [
            {
                "parts": parts
            }
        ],
        "generationConfig": generation_config,
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"}
        ]
    }

    try:
        response = requests.post(url, json=payload, timeout=120)
    except Exception as e:
        raise RuntimeError(f"Network request to Gemini API failed: {str(e)}") from e

    if response.status_code != 200:
        raise RuntimeError(f"Gemini API returned error ({response.status_code}): {response.text}")

    data = response.json()
    image_bytes = None
    thought_texts = []
    output_texts = []

    candidates = data.get("candidates", [])
    for c in candidates:
        candidate_parts = c.get("content", {}).get("parts", [])
        for p in candidate_parts:
            is_thought = p.get("thought", False)
            if "text" in p and p["text"]:
                if is_thought:
                    thought_texts.append(p["text"].strip())
                else:
                    output_texts.append(p["text"].strip())

            inline = p.get("inlineData") or p.get("inline_data")
            if inline and inline.get("data"):
                image_bytes = base64.b64decode(inline["data"])

    if thought_texts:
        print("\n[SmileAI] --- Model Thinking / Reasoning Process ---")
        for idx, th in enumerate(thought_texts, 1):
            print(f"[Thought Step {idx}]:\n{th}\n")
        print("[SmileAI] --------------------------------------------\n")

    if output_texts:
        print(f"[SmileAI] Model output commentary: {' '.join(output_texts)}")

    if image_bytes is None:
        raise RuntimeError(f"Gemini did not return an image. Response text: {response.text[:500]}")

    with open(output_path, "wb") as f:
        f.write(image_bytes)

    # logo_path = os.path.join(settings.MEDIA_ROOT, "logo", "usd-logo.png")
    # if os.path.exists(logo_path):
    #     add_logo_on_right(output_path, logo_path)

    print(f"[SmileAI] AI smile design generated and saved successfully to {output_path}")