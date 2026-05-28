from django.conf import settings
from django.db import models


class Conversation(models.Model):
    """A chat thread.

    Two kinds:
    - ``support``: opened by a lab user. Visible to all admin/staff (reps);
      only the rep listed in ``claimed_by`` can reply (or the lab themself).
    - ``dm``: a 1:1 thread between two reps (stored in ``participants``).
    """

    KIND_SUPPORT = "support"
    KIND_DM = "dm"
    KIND_CHOICES = [
        (KIND_SUPPORT, "Support"),
        (KIND_DM, "Direct message"),
    ]

    kind = models.CharField(max_length=10, choices=KIND_CHOICES)

    # Support-only fields.
    lab_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="lab_conversations",
    )
    claimed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="claimed_conversations",
    )

    # DM-only: 1:1 between two reps.
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="dm_conversations",
    )

    # Per-user archive: users in here have hidden this conversation from their
    # own list. Cleared on each new message so important threads bubble back up.
    archived_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="archived_conversations",
    )

    is_closed = models.BooleanField(default=False)
    last_message_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_message_at", "-created_at"]

    def __str__(self):
        if self.kind == self.KIND_SUPPORT:
            return f"Support #{self.pk}"
        return f"DM #{self.pk}"

    # --- permission helpers ---------------------------------------------------

    def visible_to(self, user):
        if not user.is_authenticated:
            return False
        if user.is_lab:
            return (
                self.kind == self.KIND_SUPPORT
                and self.lab_user_id == user.id
            )
        if user.is_admin or user.is_staff_role:
            if self.kind == self.KIND_SUPPORT:
                return True
            return self.participants.filter(pk=user.pk).exists()
        return False

    def can_reply(self, user):
        if self.is_closed or not self.visible_to(user):
            return False
        if self.kind == self.KIND_SUPPORT:
            if user.is_lab:
                return self.lab_user_id == user.id
            # Reps: only the claimed rep may reply.
            return self.claimed_by_id == user.id
        # DM: any participant may reply.
        return True


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sent_messages",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Message #{self.pk} in {self.conversation_id}"


class ConversationRead(models.Model):
    """Tracks how far through a conversation each user has read.

    Unread count = messages in the conversation with ``created_at`` greater
    than this user's ``last_read_at``, excluding their own messages.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversation_reads",
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="reads",
    )
    last_read_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user", "conversation")]
