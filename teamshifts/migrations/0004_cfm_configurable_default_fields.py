from django.db import migrations, models


def seed_field_order(apps, schema_editor):
    CallForTeamMembers = apps.get_model("teamshifts", "CallForTeamMembers")
    TeamApplicationQuestion = apps.get_model("teamshifts", "TeamApplicationQuestion")

    builtin_keys = ["full_name", "email", "phone", "role", "availability"]

    for cfm in CallForTeamMembers.objects.all():
        custom_pks = list(TeamApplicationQuestion.objects.filter(event_id=cfm.event_id).order_by("position", "pk").values_list("pk", flat=True))
        cfm.field_order = builtin_keys + custom_pks
        cfm.save(update_fields=["field_order"])


class Migration(migrations.Migration):
    dependencies = [
        ("teamshifts", "0003_callforteammembers_show_on_menu"),
    ]

    operations = [
        migrations.AddField(
            model_name="callforteammembers",
            name="ask_full_name",
            field=models.CharField(
                choices=[("do_not_ask", "Do not ask"), ("optional", "Optional"), ("required", "Required")],
                default="optional",
                max_length=20,
                verbose_name="Full name",
            ),
        ),
        migrations.AddField(
            model_name="callforteammembers",
            name="ask_email",
            field=models.CharField(
                choices=[("do_not_ask", "Do not ask"), ("optional", "Optional"), ("required", "Required")],
                default="required",
                max_length=20,
                verbose_name="Email address",
            ),
        ),
        migrations.AddField(
            model_name="callforteammembers",
            name="ask_phone",
            field=models.CharField(
                choices=[("do_not_ask", "Do not ask"), ("optional", "Optional"), ("required", "Required")],
                default="optional",
                max_length=20,
                verbose_name="Phone / Mobile",
            ),
        ),
        migrations.AddField(
            model_name="callforteammembers",
            name="ask_role",
            field=models.CharField(
                choices=[("do_not_ask", "Do not ask"), ("optional", "Optional"), ("required", "Required")],
                default="required",
                max_length=20,
                verbose_name="Role",
            ),
        ),
        migrations.AddField(
            model_name="callforteammembers",
            name="ask_availability",
            field=models.CharField(
                choices=[("do_not_ask", "Do not ask"), ("optional", "Optional"), ("required", "Required")],
                default="optional",
                max_length=20,
                verbose_name="Availability notes",
            ),
        ),
        migrations.AddField(
            model_name="callforteammembers",
            name="field_order",
            field=models.JSONField(default=list, verbose_name="Field order"),
        ),
        migrations.RunPython(seed_field_order, migrations.RunPython.noop),
    ]
