from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse

from .models import ImplantSize, ImplantType, Material, Product, RestorationType


@staff_member_required
def restoration_type_options(request):
    restoration_type_id = request.GET.get("restoration_type")
    if restoration_type_id:
        try:
            rt = RestorationType.objects.get(pk=restoration_type_id)
        except RestorationType.DoesNotExist:
            return JsonResponse({"materials": [], "requires_tooth_number": True, "extra_fields": []})
        materials = list(
            Material.objects.filter(restoration_types=rt).values("id", "name")
        )
        requires_tooth_number = rt.requires_tooth_number
        requires_shade = rt.requires_shade
        extra_fields = rt.extra_fields or []
    else:
        materials = []
        requires_tooth_number = True
        requires_shade = False
        extra_fields = []
    return JsonResponse({
        "materials": materials,
        "requires_tooth_number": requires_tooth_number,
        "requires_shade": requires_shade,
        "extra_fields": extra_fields,
    })


@staff_member_required
def material_products(request):
    material_id = request.GET.get("material")
    if material_id:
        try:
            mat = Material.objects.get(pk=material_id)
        except Material.DoesNotExist:
            return JsonResponse({"products": [], "has_products": False})
        products = list(
            Product.objects.filter(material=mat).values("id", "name")
        ) if mat.has_products else []
        return JsonResponse({"products": products, "has_products": mat.has_products})
    return JsonResponse({"products": [], "has_products": False})


@staff_member_required
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
