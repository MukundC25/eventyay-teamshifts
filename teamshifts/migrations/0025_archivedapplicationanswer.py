import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0001_initial"),
        ("teamshifts", "0024_shift_notification_queue_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="ArchivedApplicationAnswer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question_id", models.PositiveIntegerField()),
                ("question_text", models.TextField()),
                (
                    "variant",
                    models.CharField(
                        choices=[
                            ("string", "Text (one line)"),
                            ("text", "Multi-line text"),
                            ("number", "Number"),
                            ("boolean", "Confirmation (checkbox)"),
                            ("date", "Date"),
                            ("datetime", "Date and time"),
                            ("url", "URL"),
                            ("choices", "Radio button (choose one option)"),
                            ("choices_dropdown", "Dropdown (choose one option)"),
                            ("multiple_choice", "Checkbox (choose one or more options)"),
                            ("country", "Country"),
                            ("phone", "Phone number"),
                        ],
                        default="string",
                        max_length=20,
                    ),
                ),
                ("answer", models.TextField(blank=True)),
                (
                    "application",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="archived_answers", to="teamshifts.teammemberapplication"),
                ),
                (
                    "event",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="archived_application_answers", to="base.event"),
                ),
            ],
            options={
                "verbose_name": "Archived Application Answer",
                "verbose_name_plural": "Archived Application Answers",
                "ordering": ["question_id"],
                "unique_together": {("application", "question_id")},
            },
        ),
    ]
