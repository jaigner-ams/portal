from django.contrib import admin

from .models import SiteMessage


@admin.register(SiteMessage)
class SiteMessageAdmin(admin.ModelAdmin):
    list_display = ("message_type", "is_active", "short_message", "updated_at")
    list_filter = ("is_active", "message_type")
    list_editable = ("is_active",)
    readonly_fields = ("created_at", "updated_at")

    def short_message(self, obj):
        return obj.message[:80] + "..." if len(obj.message) > 80 else obj.message
    short_message.short_description = "Message"
