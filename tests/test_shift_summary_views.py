import json
from unittest.mock import patch

import pytest
from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import now, timedelta
from django_scopes import scope
from eventyay.base.models import Team

from teamshifts.models import (
    ApplicationStatus,
    CallForTeamMembers,
    Shift,
    ShiftLocation,
    ShiftRoleAssignment,
    TeamMemberApplication,
    TeamRole,
    TeamShiftsEmailQueue,
)

JSON_HEADERS = {"HTTP_ACCEPT": "application/json", "HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


@pytest.fixture(autouse=True)
def site_url(settings):
    settings.SITE_URL = "https://testserver"


@pytest.fixture
def cfm(event):
    with scope(event=event):
        return CallForTeamMembers.objects.create(event=event, active=True, shift_schedule_published=True)


@pytest.fixture
def volunteer(django_user_model):
    return django_user_model.objects.create_user(email="volunteer@example.com", password="x")


@pytest.fixture
def application(event, cfm, volunteer):
    with scope(event=event):
        return TeamMemberApplication.objects.create(event=event, user=volunteer, status=ApplicationStatus.ACCEPTED)


@pytest.fixture
def organizer_user(event, user):
    with scope(event=event):
        team = Team.objects.create(organizer=event.organizer, name="Orga", can_change_event_settings=True, all_events=True)
        team.members.add(user)
    return user


@pytest.fixture
def team_role(event):
    with scope(event=event):
        return TeamRole.objects.create(event=event, name="Registration")


def _make_shift(event, role, hours_from_now):
    with scope(event=event):
        location, _created = ShiftLocation.objects.get_or_create(event=event, name="Hall A")
        shift = Shift.objects.create(
            event=event,
            name=f"Shift +{hours_from_now}h",
            location=location,
            start_time=now() + timedelta(hours=hours_from_now),
            end_time=now() + timedelta(hours=hours_from_now + 2),
        )
        ShiftRoleAssignment.objects.create(shift=shift, role=role, capacity=3)
    return shift


@pytest.fixture
def shift(event, team_role):
    return _make_shift(event, team_role, 24)


def _post(client, event, name, shift, payload):
    url = reverse(f"plugins:teamshifts:{name}", kwargs={"organizer": event.organizer.slug, "event": event.slug, "pk": shift.pk})
    with TestCase.captureOnCommitCallbacks(execute=True):
        return client.post(url, data=json.dumps(payload), content_type="application/json", **JSON_HEADERS)


def _claim(client, event, shift, role, **extra):
    return _post(client, event, "public_shift_claim", shift, {"role_id": role.pk, **extra})


def _drop(client, event, shift, role, **extra):
    return _post(client, event, "public_shift_withdraw", shift, {"role_id": role.pk, **extra})


def _summary_count(event, user):
    with scope(event=event):
        return TeamShiftsEmailQueue.objects.filter(is_shift_summary=True, recipients__user=user).count()


@pytest.mark.django_db
def test_claim_and_drop_share_one_daily_summary(client, event, application, volunteer, shift, team_role):
    client.force_login(volunteer)
    assert _claim(client, event, shift, team_role).status_code == 200
    assert _drop(client, event, shift, team_role).status_code == 200
    assert _claim(client, event, shift, team_role).status_code == 200
    assert _summary_count(event, volunteer) == 1


@pytest.mark.django_db
def test_summary_is_queued_even_when_volunteer_opted_out_of_action_emails(client, event, application, volunteer, shift, team_role):
    client.force_login(volunteer)
    with patch("teamshifts.views.queue_shift_notification_email") as mock_queue:
        _claim(client, event, shift, team_role, send_email=False)
    mock_queue.assert_not_called()
    assert _summary_count(event, volunteer) == 1


@pytest.mark.django_db
def test_organizer_assign_and_remove_queue_summary(client, event, application, volunteer, organizer_user, shift, team_role):
    client.force_login(organizer_user)
    base = reverse("plugins:teamshifts:api_assignments", kwargs={"organizer": event.organizer.slug, "event": event.slug})
    with TestCase.captureOnCommitCallbacks(execute=True):
        resp = client.post(base, data=json.dumps({"shift_id": shift.pk, "user_id": volunteer.pk, "role_id": team_role.pk}), content_type="application/json")
    assert resp.status_code == 200
    assert _summary_count(event, volunteer) == 1
    with scope(event=event):
        TeamShiftsEmailQueue.objects.filter(is_shift_summary=True).update(sent_at=now())
    with TestCase.captureOnCommitCallbacks(execute=True):
        resp = client.delete(f"{base}?shift_id={shift.pk}&user_id={volunteer.pk}&role_id={team_role.pk}")
    assert resp.status_code == 200
    assert _summary_count(event, volunteer) == 2
