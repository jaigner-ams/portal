from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_conversation_archived_by'),
    ]

    operations = [
        migrations.AlterField(
            model_name='conversation',
            name='kind',
            field=models.CharField(
                choices=[
                    ('support', 'Support'),
                    ('dm', 'Direct message'),
                    ('cancellation', 'Cancellation'),
                ],
                max_length=15,
            ),
        ),
    ]
