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
        if not path or path == "N/A":
            return None
        p = str(path).strip()
        if not p:
            return None
        if p.startswith("http://") or p.startswith("https://") or p.startswith("/"):
            return p
        return f"{settings.MEDIA_URL}{p}"

    def before_preview(self, obj):
        url = self._get_image_url(obj.before_image)
        if url:
            try:
                return format_html(
                    '<a href="{0}" target="_blank" rel="noopener noreferrer">'
                    '<img src="{0}" width="120" height="120" style="object-fit: contain; border-radius: 6px; display: block; cursor: pointer;" />'
                    '</a>',
                    url
                )
            except Exception:
                pass
        return mark_safe('<span style="color: #888;">(No Image)</span>')

    before_preview.short_description = "Before Image"

    def after_preview(self, obj):
        url = self._get_image_url(obj.after_image)
        if url:
            try:
                return format_html(
                    '<a href="{0}" target="_blank" rel="noopener noreferrer">'
                    '<img src="{0}" width="120" height="120" style="object-fit: contain; border-radius: 6px; display: block; cursor: pointer;" />'
                    '</a>',
                    url
                )
            except Exception:
                pass
        return mark_safe('<span style="color: #888;">(No Image)</span>')

    after_preview.short_description = "After Image"
