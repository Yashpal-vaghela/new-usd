from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_bot, name='chat_bot'),
    path('api/tts', views.api_tts, name='api_tts'),
    path('api/tts/', views.api_tts, name='api_tts_slash'),
    path('api/submit-feedback', views.submit_feedback, name='submit_feedback'),
    path('api/submit-feedback/', views.submit_feedback, name='submit_feedback_slash'),
]