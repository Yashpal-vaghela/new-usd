from django.urls import path
from . import views
app_name='home'
urlpatterns = [
    path('', views.home, name='home'),
    path('find-dentist/', views.find_dentist, name='find_dentist'),
    path('gallery/', views.gallery, name='gallery'),
    path('dentist/<str:pk>/', views.find_dentist_d, name='find_dentist_d'),
    path('blogs/', views.blogs, name='blogs'),
    path('blogs/<str:pk>/', views.blogsd, name='blogsd'),
    path('contact/', views.contact, name='contact'),
    path('thank-you/', views.thankyou, name='thankyou'),
    path('sitemap.xml',views.sitemap, name='sitemap'),
    path('robots.txt',views.robots, name='robots'),
    path('all-usd/', views.all_usd, name='all_usd'),
    path('search-all-usd/', views.search_all_usd, name='search_all_usd'),
    path('receive_location/', views.receive_location, name='receive_location'),
    path('locations/', views.location_view, name='locations'),
    # path('smile_step/', views.smile_step, name='smile_step'),

] 
