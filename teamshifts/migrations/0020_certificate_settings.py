import django.db.models.deletion
from django.db import migrations, models

import teamshifts.models


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0052_admission_validity_fields"),
        ("teamshifts", "0019_member_added_by_organizer"),
    ]

    operations = [
        migrations.AddField(
            model_name="shiftassignment",
            name="ended_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Set when the member checks out on My Shifts. A shift counts as completed once this is set.",
                null=True,
                verbose_name="Ended At",
            ),
        ),
        migrations.AddField(
            model_name="shiftassignment",
            name="started_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Set when the member checks in on My Shifts.",
                null=True,
                verbose_name="Started At",
            ),
        ),
        migrations.CreateModel(
            name="CertificateSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("require_arrived", models.BooleanField(default=True, verbose_name="Marked as arrived at the event")),
                ("require_min_shifts", models.BooleanField(default=False, verbose_name="Completed at least a minimum number of shifts")),
                ("min_shifts", models.PositiveIntegerField(default=1, verbose_name="Minimum completed shifts")),
                (
                    "match_mode",
                    models.CharField(
                        choices=[("all", "Require all selected conditions"), ("any", "Require any one selected condition")],
                        default="all",
                        max_length=8,
                        verbose_name="How conditions combine",
                    ),
                ),
                (
                    "trigger",
                    models.CharField(
                        choices=[("auto", "Automatically"), ("manual", "Manually")],
                        default="auto",
                        max_length=8,
                        verbose_name="Certificate generation trigger",
                    ),
                ),
                ("layout", models.TextField(blank=True)),
                ("background", models.FileField(blank=True, max_length=255, null=True, upload_to=teamshifts.models.certificate_background_name)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "event",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="teamshifts_certificate_settings",
                        to="base.event",
                    ),
                ),
            ],
            options={
                "verbose_name": "Certificate settings",
                "verbose_name_plural": "Certificate settings",
            },
        ),
        migrations.CreateModel(
            name="MemberCertificate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(blank=True, max_length=255, null=True, upload_to=teamshifts.models.member_certificate_name)),
                ("generated_at", models.DateTimeField(auto_now=True)),
                ("downloaded_at", models.DateTimeField(blank=True, null=True)),
                (
                    "application",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="certificate",
                        to="teamshifts.teammemberapplication",
                    ),
                ),
            ],
            options={
                "verbose_name": "Member certificate",
                "verbose_name_plural": "Member certificates",
            },
        ),
    ]
