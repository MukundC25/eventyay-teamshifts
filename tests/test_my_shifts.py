import pytest
from django.urls import reverse
from django.utils.timezone import now, timedelta
from django_scopes import scopes_disabled
from eventyay.base.models import Event, Organizer, User

from teamshifts.models import (
    ApplicationStatus,
    CallForTeamMembers,
    Shift,
    ShiftAssignment,
    ShiftRoleAssignment,
    TeamMemberApplication,
    TeamRole,
)


@pytest.fixture
def user():
    return User.objects.create_user(email="volunteer@example.com", password="password")


@pytest.fixture
def organizer():
    return Organizer.objects.create(name="FOSSASIA", slug="fossasia")


@pytest.fixture
def event(organizer):
    return Event.objects.create(
        name="FOSSASIA Summit",
        slug="fossasia-summit",
        organizer=organizer,
        date_from=now(),
        date_to=now() + timedelta(days=2),
        plugins="teamshifts",
    )


@pytest.fixture
def cfm(event):
    return CallForTeamMembers.objects.create(
        event=event,
        title="Join our team",
        active=True,
        shift_schedule_published=True,
    )


@pytest.fixture
def accepted_application(event, user):
    return TeamMemberApplication.objects.create(
        event=event,
        user=user,
        status=ApplicationStatus.ACCEPTED,
    )


@pytest.fixture
def team_role(event):
    return TeamRole.objects.create(event=event, name="Registration")


@pytest.fixture
def shift(event):
    return Shift.objects.create(
        event=event,
        name="Morning Shift",
        start_time=now(),
        end_time=now() + timedelta(hours=3),
    )


@pytest.fixture
def shift_assignment(shift, user, team_role):
    ShiftRoleAssignment.objects.create(shift=shift, role=team_role, capacity=5)
    return ShiftAssignment.objects.create(
        shift=shift,
        team_member=user,
        role=team_role,
    )


@pytest.fixture
def global_url():
    return reverse("plugins:teamshifts:my_shifts_global")


@pytest.mark.django_db
def test_my_shifts_unauthenticated(client, global_url):
    response = client.get(global_url)
    assert response.status_code == 302
    assert "/login" in response.url or "login" in response.url.lower()


@pytest.mark.django_db
def test_my_shifts_no_shifts(client, user, global_url):
    client.force_login(user)
    response = client.get(global_url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_my_shifts_plugin_disabled(client, user, event, accepted_application, shift_assignment, global_url):
    event.plugins = ""
    event.save(update_fields=["plugins"])
    client.force_login(user)
    response = client.get(global_url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_my_shifts_with_assignment(client, user, event, cfm, accepted_application, shift_assignment, global_url):
    client.force_login(user)
    with scopes_disabled():
        response = client.get(global_url)
    assert response.status_code == 200
    assert b"Registration" in response.content
    assert b"Morning Shift" in response.content


@pytest.mark.django_db
def test_my_shifts_toggle_arrived(client, user, event, accepted_application, shift_assignment):
    client.force_login(user)
    url = reverse("plugins:teamshifts:my_shifts_toggle_arrived", kwargs={"event_id": event.pk})
    response = client.post(url, content_type="application/json")
    assert response.status_code == 200
    data = response.json()
    assert data["arrived"] is True

    response = client.post(url, content_type="application/json")
    assert response.json()["arrived"] is False
