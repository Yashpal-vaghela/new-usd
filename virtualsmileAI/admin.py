from django.contrib import admin
from .models import SmileDesignLead

@admin.register(SmileDesignLead)
class SmileDesignLeadAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "city", "created_at")
    search_fields = ("name", "phone", "city")
    list_filter = ('created_at',)
