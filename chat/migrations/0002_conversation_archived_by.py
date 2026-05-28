from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('chat', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversation',
            name='archived_by',
            field=models.ManyToManyField(blank=True, related_name='archived_conversations', to=settings.AUTH_USER_MODEL),
        ),
    ]
