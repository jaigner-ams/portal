from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('messages/', views.message_list, name='message_list'),
    path('messages/create/', views.message_create, name='message_create'),
    path('messages/<int:pk>/edit/', views.message_edit, name='message_edit'),
    path('messages/<int:pk>/toggle/', views.message_toggle, name='message_toggle'),
    path('messages/<int:pk>/delete/', views.message_delete, name='message_delete'),
]
