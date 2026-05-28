from django.db import migrations, models
from django.db.models import F


def backfill_submitted_at(apps, schema_editor):
    """Existing cases predate the draft/submit gate — treat them as already
    submitted (submitted_at = created_at) so they stay visible to admins/staff
    after this migration runs."""
    Case = apps.get_model("restorations", "Case")
    Case.objects.filter(submitted_at__isnull=True).update(
        submitted_at=F("created_at"),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('restorations', '0016_restoration_cancellation_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='case',
            name='submitted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(
            backfill_submitted_at,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
