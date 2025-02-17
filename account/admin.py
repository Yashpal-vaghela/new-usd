from django.contrib import admin
from .models import Location, City, Specializations, Dentist, Image, Rating, Category, Tags, Author, Blog, Team, Testimonials, Gallery, Hgallery, Contact, UserSubmission

class DentistAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'contact', 'status')
    search_fields = ('name', 'city__city', 'contact')
    list_filter = ('status', 'city')

class BlogAdmin(admin.ModelAdmin):
    list_display = ('h1', 'author', 'published', 'status')
    search_fields = ('h1', 'author__name', 'keyword')
    list_filter = ('status', 'category', 'published')

class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name', 'position')
    search_fields = ('name', 'position')

class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'position')
    search_fields = ('name', 'position')

class TestimonialsAdmin(admin.ModelAdmin):
    list_display = ('name', 'position')
    search_fields = ('name', 'position')

class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'date', 'subject', 'message')
    search_fields = ('name', 'email', 'phone')
    list_filter = ('date',)

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
admin.site.register(UserSubmission)
