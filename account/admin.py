from django.contrib import admin
from django.db import models
from import_export.admin import ImportExportModelAdmin
from django.utils.html import format_html, mark_safe
from django_json_widget.widgets import JSONEditorWidget
from .models import *

class DentistAdmin(ImportExportModelAdmin):
    list_display = ('profile_preview', 'dentist_image_preview', 'name', 'city', 'contact', 'status')
    list_display_links = ('name',)
    search_fields = ('name', 'city__city', 'contact')
    list_filter = ('status', 'city')
    readonly_fields = ('profile_preview', 'dentist_image_preview')

    def profile_preview(self, obj):
        if obj.profile:
            try:
                return format_html(
                    '<a href="{}" target="_blank" rel="noopener noreferrer">'
                    '<img src="{}" width="100" height="100" style="object-fit: contain; border-radius: 6px; display: block; cursor: pointer;" />'
                    '</a>',
                    obj.profile.url,
                    obj.profile.url
                )
            except Exception:
                pass
        return mark_safe('<span style="color: #888;">(No Image)</span>')

    profile_preview.short_description = "Profile"

    def dentist_image_preview(self, obj):
        if obj.dentist_image:
            try:
                return format_html(
                    '<a href="{}" target="_blank" rel="noopener noreferrer">'
                    '<img src="{}" width="100" height="100" style="object-fit: contain; border-radius: 6px; display: block; cursor: pointer;" />'
                    '</a>',
                    obj.dentist_image.url,
                    obj.dentist_image.url
                )
            except Exception:
                pass
        return mark_safe('<span style="color: #888;">(No Image)</span>')

    dentist_image_preview.short_description = "Dentist Image"


class DentistDetailsAdmin(ImportExportModelAdmin):
    list_display = ('list_page_image_preview', 'details_page_image_preview', 'name', 'city', 'contact', 'status')
    list_display_links = ('name',)
    search_fields = ('name', 'city__city', 'contact')
    list_filter = ('status', 'city')
    readonly_fields = ('list_page_image_preview', 'details_page_image_preview')

    def list_page_image_preview(self, obj):
        if obj.list_page_image:
            try:
                return format_html(
                    '<a href="{}" target="_blank" rel="noopener noreferrer">'
                    '<img src="{}" width="100" height="100" style="object-fit: contain; border-radius: 6px; display: block; cursor: pointer;" />'
                    '</a>',
                    obj.list_page_image.url,
                    obj.list_page_image.url
                )
            except Exception:
                pass
        return mark_safe('<span style="color: #888;">(No Image)</span>')

    list_page_image_preview.short_description = "List Page Image"

    def details_page_image_preview(self, obj):
        if obj.details_page_image:
            try:
                return format_html(
                    '<a href="{}" target="_blank" rel="noopener noreferrer">'
                    '<img src="{}" width="100" height="100" style="object-fit: contain; border-radius: 6px; display: block; cursor: pointer;" />'
                    '</a>',
                    obj.details_page_image.url,
                    obj.details_page_image.url
                )
            except Exception:
                pass
        return mark_safe('<span style="color: #888;">(No Image)</span>')

    details_page_image_preview.short_description = "Details Page Image"


class BlogAdmin(admin.ModelAdmin):
    list_display = ('h1', 'author', 'published', 'status')
    search_fields = ('h1', 'author__name', 'keyword')
    list_filter = ('status', 'category', 'published')
    exclude = ('blog_banner_lg_alt', 'blog_banner_sm_alt', 'image_alt')

    formfield_overrides = {
        models.JSONField: {"widget": JSONEditorWidget},
    }

class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name', 'position')
    search_fields = ('name', 'position')

class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'position')
    search_fields = ('name', 'position')

class TestimonialsAdmin(admin.ModelAdmin):
    list_display = ('name', 'position')
    search_fields = ('name', 'position')

