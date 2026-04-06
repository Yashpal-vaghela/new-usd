from django.contrib import admin
from .models import SmileDesignLead
from import_export.admin import ImportExportModelAdmin

@admin.register(SmileDesignLead)
class SmileDesignLeadAdmin(ImportExportModelAdmin):
    list_display = ("name", "phone", "city", "created_at")
    search_fields = ("name", "phone", "city")
    list_filter = ('created_at',)
