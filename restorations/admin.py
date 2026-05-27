from django.contrib import admin

from .forms import RestorationAdminForm, RestorationTypeAdminForm
from django.utils.text import Truncator

from .models import (
    Batch,
    Case,
    ImplantSize,
    ImplantType,
    Material,
    Product,
    Restoration,
    RestorationFile,
    RestorationType,
    Shade,
    TiBaseType,
)


@admin.register(Shade)
class ShadeAdmin(admin.ModelAdmin):
    list_display = ["name", "get_group_display", "sort_order"]
    list_filter = ["group"]
    search_fields = ["name"]
    ordering = ["group", "sort_order"]


@admin.register(ImplantType)
class ImplantTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at", "updated_at"]
    search_fields = ["name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ImplantSize)
class ImplantSizeAdmin(admin.ModelAdmin):
    list_display = ["name", "implant_type", "created_at", "updated_at"]
    list_filter = ["implant_type"]
    search_fields = ["name", "implant_type__name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(TiBaseType)
class TiBaseTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at", "updated_at"]
    search_fields = ["name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(RestorationType)
class RestorationTypeAdmin(admin.ModelAdmin):
    form = RestorationTypeAdminForm
    list_display = ["name", "requires_tooth_number", "requires_shade", "created_at", "updated_at"]
    list_filter = ["requires_tooth_number", "requires_shade"]
    search_fields = ["name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ["name", "has_products", "created_at", "updated_at"]
    list_filter = ["has_products"]
    search_fields = ["name"]
    filter_horizontal = ["restoration_types"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "material", "created_at", "updated_at"]
    list_filter = ["material"]
    search_fields = ["name", "material__name"]
    readonly_fields = ["created_at", "updated_at"]


class CaseInline(admin.TabularInline):
    model = Case
    extra = 0
    fields = ["patient_name", "mill_priority", "shipping_method"]
    show_change_link = True


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ["id", "truncated_batch_note", "case_count", "created_at"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [CaseInline]
    fieldsets = (
        (None, {"fields": ("batch_note",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Batch Note")
    def truncated_batch_note(self, obj):
        return Truncator(obj.batch_note).chars(50)

    @admin.display(description="Cases")
    def case_count(self, obj):
        return obj.cases.count()


class RestorationInline(admin.TabularInline):
    model = Restoration
    extra = 0
    fields = ["restoration_type", "tooth_number", "material"]
    show_change_link = True


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = [
        "patient_name", "mill_priority", "shipping_method",
        "batch", "restoration_count", "created_at",
    ]
    list_filter = ["mill_priority", "shipping_method"]
    search_fields = ["patient_name"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [RestorationInline]
    fieldsets = (
        (None, {
            "fields": ("patient_name", "mill_priority", "shipping_method", "batch"),
        }),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Restorations")
    def restoration_count(self, obj):
        return obj.restorations.count()


class RestorationFileInline(admin.TabularInline):
    model = RestorationFile
    extra = 1
    readonly_fields = ["uploaded_at"]


@admin.register(Restoration)
class RestorationAdmin(admin.ModelAdmin):
    form = RestorationAdminForm
    list_display = ["restoration_type", "tooth_number", "shade", "material", "product", "created_at"]
    list_filter = ["restoration_type", "material", "product"]
    search_fields = ["restoration_type__name", "material__name", "product__name"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [RestorationFileInline]
    fieldsets = (
        (None, {
            "fields": (
                "case", "restoration_type", "tooth_number", "material", "product", "shade",
            ),
        }),
        ("Type-Specific Options", {
            "fields": (
                "add_blocker", "stain_and_glaze", "design_service",
                "include_tibase", "assembled_bonded",
                "implant_type", "implant_size", "tibase_type",
                "number_of_units", "is_screw_retained",
                "bar_details",
                "model_type", "arches", "size",
                "extra_separate_dies", "vertex_articulator",
                "model_unit_details",
                "gold_anodizing",
            ),
        }),
        ("Case Note", {
            "fields": ("case_note",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.restoration_type_id:
            form.base_fields["material"].queryset = Material.objects.filter(
                restoration_types=obj.restoration_type
            )
        else:
            form.base_fields["material"].queryset = Material.objects.none()
        if obj and obj.material_id:
            form.base_fields["product"].queryset = Product.objects.filter(
                material=obj.material
            )
        else:
            form.base_fields["product"].queryset = Product.objects.none()
        if obj and obj.implant_type_id:
            form.base_fields["implant_size"].queryset = ImplantSize.objects.filter(
                implant_type=obj.implant_type
            )
        else:
            form.base_fields["implant_size"].queryset = ImplantSize.objects.none()
        return form

    class Media:
        js = ("restorations/js/restoration_admin.js",)
