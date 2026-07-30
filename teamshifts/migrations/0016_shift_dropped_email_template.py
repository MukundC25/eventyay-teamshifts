from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('teamshifts', '0015_shiftassignment_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='teamshiftsemailtemplate',
            name='role',
            field=models.CharField(
                choices=[
                    ('teamshifts.application.received', 'Application received'),
                    ('teamshifts.application.accepted', 'Application accepted'),
                    ('teamshifts.application.rejected', 'Application rejected'),
                    ('teamshifts.shift.dropped', 'Shift dropped by volunteer'),
                ],
                max_length=40,
            ),
        ),
    ]
