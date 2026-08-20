from unittest.mock import patch

import pytest
from django.urls import reverse
from django_scopes import scope
from eventyay.base.models import Team, User

from teamshifts.forms import TeamMemberApplicationForm
from teamshifts.models import ApplicationStatus, CallForTeamMembers, TeamMemberApplication
from teamshifts.services.members import AlreadyMemberError, add_member_from_organizer


@pytest.fixture
def call_for_team_members(event):
    with scope(event=event):
        return CallForTeamMembers.objects.create(event=event, active=True)


@pytest.fixture
def orga_user(event, user):
    with scope(event=event):
        team = Team.objects.create(
            organizer=event.organizer,
            name="Test Team",
            can_change_event_settings=True,
            all_events=True,
        )
        team.members.add(user)
    return user


@pytest.mark.django_db
def test_organizer_add_member_form_email_is_editable(event, call_for_team_members):
    form = TeamMemberApplicationForm(event=event, cfm=call_for_team_members, organizer_mode=True)
    assert "email" in form.fields
    assert form.fields["email"].widget.attrs.get("readonly") is None
    assert form.fields["email"].required is True


@pytest.mark.django_db
def test_add_member_creates_accepted_application(event, call_for_team_members):
    form = TeamMemberApplicationForm(
        data={
            "full_name": "Jane Member",
            "email": "jane.member@example.com",
            "phone": "+1 555 0100",
            "availability_notes": "Weekends",
        },
        event=event,
        cfm=call_for_team_members,
        organizer_mode=True,
    )
    assert form.is_valid(), form.errors
    application = add_member_from_organizer(event=event, form=form)
    assert application.status == ApplicationStatus.ACCEPTED
    assert application.user.email == "jane.member@example.com"
    assert application.user.fullname == "Jane Member"
    assert application.phone == "+1 555 0100"


@pytest.mark.django_db
def test_add_member_rejects_existing_accepted(event, call_for_team_members, django_user_model):
    member = django_user_model.objects.create_user(email="existing@example.com", password="x", fullname="Existing")
    with scope(event=event):
        TeamMemberApplication.objects.create(event=event, user=member, status=ApplicationStatus.ACCEPTED)

    form = TeamMemberApplicationForm(
        data={"full_name": "Existing", "email": "existing@example.com"},
        event=event,
        cfm=call_for_team_members,
        organizer_mode=True,
    )
    assert form.is_valid(), form.errors
    with pytest.raises(AlreadyMemberError):
        add_member_from_organizer(event=event, form=form)


@pytest.mark.django_db
def test_add_member_accepts_pending_application(event, call_for_team_members, django_user_model):
    member = django_user_model.objects.create_user(email="pending@example.com", password="x", fullname="Pending")
    with scope(event=event):
        application = TeamMemberApplication.objects.create(
            event=event,
            user=member,
            status=ApplicationStatus.PENDING,
            phone="",
        )

    form = TeamMemberApplicationForm(
        data={"full_name": "Pending Updated", "email": "pending@example.com", "phone": "123"},
        event=event,
        cfm=call_for_team_members,
        organizer_mode=True,
    )
    assert form.is_valid(), form.errors
    updated = add_member_from_organizer(event=event, form=form)
    assert updated.pk == application.pk
    assert updated.status == ApplicationStatus.ACCEPTED
    assert updated.phone == "123"


@pytest.mark.django_db
@patch("teamshifts.views.queue_lifecycle_email")
def test_member_add_view_creates_member(mock_queue, client, event, call_for_team_members, orga_user, settings):
    settings.SITE_URL = "https://testserver"
    client.force_login(orga_user)
    url = reverse("plugins:teamshifts:member_add", kwargs={"organizer": event.organizer.slug, "event": event.slug})
    response = client.post(
        url,
        {
            "full_name": "Org Added",
            "email": "org.added@example.com",
        },
    )
    assert response.status_code == 302
    with scope(event=event):
        application = TeamMemberApplication.objects.get(event=event, user__email="org.added@example.com")
        assert application.status == ApplicationStatus.ACCEPTED
    assert User.objects.filter(email="org.added@example.com").exists()
