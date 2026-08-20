from datetime import timedelta

import pytest
from django.utils.timezone import now
from django_scopes import scope
from eventyay.base.models import User

from teamshifts.forms import CertificateSettingsForm
from teamshifts.models import (
    ApplicationStatus,
    CertificateMatchMode,
    CertificateSettings,
    Shift,
    ShiftAssignment,
    ShiftLocation,
    TeamMemberApplication,
)
from teamshifts.services.certificates import completed_shift_count, member_qualifies


@pytest.fixture
def member(db):
    return User.objects.create_user(email="member@example.com", password="secret", fullname="Jane Member")


@pytest.fixture
def application(event, member):
    with scope(event=event):
        return TeamMemberApplication.objects.create(
            event=event,
            user=member,
            status=ApplicationStatus.ACCEPTED,
        )


@pytest.fixture
def settings_obj(event):
    with scope(event=event):
        return CertificateSettings.objects.create(event=event, require_arrived=True, require_min_shifts=False)


def _assign_shift(event, member, *, ended=False, name="Door"):
    with scope(event=event):
        location, _created = ShiftLocation.objects.get_or_create(event=event, name="Hall")
        shift = Shift.objects.create(
            event=event,
            name=name,
            location=location,
            start_time=now(),
            end_time=now() + timedelta(hours=2),
        )
        assignment = ShiftAssignment.objects.create(shift=shift, team_member=member)
        if ended:
            assignment.ended_at = now()
            assignment.save(update_fields=["ended_at"])
        return assignment


@pytest.mark.django_db
def test_arrived_only_qualifies(application, settings_obj):
    assert member_qualifies(application, settings_obj) is False
    application.arrived = True
    application.save(update_fields=["arrived"])
    assert member_qualifies(application, settings_obj) is True


@pytest.mark.django_db
def test_completed_shifts_require_ended_at(event, application, member, settings_obj):
    settings_obj.require_arrived = False
    settings_obj.require_min_shifts = True
    settings_obj.min_shifts = 1
    settings_obj.save()

    _assign_shift(event, member, ended=False, name="Door 1")
    assert completed_shift_count(application) == 0
    assert member_qualifies(application, settings_obj) is False

    _assign_shift(event, member, ended=True, name="Door 2")
    assert completed_shift_count(application) == 1
    assert member_qualifies(application, settings_obj) is True


@pytest.mark.django_db
def test_match_mode_any(event, application, member, settings_obj):
    settings_obj.require_arrived = True
    settings_obj.require_min_shifts = True
    settings_obj.min_shifts = 1
    settings_obj.match_mode = CertificateMatchMode.ANY
    settings_obj.save()

    application.arrived = True
    application.save(update_fields=["arrived"])
    assert member_qualifies(application, settings_obj) is True

    application.arrived = False
    application.save(update_fields=["arrived"])
    _assign_shift(event, member, ended=True)
    assert member_qualifies(application, settings_obj) is True


@pytest.mark.django_db
def test_match_mode_all_requires_both(event, application, member, settings_obj):
    settings_obj.require_arrived = True
    settings_obj.require_min_shifts = True
    settings_obj.min_shifts = 1
    settings_obj.match_mode = CertificateMatchMode.ALL
    settings_obj.save()

    application.arrived = True
    application.save(update_fields=["arrived"])
    assert member_qualifies(application, settings_obj) is False

    _assign_shift(event, member, ended=True)
    assert member_qualifies(application, settings_obj) is True


@pytest.mark.django_db
def test_form_requires_at_least_one_condition(settings_obj):
    form = CertificateSettingsForm(
        data={
            "min_shifts": "1",
            "match_mode": "all",
            "trigger": "auto",
        },
        instance=settings_obj,
    )
    assert form.is_valid() is False
