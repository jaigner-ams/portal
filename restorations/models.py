from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


# All possible extra fields for restorations, keyed by field name.
# Used by the admin widget to render checkboxes on RestorationType.
EXTRA_FIELD_CHOICES = {
    "add_blocker": "Add Blocker",
    "stain_and_glaze": "Stain & Glaze",
    "design_service": "Design Service",
    "include_tibase": "Include Ti-Base",
    "assembled_bonded": "Assembled & Bonded",
    "implant_type": "Implant Type",
    "implant_size": "Implant Size",
    "tibase_type": "Scan Flag/Body Brand",
    "number_of_units": "Number of Units",
    "is_screw_retained": "Is Screw-Retained",
    "bar_details": "Bar Details",
    "model_type": "Model Type",
    "arches": "Arches",
    "size": "Size",
    "extra_separate_dies": "Extra Separate Dies",
    "vertex_articulator": "Vertex Articulator",
    "model_unit_details": "Model Unit Details",
    "gold_anodizing": "Gold Anodizing",
}


class Shade(models.Model):
    GROUP_OTHER = 1
    GROUP_VITA_CLASSICAL = 2
    GROUP_VITA_3D = 3
    GROUP_IVOCLAR_BLEACH = 4
    GROUP_CHOICES = [
        (GROUP_OTHER, "Other"),
        (GROUP_VITA_CLASSICAL, "VITA Classical A1-D4"),
        (GROUP_VITA_3D, "VITA 3D-MASTER"),
        (GROUP_IVOCLAR_BLEACH, "Ivoclar Bleach"),
    ]

    name = models.CharField(max_length=100, unique=True)
    group = models.PositiveSmallIntegerField(choices=GROUP_CHOICES)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shade"
        verbose_name_plural = "Shades"
        ordering = ["group", "sort_order"]

    def __str__(self):
        return self.name


