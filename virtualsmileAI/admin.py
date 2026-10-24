import os
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.conf import settings
from .models import SmileDesignLead
from import_export.admin import ImportExportModelAdmin


@admin.register(SmileDesignLead)
class SmileDesignLeadAdmin(ImportExportModelAdmin):
    list_display = ("before_preview", "after_preview", "name", "phone", "city", "created_at")
    list_display_links = ("name",)
    search_fields = ("name", "phone", "city")
    list_filter = ('created_at',)
    ordering = ('-created_at',)
    readonly_fields = ('before_preview', 'after_preview')

    def _get_image_url(self, path):
        """
        Resolves image path to a clean browser-loadable URL.
        - Supports base64 data URLs directly.
        - Converts absolute /media/ paths to root-relative /media/... to prevent mixed-content blocks.
        - Upgrades external http:// URLs to https://.
        """
        if not path or path == "N/A":
            return None

        p = str(path).strip()
        if not p:
            return None

        # 1. Base64 data URL
        if p.startswith("data:image"):
            return p

        # 2. Contains /media/ (extract root-relative /media/... to prevent mixed content & domain issues)
        if "/media/" in p:
            return p[p.index("/media/"):]

        # 3. External HTTP URL -> upgrade to HTTPS to prevent browser mixed content blocking
        if p.startswith("http://"):
            return "https://" + p[7:]

        if p.startswith("https://") or p.startswith("/"):
            return p

        # 4. Relative path -> prepend MEDIA_URL
        media_url = getattr(settings, "MEDIA_URL", "/media/")
        return f"{media_url}{p.lstrip('/')}"

    def _render_preview(self, path, label):
        url = self._get_image_url(path)
        if not url:
            return mark_safe('<span style="color: #666; font-size: 12px;">(No Image)</span>')

        # Use referrerpolicy="no-referrer" so server hotlink protection doesn't block the admin preview,
        # and loading="lazy" for smooth changelist rendering.
        return format_html(
            '<div style="position: relative; width: 120px; height: 120px;">'
            '<a href="{0}" target="_blank" rel="noopener noreferrer">'
            '<img src="{0}" width="120" height="120" referrerpolicy="no-referrer" loading="lazy" '
            'style="object-fit: contain; border-radius: 6px; display: block; background: #141414; border: 1px solid #333;" '
            'onerror="this.style.display=\'none\'; this.parentElement.nextElementSibling.style.display=\'flex\';" />'
            '</a>'
            '<div style="display: none; width: 120px; height: 120px; border: 1px dashed #555; border-radius: 6px; '
            'flex-direction: column; align-items: center; justify-content: center; background: #181818; color: #888; font-size: 11px; text-align: center; padding: 4px; box-sizing: border-box;">'
            '<span>⚠️ Load Error</span>'
            '</div>'
            '</div>',
            url
        )

    def before_preview(self, obj):
        return self._render_preview(obj.before_image, "Before")

    before_preview.short_description = "Before Image"

    def after_preview(self, obj):
        return self._render_preview(obj.after_image, "After")

    after_preview.short_description = "After Image"


