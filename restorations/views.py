from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CaseForm, RestorationForm
from .models import (
    Case,
    ImplantSize,
    ImplantType,
    Material,
    Product,
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
                case = case_form.save()
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
