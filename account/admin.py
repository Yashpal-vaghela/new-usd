from django.contrib import admin, messages
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied
from django.db import models
from django.http import Http404, HttpResponseNotAllowed
from django.shortcuts import redirect
from django.urls import path
from import_export.admin import ImportExportModelAdmin
from django.utils.html import format_html, mark_safe
from django_json_widget.widgets import JSONEditorWidget
from .clinic_hours import active_dentists, sync_dentist_hours
from .google_places import PlacesConfigError
from .models import *

class DentistAdmin(ImportExportModelAdmin):
    list_display = ('profile_preview', 'dentist_image_preview', 'name', 'city', 'contact', 'status')
    list_display_links = ('name',)
    search_fields = ('name', 'city__city', 'contact')
    list_filter = ('status', 'city')
    readonly_fields = ('profile_preview', 'dentist_image_preview', 'hours_synced_at')

    # "Fetch Google hours" buttons (templates in account/templates/admin/account/dentist/)
    import_export_change_list_template = 'admin/account/dentist/change_list_google_hours.html'
    change_form_template = 'admin/account/dentist/change_form_google_hours.html'
    actions = ['fetch_google_hours']

    def get_urls(self):
        urls = [
            path('google-hours/sync-all/',
                 self.admin_site.admin_view(self.sync_all_google_hours_view),
                 name='account_dentist_sync_all_google_hours'),
            path('<path:object_id>/google-hours/sync/',
                 self.admin_site.admin_view(self.sync_one_google_hours_view),
                 name='account_dentist_sync_one_google_hours'),
        ]
        return urls + super().get_urls()

    @admin.action(description='Fetch opening hours from Google (selected active dentists)')
    def fetch_google_hours(self, request, queryset):
        self._sync_google_hours(request, queryset.select_related('city').order_by('id'))

    def sync_all_google_hours_view(self, request):
        if request.method != 'POST':
            return HttpResponseNotAllowed(['POST'])
        if not self.has_change_permission(request):
            raise PermissionDenied
        self._sync_google_hours(request, active_dentists())
        return redirect('admin:account_dentist_changelist')

    def sync_one_google_hours_view(self, request, object_id):
        if request.method != 'POST':
            return HttpResponseNotAllowed(['POST'])
        dentist = self.get_object(request, unquote(object_id))
        if dentist is None:
            raise Http404('Dentist not found')
        if not self.has_change_permission(request, dentist):
            raise PermissionDenied
        self._sync_google_hours(request, [dentist])
        return redirect('admin:account_dentist_change', dentist.pk)

    def _sync_google_hours(self, request, dentists):
        """Run the Google hours sync for `dentists` and report the outcome as admin messages."""
        results = []
        try:
            for dentist in dentists:
                results.append(sync_dentist_hours(dentist))
        except PlacesConfigError as exc:
            self.message_user(request, f'Google Places API not usable, nothing more was fetched: {exc}', messages.ERROR)

        by_status = {}
        for r in results:
            by_status.setdefault(r.status, []).append(r)
            if r.linked_place:
                self.message_user(
                    request,
                    f'{r.label}: linked to Google place "{r.linked_place_text}". '
                    f'If this is the wrong clinic, correct the "Google place id" field.',
                    messages.INFO,
                )
            if r.business_status and r.business_status != 'OPERATIONAL':
                self.message_user(request, f'{r.label}: Google Maps says {r.business_status}.', messages.WARNING)
            if r.status == 'error':
                self.message_user(request, f'{r.label}: Google error: {r.error}', messages.ERROR)

        def names(status, with_days=False):
            items = by_status.get(status, [])
            if with_days and len(items) <= 5:  # show the changed days only for a few dentists
                return ', '.join(f'{r.label} ({", ".join(r.changes)})' for r in items)
            return ', '.join(r.label for r in items)

        if 'changed' in by_status:
            self.message_user(request, f'Opening hours updated for {len(by_status["changed"])} dentist(s): '
                                       f'{names("changed", with_days=True)}', messages.SUCCESS)
        if 'unchanged' in by_status:
            self.message_user(request, f'Opening hours already up to date for {len(by_status["unchanged"])} dentist(s).', messages.SUCCESS)
        if 'no_hours' in by_status:
            self.message_user(request, f'No opening hours on Google Maps (kept existing hours): {names("no_hours")}', messages.WARNING)
        if 'not_found' in by_status:
            self.message_user(request, f'Clinic not found on Google Maps, add the "Google place id" manually: {names("not_found")}', messages.WARNING)
        if 'inactive' in by_status:
            self.message_user(request, f'Skipped (status is off, only active dentists are fetched): {names("inactive")}', messages.WARNING)
        if not results and not dentists:
            self.message_user(request, 'No active dentists to fetch.', messages.WARNING)

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