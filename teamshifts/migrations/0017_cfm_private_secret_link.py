from django.db import migrations, models

import teamshifts.models


class Migration(migrations.Migration):
    dependencies = [
        ("teamshifts", "0016_shiftassignment_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="callforteammembers",
            name="cfm_private",
            field=models.BooleanField(
                default=False,
                help_text="When enabled, the call is not linked from public pages. Only people with the secret link can access it.",
                verbose_name="Private (secret link only)",
            ),
        ),
        migrations.AddField(
            model_name="callforteammembers",
            name="cfm_secret",
            field=models.CharField(
                default=teamshifts.models.generate_cfm_secret,
                max_length=64,
                verbose_name="Secret token",
            ),
        ),
    ]
