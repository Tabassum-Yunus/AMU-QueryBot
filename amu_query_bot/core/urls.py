from django.urls import path
from . import views

urlpatterns = [
    path('', views.lobby, name='chat-lobby'),
    path('message/', views.chat_message, name='chat-message'),
]