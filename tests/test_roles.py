import pytest
from django.urls import reverse
from django_scopes import scope
from eventyay.base.models import Team

from teamshifts.forms import TeamRoleForm
from teamshifts.models import TeamRole


@pytest.mark.django_db
def test_teamrole_is_restricted_default(event):
    with scope(event=event):
        role = TeamRole.objects.create(event=event, name="Open Role")
        assert role.is_restricted is False


@pytest.mark.django_db
def test_teamrole_form_validates_is_restricted(event):
    with scope(event=event):
        form = TeamRoleForm(data={"name": "Manager", "is_restricted": True})
        form.instance.event = event
        assert form.is_valid()
        role = form.save()
        assert role.is_restricted is True


@pytest.mark.django_db
def test_teamrole_form_validates_open_role(event):
    with scope(event=event):
        form = TeamRoleForm(data={"name": "Helper"})
        form.instance.event = event
        assert form.is_valid()
        role = form.save()
        assert role.is_restricted is False


@pytest.mark.django_db
def test_roles_list_renders_tiptap_html_description(client, event, user, settings):
    settings.SITE_URL = "https://testserver"
    with scope(event=event):
        team = Team.objects.create(
            organizer=event.organizer,
            name="Orga Team",
            can_change_event_settings=True,
            all_events=True,
        )
        team.members.add(user)
        TeamRole.objects.create(
            event=event,
            name="Registration",
            description="<p>Assist attendees with <strong>check-in</strong>.</p>",
        )
    client.force_login(user)

    url = reverse("plugins:teamshifts:roles", kwargs={"organizer": event.organizer.slug, "event": event.slug})
    response = client.get(url)
    assert response.status_code == 200
    assert b"&lt;p&gt;" not in response.content
    assert b"<strong>check-in</strong>" in response.content
