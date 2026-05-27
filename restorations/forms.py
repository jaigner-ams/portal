from itertools import groupby

from django import forms
from django.forms.widgets import Select

from .models import Restoration, RestorationType, Shade
from .widgets import ExtraFieldsCheckboxWidget


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
