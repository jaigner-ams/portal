from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('restorations', '0013_batch_case_restoration_case'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='tibasetype',
            options={
                'ordering': ['name'],
                'verbose_name': 'Scan Flag/Body Brand',
                'verbose_name_plural': 'Scan Flag/Body Brands',
            },
        ),
    ]
