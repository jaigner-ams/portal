from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from chat.models import Conversation, Message

from .forms import CaseForm, RestorationForm
from .models import (
    Case,
    ImplantSize,
    ImplantType,
    Material,
    Product,
    Restoration,
    RestorationType,
)


@login_required
def restoration_add(request):
    """Create a new case and add its first restoration."""
    case_form = CaseForm(request.POST or None)
    restoration_form = RestorationForm(request.POST or None)
    if request.method == "POST":
        if case_form.is_valid() and restoration_form.is_valid():
            with transaction.atomic():
                case = case_form.save(commit=False)
                case.created_by = request.user
                case.save()
                restoration = restoration_form.save(commit=False)
                restoration.case = case
                restoration.save()
            messages.success(request, "Case created and restoration added.")
            return redirect("restorations:case-detail", pk=case.pk)
    return render(request, "restorations/restoration_form.html", {
        "case_form": case_form,
        "restoration_form": restoration_form,
    })


@login_required
def case_detail(request, pk):
    """Show a case with its restorations and add more to it."""
    case = get_object_or_404(Case, pk=pk)
    restoration_form = RestorationForm(request.POST or None)
    if request.method == "POST":
        if restoration_form.is_valid():
            restoration = restoration_form.save(commit=False)
            restoration.case = case
            restoration.save()
            messages.success(request, "Restoration added.")
            return redirect("restorations:case-detail", pk=case.pk)
    return render(request, "restorations/case_detail.html", {
        "case": case,
        "restorations": case.restorations.all(),
        "restoration_form": restoration_form,
    })


@login_required
def orders(request):
    """List of restoration orders.

    - Lab users see only their own cases.
    - Admin/staff users see every lab-created case (read-only) with a search
      box that filters by patient name or lab user (name / username / email).
    """
    user = request.user
    if user.is_lab:
        qs = Case.objects.filter(created_by=user)
        is_lab_view = True
    elif user.is_admin or user.is_staff_role:
        # Show lab-created cases that have been submitted by the lab; legacy
        # cases without a created_by still appear (they predate the field).
        # Drafts (submitted_at IS NULL) are hidden from admin/staff until the
        # lab clicks Submit on the case.
        qs = Case.objects.filter(
            Q(created_by__role="lab") | Q(created_by__isnull=True),
            submitted_at__isnull=False,
        )
        is_lab_view = False
    else:
        return HttpResponseForbidden("Orders are not available for your role.")

    q = (request.GET.get("q") or "").strip()
    if q and not is_lab_view:
        qs = qs.filter(
            Q(patient_name__icontains=q)
            | Q(created_by__first_name__icontains=q)
            | Q(created_by__last_name__icontains=q)
            | Q(created_by__username__icontains=q)
            | Q(created_by__email__icontains=q)
        )

    cases = (
        qs.select_related("batch", "created_by")
        .prefetch_related(
            "restorations__restoration_type",
            "restorations__material",
            "restorations__product",
            "restorations__cancellation_conversation__claimed_by",
        )
        .order_by("-created_at")
        [:200]
    )
    return render(request, "restorations/orders.html", {
        "cases": cases,
        "is_lab_view": is_lab_view,
        "q": q,
    })


@login_required
def case_print(request, pk):
    """Standalone print-friendly view of a single case.

    Lab can print their own cases (draft or submitted); admins/staff can
    print any case. The template is black-and-white, sized so the content
    fits in the top half of a portrait letter sheet — fold the paper in half
    along the horizontal midpoint and the printed side is visible.
    """
    case = get_object_or_404(
        Case.objects.select_related("created_by")
        .prefetch_related(
            "restorations__restoration_type",
            "restorations__material",
            "restorations__product",
            "restorations__shade",
            "restorations__implant_type",
            "restorations__implant_size",
            "restorations__tibase_type",
        ),
        pk=pk,
    )
    user = request.user
    if user.is_lab:
        if case.created_by_id != user.id:
            return HttpResponseForbidden("Not your case.")
    elif not (user.is_admin or user.is_staff_role):
        return HttpResponseForbidden("Cannot print this case.")
    return render(request, "restorations/case_print.html", {"case": case})


@login_required
@require_POST
def submit_case(request, pk):
    """Lab submits a draft case so admins/staff can see it in Orders."""
    case = get_object_or_404(Case, pk=pk)
    if case.created_by_id != request.user.id:
        return HttpResponseForbidden("Not your case.")
    if case.submitted_at is None:
        if not case.restorations.exists():
            messages.error(
                request,
                "Add at least one restoration before submitting this case.",
            )
            return redirect("restorations:case-detail", pk=case.pk)
        case.submitted_at = timezone.now()
        case.save(update_fields=["submitted_at", "updated_at"])
        messages.success(request, "Case submitted to AMS.")
    return redirect("restorations:orders")


