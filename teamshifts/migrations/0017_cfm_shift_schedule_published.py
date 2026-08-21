from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("teamshifts", "0016_shiftassignment_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="callforteammembers",
            name="shift_schedule_published",
            field=models.BooleanField(
                default=False,
                help_text="When enabled, accepted team members can view the shift schedule. Changes are live after the first publish.",
                verbose_name="Shift schedule published",
            ),
        ),
    ]
