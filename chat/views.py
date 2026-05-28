"""Chat API endpoints.

All endpoints are JSON, ``@login_required``, namespaced under ``/chat/``.
Permissions are enforced both by ``Conversation.visible_to`` / ``can_reply``
and by per-endpoint role checks (see ``_is_rep``).
"""
import json

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from .models import Conversation, ConversationRead, Message

User = get_user_model()

# Cap a single response so a chat with thousands of messages can't blow up
# a poll request. The UI handles incremental fetch via ``?after=<id>``.
MAX_MESSAGES = 200
MAX_BODY = 5000
MAX_CONVERSATIONS = 200


def _is_rep(user):
    """admin OR staff role — the people who can claim/answer support chats."""
    return user.is_authenticated and (user.is_admin or user.is_staff_role)


def _visible_conversations(user):
    if not user.is_authenticated:
        return Conversation.objects.none()
    if user.is_lab:
        return Conversation.objects.filter(
            kind=Conversation.KIND_SUPPORT, lab_user=user,
        )
    if _is_rep(user):
        return Conversation.objects.filter(
            Q(kind=Conversation.KIND_SUPPORT)
            | Q(kind=Conversation.KIND_DM, participants=user)
        ).distinct()
    return Conversation.objects.none()


def _display_name(user):
    if not user:
        return ""
    return user.get_full_name() or user.username


def _unread_count(conv, user):
    try:
        cutoff = ConversationRead.objects.get(
            user=user, conversation=conv,
        ).last_read_at
    except ConversationRead.DoesNotExist:
        cutoff = None
    qs = conv.messages.exclude(sender=user)
    if cutoff is not None:
        qs = qs.filter(created_at__gt=cutoff)
    return qs.count()


def _serialize_conv(conv, user):
    peer = None
    peer_name = ""
    if conv.kind == Conversation.KIND_SUPPORT:
        if user.is_lab:
            peer = conv.claimed_by
            peer_name = _display_name(peer) or "AMS Support"
        else:
            peer = conv.lab_user
            peer_name = _display_name(peer) or "(Unknown lab)"
    else:
        # DM: peer is the other participant.
        peer = conv.participants.exclude(pk=user.pk).first()
        peer_name = _display_name(peer)

    last_msg = conv.messages.order_by("-created_at").first()
    return {
        "id": conv.pk,
        "kind": conv.kind,
        "peer_name": peer_name,
        "peer_id": peer.pk if peer else None,
        "lab_user_id": conv.lab_user_id,
        "lab_user_name": _display_name(conv.lab_user) if conv.lab_user_id else None,
        "claimed_by_id": conv.claimed_by_id,
        "claimed_by_name": (
            _display_name(conv.claimed_by) if conv.claimed_by_id else None
        ),
        "is_closed": conv.is_closed,
        "last_snippet": (last_msg.body[:120] if last_msg else ""),
        "last_message_at": (
            conv.last_message_at.isoformat() if conv.last_message_at else None
        ),
        "unread_count": _unread_count(conv, user),
        "can_reply": conv.can_reply(user),
    }


def _serialize_message(msg, user):
    return {
        "id": msg.pk,
        "sender_id": msg.sender_id,
        "sender_name": _display_name(msg.sender),
        "is_mine": msg.sender_id == user.id,
        "body": msg.body,
        "created_at": msg.created_at.isoformat(),
    }


# --- endpoints ---------------------------------------------------------------


@login_required
@require_GET
def state(request):
    """The poll endpoint. Returns visible conversations + unread totals."""
    convs = (
        _visible_conversations(request.user)
        .select_related("lab_user", "claimed_by")
        .prefetch_related("participants")
        .order_by("is_closed", "-last_message_at", "-created_at")
        [:MAX_CONVERSATIONS]
    )
    serialized = [_serialize_conv(c, request.user) for c in convs]
    return JsonResponse({
        "conversations": serialized,
        "total_unread": sum(c["unread_count"] for c in serialized),
        "is_rep": _is_rep(request.user),
        "is_lab": request.user.is_lab,
    })


@login_required
@require_GET
def messages(request, pk):
    conv = get_object_or_404(Conversation, pk=pk)
    if not conv.visible_to(request.user):
        return JsonResponse({"detail": "Forbidden"}, status=403)
    qs = conv.messages.select_related("sender").all()
    after = request.GET.get("after")
    if after:
        try:
            qs = qs.filter(pk__gt=int(after))
        except (TypeError, ValueError):
            pass
    msgs = list(qs[:MAX_MESSAGES])
    return JsonResponse({
        "messages": [_serialize_message(m, request.user) for m in msgs],
    })


def _parse_json(request):
    try:
        return json.loads(request.body or b"{}"), None
    except json.JSONDecodeError:
        return None, JsonResponse({"detail": "Invalid JSON"}, status=400)


@login_required
@require_POST
def send(request, pk):
    conv = get_object_or_404(Conversation, pk=pk)
    if not conv.can_reply(request.user):
        return JsonResponse({"detail": "Forbidden"}, status=403)
    data, err = _parse_json(request)
    if err:
        return err
    body = (data.get("body") or "").strip()
    if not body:
        return JsonResponse({"detail": "Empty message"}, status=400)
    msg = Message.objects.create(
        conversation=conv, sender=request.user, body=body[:MAX_BODY],
    )
    conv.last_message_at = msg.created_at
    conv.save(update_fields=["last_message_at", "updated_at"])
    # Sender's own messages count as "read" up to now.
    ConversationRead.objects.update_or_create(
        user=request.user, conversation=conv,
    )
    return JsonResponse({"message": _serialize_message(msg, request.user)})


