from itertools import groupby

from django import forms
from django.forms.widgets import Select

from .models import (
    EXTRA_FIELD_CHOICES,
    Case,
    Restoration,
    RestorationType,
    Shade,
)
from .widgets import ExtraFieldsCheckboxWidget

# Extra fields rendered as plain on/off checkboxes on the frontend form.
BOOLEAN_EXTRA_FIELDS = [
    "add_blocker", "stain_and_glaze", "include_tibase",
    "assembled_bonded", "is_screw_retained", "vertex_articulator",
    "gold_anodizing",
]
# Extra fields that should reset to NULL (integers + FKs) when not enabled.
NULLABLE_EXTRA_FIELDS = {
    "number_of_units", "extra_separate_dies",
    "implant_type", "implant_size", "tibase_type",
}


class GroupedShadeSelect(Select):
    """Renders shade options as <optgroup> elements grouped by shade group."""

    def optgroups(self, name, value, attrs=None):
        groups = []
        index = 0
        str_values = {str(v) for v in value if v is not None and v != ""}

        # Empty option
        groups.append((None, [self.create_option(name, "", "---------", "" in value, index)], index))
        index += 1

        group_labels = dict(Shade.GROUP_CHOICES)
        shades = Shade.objects.order_by("group", "sort_order")
        for group_int, group_shades_iter in groupby(shades, key=lambda s: s.group):
            group_label = group_labels[group_int]
            subgroup = []
            for shade in group_shades_iter:
                selected = str(shade.pk) in str_values
                subgroup.append(self.create_option(name, shade.pk, shade.name, selected, index))
                index += 1
            groups.append((group_label, subgroup, index))

        return groups


class RestorationTypeAdminForm(forms.ModelForm):
    extra_fields = forms.MultipleChoiceField(
        required=False,
        widget=ExtraFieldsCheckboxWidget(),
    )

    class Meta:
        model = RestorationType
        fields = "__all__"

    def clean_extra_fields(self):
        return self.cleaned_data.get("extra_fields", [])


class RestorationAdminForm(forms.ModelForm):
    shade = forms.ModelChoiceField(
        queryset=Shade.objects.all(),
        required=False,
        widget=GroupedShadeSelect(),
    )

    class Meta:
        model = Restoration
        fields = "__all__"


class StyledFormMixin:
    """Applies the portal's shadcn-style CSS classes to all widgets."""

    def style_widgets(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "h-4 w-4 rounded border-input")
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("class", "input h-auto resize-y")
                widget.attrs.setdefault("rows", 3)
            else:
                widget.attrs.setdefault("class", "input")


class CaseForm(StyledFormMixin, forms.ModelForm):
    """Patient/case details captured once when the first restoration is added."""

    class Meta:
        model = Case
        fields = ["patient_name", "shipping_method", "mill_priority"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient_name"].widget.attrs.setdefault(
            "placeholder", "Patient name"
        )
        self.style_widgets()


class RestorationForm(StyledFormMixin, forms.ModelForm):
    """Frontend restoration form mirroring the admin's dynamic behavior.

    The ``case`` FK is assigned by the view. Field visibility and cascading
    selects are driven client-side by ``restoration_form.js``; ``clean()``
    enforces the same rules server-side and drops any values for extra fields
    that the chosen restoration type doesn't enable.
    """

    shade = forms.ModelChoiceField(
        queryset=Shade.objects.all(),
        required=False,
        widget=GroupedShadeSelect(),
    )

    class Meta:
        model = Restoration
        exclude = ["case", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Render the nullable booleans as plain on/off checkboxes.
        for name in BOOLEAN_EXTRA_FIELDS:
            self.fields[name] = forms.BooleanField(required=False)
        self.style_widgets()

    def _reset_value(self, field_name):
        if field_name in BOOLEAN_EXTRA_FIELDS:
            return False
        if field_name in NULLABLE_EXTRA_FIELDS:
            return None
        return ""

    def clean(self):
        cleaned = super().clean()
        rt = cleaned.get("restoration_type")

        # Drop values for extra fields the restoration type doesn't enable,
        # matching the client-side clearing of hidden fields.
        if rt is not None:
            enabled = set(rt.extra_fields or [])
            for field_name in EXTRA_FIELD_CHOICES:
                if field_name not in enabled:
                    cleaned[field_name] = self._reset_value(field_name)

        material = cleaned.get("material")
        product = cleaned.get("product")
        implant_type = cleaned.get("implant_type")
        implant_size = cleaned.get("implant_size")

        if rt is not None:
            if rt.requires_tooth_number and not cleaned.get("tooth_number"):
                self.add_error(
                    "tooth_number",
                    "Tooth number is required for this restoration type.",
                )
            if rt.requires_shade and not cleaned.get("shade"):
                self.add_error(
                    "shade", "Shade is required for this restoration type."
                )
            if material and not material.restoration_types.filter(pk=rt.pk).exists():
                self.add_error(
                    "material",
                    "This material isn't available for the selected restoration type.",
                )

        if material and material.has_products and not product:
            self.add_error("product", "Please select a product.")
        if material and product and product.material_id != material.id:
            self.add_error(
                "product", "This product doesn't belong to the selected material."
            )
        if implant_type and implant_size and implant_size.implant_type_id != implant_type.id:
            self.add_error(
                "implant_size",
                "This implant size doesn't belong to the selected implant type.",
            )

        return cleaned