@login_required
@require_POST
def cancel_restoration(request, pk):
    """Lab cancels (or removes) one of their restorations.

    - **Draft case** (never submitted): just delete the restoration row.
      Nothing was sent to AMS, so no cancellation alert is created.
    - **Submitted case**: mark the restoration cancelled and create a chat
      ``Conversation`` (kind='cancellation') so admins/staff see and claim
      the alert.
    """
    restoration = get_object_or_404(
        Restoration.objects.select_related("case", "restoration_type", "material"),
        pk=pk,
    )
    case = restoration.case
    if case is None or case.created_by_id != request.user.id:
        return HttpResponseForbidden("Not your restoration.")
    if restoration.is_cancelled:
        messages.info(request, "That restoration was already cancelled.")
        return redirect("restorations:orders")

    # Draft branch: silently remove. AMS never saw this restoration.
    if case.submitted_at is None:
        restoration.delete()
        messages.success(request, "Restoration removed from draft case.")
        return redirect("restorations:case-detail", pk=case.pk)

    reason = (request.POST.get("reason") or "").strip()
    # Compose the system message admins/staff will see.
    lab_name = request.user.get_full_name() or request.user.username
    parts = [
        f"Lab {lab_name} cancelled restoration #{restoration.pk}.",
        f"Patient: {case.patient_name}.",
        f"Type: {restoration.restoration_type}.",
    ]
    if restoration.tooth_number:
        parts.append(f"Tooth: #{restoration.tooth_number}.")
    if restoration.material_id:
        parts.append(f"Material: {restoration.material}.")
    if restoration.product_id:
        parts.append(f"Product: {restoration.product}.")
    if reason:
        parts.append(f"Reason: {reason}")
    body = " ".join(parts)

    with transaction.atomic():
        conv = Conversation.objects.create(
            kind=Conversation.KIND_CANCELLATION,
            lab_user=request.user,
        )
        msg = Message.objects.create(
            conversation=conv, sender=request.user, body=body,
        )
        conv.last_message_at = msg.created_at
        conv.save(update_fields=["last_message_at", "updated_at"])

        restoration.is_cancelled = True
        restoration.cancelled_at = timezone.now()
        restoration.cancellation_reason = reason
        restoration.cancellation_conversation = conv
        restoration.save(update_fields=[
            "is_cancelled", "cancelled_at", "cancellation_reason",
            "cancellation_conversation", "updated_at",
        ])

    messages.success(
        request,
        "Cancellation submitted. AMS support has been notified.",
    )
    return redirect("restorations:orders")


@login_required
def restoration_type_options(request):
    restoration_type_id = request.GET.get("restoration_type")
    if restoration_type_id:
        try:
            rt = RestorationType.objects.get(pk=restoration_type_id)
        except RestorationType.DoesNotExist:
            return JsonResponse({
                "materials": [], "requires_tooth_number": True,
                "requires_shade": False, "extra_fields": [], "display_note": "",
            })
        materials = list(
            Material.objects.filter(restoration_types=rt)
            .values("id", "name", "display_note")
        )
        requires_tooth_number = rt.requires_tooth_number
        requires_shade = rt.requires_shade
        extra_fields = rt.extra_fields or []
        display_note = rt.display_note
    else:
        materials = []
        requires_tooth_number = True
        requires_shade = False
        extra_fields = []
        display_note = ""
    return JsonResponse({
        "materials": materials,
        "requires_tooth_number": requires_tooth_number,
        "requires_shade": requires_shade,
        "extra_fields": extra_fields,
        "display_note": display_note,
    })


@login_required
def material_products(request):
    material_id = request.GET.get("material")
    if material_id:
        try:
            mat = Material.objects.get(pk=material_id)
        except Material.DoesNotExist:
            return JsonResponse({"products": [], "has_products": False})
        products = list(
            Product.objects.filter(material=mat)
            .values("id", "name", "display_note")
        ) if mat.has_products else []
        return JsonResponse({"products": products, "has_products": mat.has_products})
    return JsonResponse({"products": [], "has_products": False})


@login_required
def implant_sizes(request):
    implant_type_id = request.GET.get("implant_type")
    if implant_type_id:
        try:
            it = ImplantType.objects.get(pk=implant_type_id)
        except ImplantType.DoesNotExist:
            return JsonResponse({"sizes": []})
        sizes = list(
            ImplantSize.objects.filter(implant_type=it).values("id", "name")
        )
        return JsonResponse({"sizes": sizes})
    return JsonResponse({"sizes": []})