class ImplantType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Implant Type"
        verbose_name_plural = "Implant Types"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ImplantSize(models.Model):
    name = models.CharField(max_length=100)
    implant_type = models.ForeignKey(
        ImplantType,
        on_delete=models.CASCADE,
        related_name="sizes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Implant Size"
        verbose_name_plural = "Implant Sizes"
        unique_together = [("implant_type", "name")]
        ordering = ["implant_type", "name"]

    def __str__(self):
        return f"{self.implant_type} — {self.name}"


class TiBaseType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Scan Flag/Body Brand"
        verbose_name_plural = "Scan Flag/Body Brands"
        ordering = ["name"]

    def __str__(self):
        return self.name


class RestorationType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    requires_tooth_number = models.BooleanField(default=True)
    requires_shade = models.BooleanField(default=False)
    extra_fields = models.JSONField(default=list, blank=True)
    display_note = models.TextField(
        blank=True,
        help_text="Shown on the restoration form when this type is selected. Leave blank for no note.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Restoration Type"
        verbose_name_plural = "Restoration Types"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Material(models.Model):
    name = models.CharField(max_length=100, unique=True)
    restoration_types = models.ManyToManyField(
        RestorationType,
        blank=True,
        related_name="materials",
    )
    has_products = models.BooleanField(default=False)
    display_note = models.TextField(
        blank=True,
        help_text="Shown on the restoration form when this material is selected. Leave blank for no note.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Material"
        verbose_name_plural = "Materials"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=100, unique=True)
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name="products",
    )
    display_note = models.TextField(
        blank=True,
        help_text="Shown on the restoration form when this product is selected. Leave blank for no note.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Batch(models.Model):
    batch_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Batch"
        verbose_name_plural = "Batches"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Batch #{self.pk}"


class Case(models.Model):
    MILL_PRIORITY_CHOICES = [
        ("mill_today_economy", "Mill Today at Economy Pricing"),
    ]
    SHIPPING_METHOD_CHOICES = [
        ("regular", "Regular Shipping (2 Business Days)"),
        ("next_day_saver", "Next Day Air Saver (After Noon)"),
        ("next_day", "Next Day Air (By Noon)"),
    ]

    patient_name = models.CharField(max_length=200)
    mill_priority = models.CharField(
        max_length=30, choices=MILL_PRIORITY_CHOICES, blank=True,
    )
    shipping_method = models.CharField(
        max_length=20, choices=SHIPPING_METHOD_CHOICES,
    )
    batch = models.ForeignKey(
        Batch,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cases",
    )
    # The user who created this case (typically a lab user). Lets the lab's
    # "Your orders" page query their own cases. Nullable for existing rows
    # created before this field was added.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cases_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Case"
        verbose_name_plural = "Cases"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.patient_name} (Case #{self.pk})"


class Restoration(models.Model):
    DESIGN_SERVICE_CHOICES = [
        ("mill_only", "Mill Only"),
        ("design_and_mill", "Design & Mill"),
    ]
    MODEL_TYPE_CHOICES = [
        ("removable_dies", "Removable Dies"),
        ("solid", "Solid"),
        ("implant", "Implant"),
    ]
    ARCHES_CHOICES = [
        ("both", "Both"),
        ("upper", "Upper"),
        ("lower", "Lower"),
    ]
    SIZE_CHOICES = [
        ("quad", "Quad"),
        ("full", "Full"),
        ("check", "Check"),
    ]

    case = models.ForeignKey(
        Case,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="restorations",
    )
    restoration_type = models.ForeignKey(
        RestorationType,
        on_delete=models.PROTECT,
    )
    tooth_number = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(32)],
    )
    material = models.ForeignKey(
        Material,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    product = models.ForeignKey(
        Product,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    shade = models.ForeignKey(
        Shade,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )

    # --- Type-specific extra fields ---
    # Booleans
    add_blocker = models.BooleanField(null=True, blank=True)
    stain_and_glaze = models.BooleanField(null=True, blank=True)
    include_tibase = models.BooleanField(null=True, blank=True)
    assembled_bonded = models.BooleanField(null=True, blank=True)
    is_screw_retained = models.BooleanField(null=True, blank=True)
    vertex_articulator = models.BooleanField(null=True, blank=True)
    gold_anodizing = models.BooleanField(null=True, blank=True)

    # Choices
    design_service = models.CharField(
        max_length=20, choices=DESIGN_SERVICE_CHOICES, blank=True,
    )
    model_type = models.CharField(
        max_length=20, choices=MODEL_TYPE_CHOICES, blank=True,
    )
    arches = models.CharField(
        max_length=10, choices=ARCHES_CHOICES, blank=True,
    )
    size = models.CharField(
        max_length=10, choices=SIZE_CHOICES, blank=True,
    )

    # Integers
    number_of_units = models.PositiveSmallIntegerField(null=True, blank=True)
    extra_separate_dies = models.PositiveSmallIntegerField(null=True, blank=True)

    # Text
    bar_details = models.TextField(blank=True)
    model_unit_details = models.TextField(blank=True)

    # FKs
    implant_type = models.ForeignKey(
        ImplantType,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    implant_size = models.ForeignKey(
        ImplantSize,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    tibase_type = models.ForeignKey(
        TiBaseType,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )

    # Case note
    case_note = models.TextField(blank=True)

    # --- Cancellation state ---
    is_cancelled = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    # The chat Conversation (kind='cancellation') created when the lab cancels.
    # Lets the lab's orders page show the alert's claim/resolve status without
    # an extra lookup, and ensures one Conversation per cancelled restoration.
    cancellation_conversation = models.OneToOneField(
        "chat.Conversation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cancelled_restoration",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Restoration"
        verbose_name_plural = "Restorations"
        ordering = ["-created_at"]

    def __str__(self):
        parts = [str(self.restoration_type)]
        if self.tooth_number:
            parts.append(f"#{self.tooth_number}")
        if self.material:
            parts.append(str(self.material))
        return " — ".join(parts)


class RestorationFile(models.Model):
    restoration = models.ForeignKey(
        Restoration,
        on_delete=models.CASCADE,
        related_name="files",
    )
    file = models.FileField(upload_to="restorations/%Y/%m/")
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "File"
        verbose_name_plural = "Files"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.file.name
