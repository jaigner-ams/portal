import json

from django.forms.widgets import CheckboxSelectMultiple

from .models import EXTRA_FIELD_CHOICES


class ExtraFieldsCheckboxWidget(CheckboxSelectMultiple):
    """Renders EXTRA_FIELD_CHOICES as checkboxes for the extra_fields JSONField."""

    def __init__(self, attrs=None):
        choices = [(k, v) for k, v in EXTRA_FIELD_CHOICES.items()]
        super().__init__(attrs=attrs, choices=choices)

    def format_value(self, value):
        """Convert JSON list (or string) into the list format CheckboxSelectMultiple expects."""
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                value = []
        if value is None:
            value = []
        return value

    def value_from_datadict(self, data, files, name):
        """Return the list of checked field names."""
        return data.getlist(name)
