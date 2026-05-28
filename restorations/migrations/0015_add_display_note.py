from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('restorations', '0014_rename_tibasetype_labels'),
    ]

    operations = [
        migrations.AddField(
            model_name='restorationtype',
            name='display_note',
            field=models.TextField(
                blank=True,
                help_text='Shown on the restoration form when this type is selected. Leave blank for no note.',
            ),
        ),
        migrations.AddField(
            model_name='material',
            name='display_note',
            field=models.TextField(
                blank=True,
                help_text='Shown on the restoration form when this material is selected. Leave blank for no note.',
            ),
        ),
        migrations.AddField(
            model_name='product',
            name='display_note',
            field=models.TextField(
                blank=True,
                help_text='Shown on the restoration form when this product is selected. Leave blank for no note.',
            ),
        ),
    ]
