from django.db import models


class SiteMessage(models.Model):
    class MessageType(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"
        SUCCESS = "success", "Success"

    message = models.TextField(help_text="Message displayed at the top of every page.")
    message_type = models.CharField(
        max_length=10,
        choices=MessageType.choices,
        default=MessageType.INFO,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Message"
        verbose_name_plural = "Site Messages"

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"[{self.get_message_type_display()}] [{status}] {self.message[:60]}"
