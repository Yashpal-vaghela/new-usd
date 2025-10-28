from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import *

class DentistAdmin(ImportExportModelAdmin):
    list_display = ('name', 'city', 'contact', 'status')
    search_fields = ('name', 'city__city', 'contact')
    list_filter = ('status', 'city')

class BlogAdmin(admin.ModelAdmin):
    list_display = ('h1', 'author', 'published', 'status')
    search_fields = ('h1', 'author__name', 'keyword')
    list_filter = ('status', 'category', 'published')
    exclude = ('blog_banner_lg_alt', 'blog_banner_sm_alt', 'image_alt')

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

class UserSubmissionAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'phone', 'email', 'city', 'doctor_name', 'created_at')
    search_fields = ('first_name', 'last_name', 'phone', 'email', 'doctor_name')
    list_filter = ('city', 'doctor_name', 'created_at')

class DentistRedirectAdmin(admin.ModelAdmin):
    list_display = ("old_slug", "city")

admin.site.register(Location)
admin.site.register(City)
admin.site.register(Specializations)
admin.site.register(Dentist, DentistAdmin)
admin.site.register(Image)
admin.site.register(Rating)
admin.site.register(Category)
admin.site.register(Tags)
admin.site.register(Author, AuthorAdmin)
admin.site.register(Blog, BlogAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Testimonials, TestimonialsAdmin)
admin.site.register(Gallery)
admin.site.register(Hgallery)
admin.site.register(Contact, ContactAdmin)
admin.site.register(DentistConnect, DentistConnectAdmin)
admin.site.register(DentistConnectNew, DentistConnectNewAdmin)
admin.site.register(UserSubmission)
admin.site.register(PatientReview, PatientReviewAdmin) 
admin.site.register(DentistRedirect, DentistRedirectAdmin)
