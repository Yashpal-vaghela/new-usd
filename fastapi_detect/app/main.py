from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .yolo import (
    load_model,
    decode_base64_image,
    run_inference_on_bgr,
)


# -----------------------------------------------------------------------------
# FastAPI App
# -----------------------------------------------------------------------------
app = FastAPI(
    title="USD Smile Detection Service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# -----------------------------------------------------------------------------
# CORS (allow your Django domain)
# -----------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          
    allow_credentials=False,      
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Request Schema
# -----------------------------------------------------------------------------
class DetectPayload(BaseModel):
    image: str   # base64 dataURL or raw base64


# -----------------------------------------------------------------------------
# Startup: Warm up YOLO model (prevents first-request lag)
# -----------------------------------------------------------------------------
@app.on_event("startup")
def startup_event():
    try:
        load_model()
        print("✅ YOLO model loaded successfully")
    except Exception as e:
        print("❌ YOLO model load failed:", e)


# -----------------------------------------------------------------------------
# Detect Endpoint
# -----------------------------------------------------------------------------
@app.post("/detect")
async def detect_smile(payload: DetectPayload):
    """
    Receives a base64 image and returns:
    {
        conf: float,
        visible: bool
    }
    """

    if not payload.image:
        raise HTTPException(status_code=400, detail="Image is required")

    try:
        # Decode image
        img_bgr = decode_base64_image(payload.image)

        # Run YOLO inference
        result = run_inference_on_bgr(img_bgr)

        return {
            "conf": float(result.get("max_conf", 0.0)),
            "visible": bool(result.get("visible", False)),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
