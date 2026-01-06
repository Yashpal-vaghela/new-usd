import os
from typing import Optional

from django.conf import settings

PROMPT = r"""TASK: Using [INPUT_IMAGE], perform a high-end cosmetic dentistry digital smile design. The design must strictly adhere to the visible natural tooth structure only.

⚠️ NON-NEGOTIABLE CONSTRAINTS
Facial Integrity: Do not alter any part of the face, including lips, gums, skin, beard, hair, eyes, or facial expression. No smile enhancement or expression modification is allowed.
Background & Lighting: Preserve the exact original background, lighting, and all ambient shadows outside the mouth area. Do not change, blur, or stylize any part of the surrounding image.
Framing & Perspective: Maintain the exact same camera angle, framing, and crop as the original image. No zooming, cropping, or re-centering.

😁 SMILE DESIGN (TEETH ONLY)
Transformation Scope: Replace the visible teeth only with high-end, symmetrical, and naturally aligned porcelain veneers. Do not extend tooth visibility beyond what is present in the original image.
Shade & Harmony: Use a high-value white shade (approx. B1) that appears clean yet realistic. Shade must be harmonized with the subject’s natural skin tone — avoid tones that appear unnaturally bright or mismatched, especially for darker complexions. Teeth must not appear overly bleached or artificial.
Anatomical Realism: Ensure detailed tooth anatomy including:
- Defined separation between teeth.
- Subtle enamel translucency near the incisal edges.
- Natural surface texture and shape.
Lip & Mouth Integration: Veneers must fit seamlessly under the existing lip line. Do not alter the lip position, shape, or visibility. Respect the natural mouth dynamics and avoid making the teeth look overly long, bulky, or disproportionate.
Lighting Consistency: New teeth must reflect and absorb light in harmony with the original image’s lighting conditions. Shadows, reflections, and highlights around the mouth must remain coherent.

✅ REMINDERS TO ENFORCE
No expression change. The person must look exactly the same emotionally and physically.
Final output should look professionally enhanced but indistinguishably real, as if the person naturally had perfect teeth.
"""

def get_api_key() -> Optional[str]:
    return getattr(settings, "GEMINI_API_KEY", None) or os.environ.get("GEMINI_API_KEY")

def get_model_name() -> str:
    return getattr(settings, "GEMINI_MODEL_NAME", None) or os.environ.get("GEMINI_MODEL_NAME") or "gemini-2.0-flash-exp"

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
