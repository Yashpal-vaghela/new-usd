from django.contrib import admin

from .models import EmailOutbox


@admin.register(EmailOutbox)
class EmailOutboxAdmin(admin.ModelAdmin):
    list_display = ("subject", "status", "attempts", "created_at", "sent_at")
    list_filter = ("status",)
    search_fields = ("subject", "last_error")
    readonly_fields = ("created_at", "updated_at", "sent_at")
    actions = ["retry_now"]

    @admin.action(description="Retry selected emails now")
    def retry_now(self, request, queryset):
        queryset.exclude(status=EmailOutbox.STATUS_SENT).update(
            status=EmailOutbox.STATUS_PENDING, next_try_at=None, attempts=0
        )
