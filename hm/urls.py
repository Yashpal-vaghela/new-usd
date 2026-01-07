from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from . import pre
# from exam import views as auth_view
admin.site.site_header = 'Dashboard'                    # default: "Django Administration"
admin.site.index_title = 'Admin Panel'                 # default: "Site administration"
admin.site.site_title = 'Technologies Admin Panel' # default: "Django site admin"
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),
    path('account/', include('account.urls')),
    path('virtual-smile-try-on/', include('virtualsmileAI.urls')),
    path('get-location-info/', pre.get_location_info, name='get_location_info'),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    # password reset
    path('reset_password', auth_views.PasswordResetView.as_view(template_name='reset.html'), name='reset_password'),
    path('reset_password_sent', auth_views.PasswordResetDoneView.as_view(template_name='sent.html'), name="password_reset_done"),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='updatePW.html'), name="password_reset_confirm" ),
    path('reset_password_complete/', auth_views.PasswordResetCompleteView.as_view(template_name="complete.html"), name= "password_reset_complete"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns  += static(settings.STATIC_URL,document_root=settings.STATIC_ROOT)