@login_required
@require_POST
def claim(request, pk):
    conv = get_object_or_404(Conversation, pk=pk)
    if not _is_rep(request.user) or conv.kind != Conversation.KIND_SUPPORT:
        return JsonResponse({"detail": "Forbidden"}, status=403)
    if conv.claimed_by_id and conv.claimed_by_id != request.user.id:
        return JsonResponse({"detail": "Already claimed"}, status=409)
    conv.claimed_by = request.user
    conv.save(update_fields=["claimed_by", "updated_at"])
    return JsonResponse({"conversation": _serialize_conv(conv, request.user)})


@login_required
@require_POST
def unclaim(request, pk):
    conv = get_object_or_404(Conversation, pk=pk)
    if not _is_rep(request.user) or conv.kind != Conversation.KIND_SUPPORT:
        return JsonResponse({"detail": "Forbidden"}, status=403)
    if conv.claimed_by_id != request.user.id:
        return JsonResponse({"detail": "Not your claim"}, status=403)
    conv.claimed_by = None
    conv.save(update_fields=["claimed_by", "updated_at"])
    return JsonResponse({"conversation": _serialize_conv(conv, request.user)})


@login_required
@require_POST
def close_conv(request, pk):
    conv = get_object_or_404(Conversation, pk=pk)
    if not conv.visible_to(request.user):
        return JsonResponse({"detail": "Forbidden"}, status=403)
    if conv.kind == Conversation.KIND_SUPPORT:
        # Lab can close their own; rep can close if they're the claimer or
        # the conversation is unclaimed.
        if request.user.is_lab and conv.lab_user_id != request.user.id:
            return JsonResponse({"detail": "Forbidden"}, status=403)
        if (
            _is_rep(request.user)
            and conv.claimed_by_id
            and conv.claimed_by_id != request.user.id
        ):
            return JsonResponse(
                {"detail": "Claimed by another rep"}, status=403,
            )
    conv.is_closed = True
    conv.save(update_fields=["is_closed", "updated_at"])
    return JsonResponse({"conversation": _serialize_conv(conv, request.user)})


@login_required
@require_POST
def mark_read(request, pk):
    conv = get_object_or_404(Conversation, pk=pk)
    if not conv.visible_to(request.user):
        return JsonResponse({"detail": "Forbidden"}, status=403)
    ConversationRead.objects.update_or_create(
        user=request.user, conversation=conv,
    )
    return JsonResponse({"ok": True})


@login_required
@require_POST
def start_support(request):
    if not request.user.is_lab:
        return JsonResponse(
            {"detail": "Only lab users can start a support chat"}, status=403,
        )
    # Idempotent: reuse the lab's open support thread if one exists.
    conv = (
        Conversation.objects
        .filter(
            kind=Conversation.KIND_SUPPORT,
            lab_user=request.user,
            is_closed=False,
        )
        .order_by("-created_at")
        .first()
    )
    if not conv:
        conv = Conversation.objects.create(
            kind=Conversation.KIND_SUPPORT, lab_user=request.user,
        )
    return JsonResponse({"conversation": _serialize_conv(conv, request.user)})


@login_required
@require_POST
def start_dm(request):
    if not _is_rep(request.user):
        return JsonResponse({"detail": "Forbidden"}, status=403)
    data, err = _parse_json(request)
    if err:
        return err
    try:
        user_id = int(data.get("user_id"))
    except (TypeError, ValueError):
        return JsonResponse({"detail": "Invalid user_id"}, status=400)
    if user_id == request.user.id:
        return JsonResponse({"detail": "Cannot DM yourself"}, status=400)
    try:
        peer = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({"detail": "User not found"}, status=404)
    if not (peer.is_admin or peer.is_staff_role):
        return JsonResponse(
            {"detail": "Can only DM admin or staff users"}, status=403,
        )
    # Existing 1:1 DM between these two? — find a DM containing BOTH.
    existing = (
        Conversation.objects
        .filter(kind=Conversation.KIND_DM, participants=request.user)
        .filter(participants=peer)
        .first()
    )
    if existing:
        return JsonResponse(
            {"conversation": _serialize_conv(existing, request.user)},
        )
    conv = Conversation.objects.create(kind=Conversation.KIND_DM)
    conv.participants.add(request.user, peer)
    return JsonResponse({"conversation": _serialize_conv(conv, request.user)})


@login_required
@require_GET
def search_users(request):
    """User picker for the DM flow. Reps only; returns admin+staff."""
    if not _is_rep(request.user):
        return JsonResponse({"users": []})
    q = (request.GET.get("q") or "").strip()
    qs = (
        User.objects
        .filter(role__in=["admin", "staff"], is_active=True)
        .exclude(pk=request.user.pk)
    )
    if q:
        qs = qs.filter(
            Q(username__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
        )
    return JsonResponse({
        "users": [
            {
                "id": u.pk,
                "name": _display_name(u),
                "role": u.role,
            }
            for u in qs.order_by("first_name", "last_name", "username")[:20]
        ],
    })
