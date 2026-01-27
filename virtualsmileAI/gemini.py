import os
from typing import Optional
from PIL import Image, ImageDraw
from django.conf import settings

PROMPT = r"""
TASK: Using [INPUT_IMAGE], perform a high-end cosmetic dentistry digital smile design. Only modify the visible teeth – all other features must remain unchanged.

⚠️ Non-Negotiable Constraints

Facial Integrity: Do not alter any part of the face (this includes lips, gums, skin, beard, hair, eyes, or facial expression). The subject’s smile and expression should remain natural – no forced smiles or lip adjustments.
Background & Lighting: Preserve the original background, lighting, and shadows exactly as they are. Do not change, blur, or stylize any area outside the mouth. Everything around the face and in the environment must remain identical to the input.
Framing & Perspective: Maintain the same camera angle, framing, and crop as the original image. No zooming, cropping, or re-centering is allowed. The output should align perfectly with the input image in perspective and composition.
Strict Tooth Boundary Lock: The veneers must remain fully or pariallty as per smile inside the original tooth silhouettes as seen in the input photo. Do not expand beyond the original tooth edges (top, bottom, left, right). No scaling up, no widening, no lengthening.
No Smile Expansion: Do not increase the amount of visible teeth or show additional teeth. Keep the same number of visible teeth and the same exposure.

😁 Smile Design (Teeth Only)
Transformation Scope: Replace only the visible teeth with high-end, beautifully crafted e.max veneers. The new teeth should be symmetrical and naturally aligned, following the exact layout of the original teeth (do not reveal more teeth than are originally visible, and do not alter the gum line). Each veneer should sit precisely where the original tooth is.
Shade & Harmony: Select the veneer shade dynamically based on the subject’s natural skin tone to ensure realism and harmony:
Darker skin tones: Use shade A3 (a warm, natural white with depth that complements deeper complexions).
Medium or wheatish skin tones: Use shade A2 (a balanced, soft natural white).
Fair or light skin tones: Use shade A1 (a bright yet realistic white).
Avoid any overly bleached, chalky look – the veneers should be clean and bright but still believable for the individual’s complexion. They must appear healthy and premium in color, without looking fake.
Color Consistency: Ensure the new teeth have even, consistent coloration with no spots, streaks, or discoloration. The enamel shade should transition naturally from the slightly warmer tone near the gum to a subtle translucency at the tips, mimicking real teeth. There should be no staining or blotches – the veneers must look impeccably clean and evenly shaded (while still showing gentle gradation like natural teeth). This aligns with the ideal that a tooth shade should harmonize with one’s appearance and stay free of discoloration over time.
Anatomical Realism: The veneers must have realistic dental anatomy and texture:
Tooth Separation: Each tooth should be clearly individually defined with a natural outline. Do not let veneers merge or blur together – there should be subtle, clean lines or slight gaps where teeth meet, just like real teeth.
Translucency & Texture: Incorporate subtle enamel translucency towards the incisal edges (the biting tips of the teeth) – a slight see-through quality at the edges that real enamel often has. Also include natural surface textures and micro-details (fine textures or luster) so they catch light realistically, rather than looking flat.
Micro-Asymmetry: Introduce very slight, natural variations in tooth shape or positioning (for example, a tiny variation in the contour or angle of a tooth) to avoid a “cookie-cutter” appearance. Real smiles have minor asymmetries that give them character. The veneers should not look unnaturally identical or overly uniform – they should be perfectly aligned and proportional yet with a touch of individuality for realism.
Lip & Mouth Integration: The new teeth must fit seamlessly into the existing mouth without altering any surrounding tissues:
The veneers should sit under the existing lip line exactly. Do not change the position or shape of the lips or the amount of gums showing. The lips in the image should look untouched and naturally draped over the teeth as they originally were.
Maintain Original Tooth Size: Keep each tooth’s height and width the same as in the original image. Do not make the teeth longer, wider, or bulkier than they originally appear. This ensures the veneers do not look too large or out-of-place. The overall smile line (the curve of the teeth as it follows the lip) should remain unchanged.
Ensure the gumline and teeth junction is clean and natural. Do not alter the gums’ color or shape. There should be no dark edges or obvious lines at the gum-teeth interface – the veneers should appear to emerge naturally from the gums.
Tooth Size & Proportion: Veneers must strictly match the original visible tooth dimensions. Do not increase height or width beyond what is naturally present in the input image.
Teeth should never appears with too wider and longer than input image. The design must preserve the subject’s natural smile curve.
Slight improvements for symmetry are allowed. Always prioritize natural realism over geometric correction.
Veneers must fit entirely within the original tooth contour – no extension past gumline, lips, or spacing.
The smile should look harmonious and balanced, not artificial or “overdone.”
Lighting Consistency: The replaced teeth must match the lighting of the original photo perfectly:
Retain the same highlights and shadows on the teeth that would be present given the scene’s lighting. For example, if the light in the original image comes from above or one side, the veneers should show corresponding gentle highlights on that side and soft shadows where appropriate, just like real teeth under those conditions.
The reflection and shine on the veneers should mirror what real teeth would reflect in that environment (no excessive gloss beyond what the original lighting suggests).
Do not introduce any new light sources or unnatural glare. The goal is that the new teeth appear as if they were always part of the original image, with coherent lighting and shadowing around the mouth. All ambient shadows and lighting on the face remain unchanged, and the teeth should blend into that light seamlessly.
Flawless Final Result: The final smile should look impeccably realistic and aesthetically stunning:
The veneers must be high-end and flawless – as if a top cosmetic dentist did the work. They should show no imperfections like chips, cracks, or rough edges. Each tooth’s edges should be smooth and well-defined (unless the original had a certain unique edge shape that should be preserved).
Use e.max veneers for their renowned quality – they are ultra-thin and have life-like translucency, enabling a very natural look. This means the new teeth should exhibit the slight glassy depth that real enamel has, enhancing realism.
There should be no artifacts or errors from the editing process: no double exposure of teeth, no blurred areas, no mismatched colors. Everything about the teeth should look deliberate and naturally photographical.
Overall, the outcome must radiate a premium yet natural smile. It should look like the person simply has perfect, healthy teeth. Anyone viewing the image should not detect it was digitally altered – it should look like a real, high-quality photograph of a person with a beautiful, naturally harmonious smile.
"""

