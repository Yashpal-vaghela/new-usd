from django.apps import AppConfig
import threading


class VirtualsmileaiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'virtualsmileAI'

    def ready(self):
        # Pre-warm AI segmentation models in a background daemon thread
        # Eliminates the 7-8 second cold-start disk loading delay for users
        def _prewarm_models():
            try:
                from virtualsmileAI.seamless_blend import (
                    get_bisenet_model,
                    get_face_landmarker,
                    get_teeth_model,
                )
                print("[SmileAI Prewarm] Pre-warming BiSeNet, MediaPipe & YOLO models in RAM...")
                get_bisenet_model()
                get_face_landmarker()
                get_teeth_model()
                print("[SmileAI Prewarm] All AI models pre-warmed and ready in RAM.")
            except Exception as e:
                print(f"[SmileAI Prewarm Note]: {e}")

        # Start prewarming in background thread so Django starts immediately without delay
        threading.Thread(target=_prewarm_models, daemon=True).start()