class ContactAdmin(ImportExportModelAdmin):
    list_display = ('name', 'email', 'phone','city', 'date', 'subject', 'message')
    search_fields = ('name', 'email', 'phone')
    list_filter = ('date',)

class DentistConnectAdmin(ImportExportModelAdmin):
    list_display = ('name', 'phone', 'clinic_name', 'city', 'date')
    search_fields = ('name', 'city', 'clinic_name')
    list_filter = ('date',)
class DentistConnectNewAdmin(ImportExportModelAdmin):
    list_display = ('name', 'phone', 'clinic_name', 'city', 'date')
    search_fields = ('name', 'city', 'clinic_name')
    list_filter = ('date',)

class PatientReviewAdmin(admin.ModelAdmin):
    list_display = ('patient_name', 'dentist', 'rating', 'created_at')
    search_fields = ('patient_name', 'dentist__name')
    list_filter = ('rating', 'created_at')

class UserSubmissionAdmin(ImportExportModelAdmin):
    list_display = ('first_name', 'last_name', 'phone', 'email', 'city', 'doctor_name', 'created_at')
    search_fields = ('first_name', 'last_name', 'phone', 'email', 'doctor_name')
    list_filter = ('city', 'doctor_name', 'created_at')

class DentistRedirectAdmin(admin.ModelAdmin):
    list_display = ("old_slug", "city")

class BeforeAfterAdmin(admin.ModelAdmin):
    list_display = ("id", "image_preview", "alt_text", "created_at")
    readonly_fields = ("image_preview",)
    search_fields = ("alt_text",)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="120" style="border-radius:5px;" />'.format(obj.image.url)
            )
        return "(No Image)"
    
    image_preview.short_description = "Preview"
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email','is_active','subscribed_at')
    search_fields = ('email',)
    list_filter = ('is_active','subscribed_at')

class SmileDesignLeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'city', 'submitted_at')
    search_fields = ('name', 'phone', 'city')
    list_filter = ('submitted_at',)

class AwardsAdmin(admin.ModelAdmin):
    list_display = ('name', 'year')
    search_fields = ('name', 'year')

class HgalleryAdmin(admin.ModelAdmin):
    list_display = ("id", "image_preview")
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="120" style="border-radius:5px;" />',
                obj.image.url
            )
        return "(No Image)"

    image_preview.short_description = "Preview"

class ContactHomePageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone','city', 'date', 'message')
    search_fields = ('name', 'email', 'phone')
    list_filter = ('date',)

class RedirectRuleAdmin(admin.ModelAdmin):
    list_display = ('old_url', 'new_url', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('old_url', 'new_url')
    list_editable = ('is_active',)


admin.site.register(Location)
admin.site.register(City)
admin.site.register(Specializations)
admin.site.register(Dentist, DentistAdmin)
admin.site.register(DentistDetails, DentistDetailsAdmin)
admin.site.register(Image)
admin.site.register(Rating)
admin.site.register(Category)
admin.site.register(Tags)
admin.site.register(Author, AuthorAdmin)
admin.site.register(Blog, BlogAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Testimonials, TestimonialsAdmin)
admin.site.register(Gallery)
admin.site.register(Hgallery, HgalleryAdmin)
admin.site.register(Contact, ContactAdmin)
admin.site.register(DentistConnect, DentistConnectAdmin)
admin.site.register(DentistConnectNew, DentistConnectNewAdmin)
admin.site.register(UserSubmission, UserSubmissionAdmin)
admin.site.register(PatientReview, PatientReviewAdmin) 
admin.site.register(DentistRedirect, DentistRedirectAdmin)
admin.site.register(BeforeAfter, BeforeAfterAdmin)
admin.site.register(NewsletterSubscriber, NewsletterSubscriberAdmin)
admin.site.register(SmileDesignLead, SmileDesignLeadAdmin)
admin.site.register(Awards, AwardsAdmin)
admin.site.register(ContactHomePage, ContactHomePageAdmin)
admin.site.register(RedirectRule, RedirectRuleAdmin)