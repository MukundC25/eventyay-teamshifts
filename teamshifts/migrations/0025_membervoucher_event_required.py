import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("teamshifts", "0024_membervoucher_keep_history"),
    ]

    operations = [
        migrations.AlterField(
            model_name="membervoucher",
            name="event",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="teamshifts_member_vouchers",
                to="base.event",
            ),
        ),
    ]
