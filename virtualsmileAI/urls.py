from django.urls import path
from django.contrib import sitemaps
from django.contrib.sitemaps.views import sitemap
from home.sitemaps import *
from . import views

app_name='virtualsmileAI'

urlpatterns = [
    path('', views.index, name='virtualsmiletryon'),
    path('api/detect/', views.detect_api, name='teeth_detect_api'),
    path('api/capture/', views.capture_api, name='teeth_capture_api'),
    path('api/smile-design/', views.smile_design_api, name='teeth_smile_design_api'),
]