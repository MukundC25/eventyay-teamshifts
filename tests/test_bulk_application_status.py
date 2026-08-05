from unittest.mock import patch

import pytest
from django.test import TestCase
from django.urls import reverse
from django_scopes import scope
from eventyay.base.models import Team

from teamshifts.models import ApplicationStatus, CallForTeamMembers, TeamMemberApplication, TeamRole


@pytest.fixture
def call_for_team_members(event):
    with scope(event=event):
        return CallForTeamMembers.objects.create(
            event=event,
            active=True,
        )


@pytest.fixture
def team_role(event):
    with scope(event=event):
        return TeamRole.objects.create(event=event, name="Volunteer")


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


def _make_applicant(django_user_model, email):
    return django_user_model.objects.create_user(email=email, password="x")


@pytest.fixture
def pending_applications(event, team_role, django_user_model):
    with scope(event=event):
        apps = []
        for i in range(3):
            applicant = _make_applicant(django_user_model, f"applicant{i}@example.com")
            apps.append(
                TeamMemberApplication.objects.create(
                    event=event,
                    user=applicant,
                    status=ApplicationStatus.PENDING,
                )
            )
        return apps


@pytest.mark.django_db
@patch("teamshifts.views.queue_lifecycle_email")
def test_bulk_accept_updates_all_selected_pending_applications(mock_queue, client, event, team_role, pending_applications, orga_user, settings):
    settings.SITE_URL = "https://testserver"
    client.force_login(orga_user)

    url = reverse("plugins:teamshifts:application_bulk_action", kwargs={"organizer": event.organizer.slug, "event": event.slug})
    app_ids = [str(a.pk) for a in pending_applications]

    tc = TestCase()
    with tc.captureOnCommitCallbacks(execute=True):
        response = client.post(url, {"action": "accept", "application_ids": app_ids})

    expected_url = reverse("plugins:teamshifts:applications", kwargs={"organizer": event.organizer.slug, "event": event.slug})
    assert response.status_code == 302
    assert response.url == expected_url

    with scope(event=event):
        for app in pending_applications:
            app.refresh_from_db()
            assert app.status == ApplicationStatus.ACCEPTED
    assert mock_queue.call_count == len(pending_applications)


@pytest.mark.django_db
@patch("teamshifts.views.queue_lifecycle_email")
def test_bulk_reject_updates_all_selected_pending_applications(mock_queue, client, event, team_role, pending_applications, orga_user, settings):
    settings.SITE_URL = "https://testserver"
    client.force_login(orga_user)

    url = reverse("plugins:teamshifts:application_bulk_action", kwargs={"organizer": event.organizer.slug, "event": event.slug})
    app_ids = [str(a.pk) for a in pending_applications]

    tc = TestCase()
    with tc.captureOnCommitCallbacks(execute=True):
        client.post(url, {"action": "reject", "application_ids": app_ids})

    with scope(event=event):
        for app in pending_applications:
            app.refresh_from_db()
            assert app.status == ApplicationStatus.REJECTED
    assert mock_queue.call_count == len(pending_applications)


@pytest.mark.django_db
@patch("teamshifts.views.queue_lifecycle_email")
def test_bulk_action_allows_changing_already_decided_applications(mock_queue, client, event, team_role, pending_applications, orga_user, settings):
    """Bulk actions must still work on applications that were already accepted/rejected,
    so decisions can be revisited later (not just while pending)."""
    settings.SITE_URL = "https://testserver"
    client.force_login(orga_user)

    with scope(event=event):
        pending_applications[0].status = ApplicationStatus.REJECTED
        pending_applications[0].save(update_fields=["status"])

    url = reverse("plugins:teamshifts:application_bulk_action", kwargs={"organizer": event.organizer.slug, "event": event.slug})
    app_ids = [str(a.pk) for a in pending_applications]

    tc = TestCase()
    with tc.captureOnCommitCallbacks(execute=True):
        response = client.post(url, {"action": "accept", "application_ids": app_ids})

    assert response.status_code == 302
    with scope(event=event):
        for app in pending_applications:
            app.refresh_from_db()
            assert app.status == ApplicationStatus.ACCEPTED
    assert mock_queue.call_count == len(pending_applications)


@pytest.mark.django_db
@patch("teamshifts.views.queue_lifecycle_email")
def test_bulk_action_skips_applications_already_in_target_status(mock_queue, client, event, team_role, pending_applications, orga_user, settings):
    settings.SITE_URL = "https://testserver"
    client.force_login(orga_user)

    with scope(event=event):
        pending_applications[0].status = ApplicationStatus.ACCEPTED
        pending_applications[0].save(update_fields=["status"])

    url = reverse("plugins:teamshifts:application_bulk_action", kwargs={"organizer": event.organizer.slug, "event": event.slug})
    app_ids = [str(a.pk) for a in pending_applications]

    tc = TestCase()
    with tc.captureOnCommitCallbacks(execute=True):
        client.post(url, {"action": "accept", "application_ids": app_ids})

    assert mock_queue.call_count == len(pending_applications) - 1


@pytest.mark.django_db
def test_bulk_action_requires_selection(client, event, team_role, orga_user, settings):
    settings.SITE_URL = "https://testserver"
    client.force_login(orga_user)

    url = reverse("plugins:teamshifts:application_bulk_action", kwargs={"organizer": event.organizer.slug, "event": event.slug})
    response = client.post(url, {"action": "accept"})

    assert response.status_code == 302


@pytest.mark.django_db
def test_bulk_action_rejects_invalid_action(client, event, team_role, pending_applications, orga_user, settings):
    settings.SITE_URL = "https://testserver"
    client.force_login(orga_user)

    url = reverse("plugins:teamshifts:application_bulk_action", kwargs={"organizer": event.organizer.slug, "event": event.slug})
    app_ids = [str(a.pk) for a in pending_applications]
    response = client.post(url, {"action": "delete", "application_ids": app_ids})

    assert response.status_code == 400
