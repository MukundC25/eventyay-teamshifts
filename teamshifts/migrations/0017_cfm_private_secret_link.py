from django.db import migrations, models

import teamshifts.models


def assign_unique_cfm_secrets(apps, schema_editor):
    CallForTeamMembers = apps.get_model("teamshifts", "CallForTeamMembers")
    for cfm in CallForTeamMembers.objects.all().iterator():
        cfm.cfm_secret = teamshifts.models.generate_cfm_secret()
        cfm.save(update_fields=["cfm_secret"])


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
        # Add nullable first so existing rows are not backfilled with one shared secret.
        migrations.AddField(
            model_name="callforteammembers",
            name="cfm_secret",
            field=models.CharField(
                max_length=64,
                null=True,
                verbose_name="Secret token",
            ),
        ),
        migrations.RunPython(assign_unique_cfm_secrets, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="callforteammembers",
            name="cfm_secret",
            field=models.CharField(
                default=teamshifts.models.generate_cfm_secret,
                max_length=64,
                verbose_name="Secret token",
            ),
        ),
    ]
