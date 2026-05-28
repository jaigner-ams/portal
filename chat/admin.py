from django.contrib import admin

from .models import Conversation, ConversationRead, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = [
        "id", "kind", "lab_user", "claimed_by",
        "is_closed", "last_message_at", "created_at",
    ]
    list_filter = ["kind", "is_closed"]
    search_fields = [
        "lab_user__username", "lab_user__email",
        "claimed_by__username", "participants__username",
    ]
    readonly_fields = ["created_at", "updated_at", "last_message_at"]
    filter_horizontal = ["participants", "archived_by"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "conversation", "sender", "created_at"]
    list_filter = ["sender"]
    search_fields = ["body", "sender__username"]
    readonly_fields = ["created_at"]


@admin.register(ConversationRead)
class ConversationReadAdmin(admin.ModelAdmin):
    list_display = ["user", "conversation", "last_read_at"]
    readonly_fields = ["last_read_at"]
