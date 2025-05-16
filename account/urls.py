from django.urls import path
from . import views
app_name='account'
urlpatterns = [
    path('', views.singup, name='singup'),
    path('dentist-request/', views.dentistreq, name='dentistreq'),
    path('patient-dashboard/', views.customer, name='customer'),
    path('patient-review/', views.patient_review, name='patient_review'),
    path('patient-profile/', views.patient_profile, name='patient_profile'),
    path('patient-change-password/', views.patient_password, name='patient_password'),
] 
