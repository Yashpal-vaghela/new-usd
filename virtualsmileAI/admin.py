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

    def _get_image_url(self, path):
        if not path or path == "N/A":
            return None
        p = str(path).strip()
        if not p:
            return None

        # 1. Base64 data URL
        if p.startswith("data:image"):
            return p

        # 2. Extract root-relative /media/... (works cleanly on both http local & https prod)
        if "/media/" in p:
            return p[p.index("/media/"):]

        # 3. External HTTP URL -> upgrade to HTTPS if not local
        if p.startswith("http://"):
            if not ("127.0.0.1" in p or "localhost" in p):
                return "https://" + p[7:]
            return p

        if p.startswith("https://") or p.startswith("/"):
            return p

        # 4. Relative path -> prepend MEDIA_URL
        media_url = getattr(settings, "MEDIA_URL", "/media/")
        return f"{media_url}{p.lstrip('/')}"

    def _render_preview(self, path, label):
        url = self._get_image_url(path)
        if not url:
            return mark_safe('<span style="color: #666; font-size: 12px;">(No Image)</span>')

        return format_html(
            '<div style="position: relative; width: 120px; height: 120px;">'
            '<a href="{0}" target="_blank" rel="noopener noreferrer">'
            '<img src="{0}" width="120" height="120" referrerpolicy="no-referrer" loading="lazy" '
            'style="object-fit: contain; border-radius: 6px; display: block; background: #141414; border: 1px solid #333;" '
            'onerror="this.style.display=\'none\'; this.parentElement.nextElementSibling.style.display=\'flex\';" />'
            '</a>'
            '<div style="display: none; width: 120px; height: 120px; border: 1px dashed #555; border-radius: 6px; '
            'flex-direction: column; align-items: center; justify-content: center; background: #181818; color: #888; font-size: 10px; text-align: center; padding: 2px; box-sizing: border-box;">'
            '<span>⚠️ Error</span>'
            '</div>'
            '</div>',
            url
        )

    def before_preview(self, obj):
        return self._render_preview(obj.before_image, "Before")

    before_preview.short_description = "Before"

    def after_preview(self, obj):
        return self._render_preview(obj.after_image, "After")

    after_preview.short_description = "After"

    def get_form(self, request, obj=None, change=False, **kwargs):
        if obj:
            def to_full_url(path):
                if not path or path == "N/A" or path.startswith("data:image"):
                    return path
                p = str(path).strip()
                is_local_path = "127.0.0.1" in p or "localhost" in p
                is_current_local = "127.0.0.1" in request.get_host() or "localhost" in request.get_host()
                if (is_local_path and not is_current_local) or not (p.startswith("http://") or p.startswith("https://")):
                    if "/media/" in p:
                        clean = p[p.index("/media/"):]
                    else:
                        media_url = getattr(settings, "MEDIA_URL", "/media/")
                        clean = f"{media_url}{p.lstrip('/')}"
                    return request.build_absolute_uri(clean)
                return p

            if obj.before_image:
                obj.before_image = to_full_url(obj.before_image)
            if obj.after_image:
                obj.after_image = to_full_url(obj.after_image)
        return super().get_form(request, obj=obj, change=change, **kwargs)




