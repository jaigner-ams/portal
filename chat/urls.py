from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("api/state/", views.state, name="state"),
    path("api/conversations/<int:pk>/messages/", views.messages, name="messages"),
    path("api/conversations/<int:pk>/send/", views.send, name="send"),
    path("api/conversations/<int:pk>/claim/", views.claim, name="claim"),
    path("api/conversations/<int:pk>/unclaim/", views.unclaim, name="unclaim"),
    path("api/conversations/<int:pk>/close/", views.close_conv, name="close"),
    path("api/conversations/<int:pk>/read/", views.mark_read, name="read"),
    path("api/conversations/start_support/", views.start_support, name="start_support"),
    path("api/conversations/start_dm/", views.start_dm, name="start_dm"),
    path("api/users/", views.search_users, name="users"),
]