def get_api_key() -> Optional[str]:
    return getattr(settings, "GEMINI_API_KEY", None) or os.environ.get("GEMINI_API_KEY")

def get_model_name() -> str:
    return getattr(settings, "GEMINI_MODEL_NAME", None) or os.environ.get("GEMINI_MODEL_NAME") 

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
    Sends input image + prompt to Gemini and saves an output image to output_path.

    NOTE:
      Different Gemini models/APIs return images in different formats.
      This implementation tries the common `google-generativeai` Python SDK flow.
      If your account/model differs, adjust here only (front-end/back-end stays same).
    """
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not configured. Set env var GEMINI_API_KEY or Django setting GEMINI_API_KEY.")

    try:
        import google.generativeai as genai
    except Exception as e:
        raise RuntimeError("google-generativeai not installed. Run: pip install google-generativeai") from e

    # Load bytes
    with open(input_path, "rb") as f:
        img_bytes = f.read()

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(get_model_name())

    # Many Gemini endpoints accept inline_data for images
    parts = [
        {"text": PROMPT},
        {"inline_data": {"mime_type": "image/jpeg", "data": img_bytes}},
    ]

    # Try to request an image output
    resp = model.generate_content(
        parts,
        generation_config={
            "temperature": 0.2,
        },
    )

    # Attempt to extract image bytes from the response
    # The SDK has changed across versions; handle common cases.
    image_bytes = None

    # Case 1: resp.parts contains inline_data
    try:
        for p in getattr(resp, "parts", []) or []:
            inline = getattr(p, "inline_data", None)
            if inline and getattr(inline, "data", None):
                image_bytes = inline.data
                break
    except Exception:
        pass

    # Case 2: resp.candidates -> content -> parts
    if image_bytes is None:
        try:
            for c in getattr(resp, "candidates", []) or []:
                content = getattr(c, "content", None)
                for p in getattr(content, "parts", []) or []:
                    inline = getattr(p, "inline_data", None)
                    if inline and getattr(inline, "data", None):
                        image_bytes = inline.data
                        break
                if image_bytes is not None:
                    break
        except Exception:
            pass

    if image_bytes is None:
        # If your model returns text only, log the text for debugging.
        text = getattr(resp, "text", None)
        raise RuntimeError(f"Gemini did not return an image. Response text: {text[:500] if text else '<<no text>>'}")

    with open(output_path, "wb") as f:
        f.write(image_bytes)
        # logo_path = os.path.join(settings.MEDIA_ROOT, "logo", "usd-logo.png")
        # add_logo_on_right(output_path, logo_path)