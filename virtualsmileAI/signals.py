import os
from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import SmileDesignLead


def _normalize_path(image_path):
    if not image_path:
        return ""
    p = str(image_path).strip()
    if "/media/" in p:
        p = p[p.index("/media/") + len("/media/"):]
    else:
        media_url = getattr(settings, "MEDIA_URL", "/media/")
        if p.startswith(media_url):
            p = p[len(media_url):]
        elif p.startswith("/media/"):
            p = p[len("/media/"):]
    return p.lstrip("/")


def _delete_media_file(image_path):
    """Safely delete an image file from MEDIA_ROOT."""
    clean_rel = _normalize_path(image_path)
    if not clean_rel:
        return

    # Skip base64 strings, external URLs, or unusually long text
    if clean_rel.startswith(("data:image", "http://", "https://")) or len(clean_rel) > 300:
        return

    # Build absolute path inside MEDIA_ROOT
    full_path = os.path.abspath(os.path.join(settings.MEDIA_ROOT, clean_rel))
    media_root = os.path.abspath(settings.MEDIA_ROOT)

    # Ensure path is safely within MEDIA_ROOT
    if not full_path.startswith(media_root):
        return

    # Delete if file exists
    if os.path.isfile(full_path):
        try:
            os.remove(full_path)
        except OSError:
            pass


@receiver(post_delete, sender=SmileDesignLead)
def delete_smile_design_lead_images(sender, instance, **kwargs):
    """
    Triggered when a lead is deleted (individually or via bulk delete in admin).
    Removes before_image and after_image from disk ONLY if no remaining lead references them.
    """
    for img_attr in (instance.before_image, instance.after_image):
        if not img_attr:
            continue

        clean_rel = _normalize_path(img_attr)
        if not clean_rel or clean_rel.startswith(("data:image", "http://", "https://")):
            continue

        # Check if ANY remaining record references this path (with or without /media/ prefix)
        still_in_use = SmileDesignLead.objects.filter(
            models.Q(before_image__icontains=clean_rel) | models.Q(after_image__icontains=clean_rel)
        ).exists()

        if not still_in_use:
            _delete_media_file(clean_rel)
