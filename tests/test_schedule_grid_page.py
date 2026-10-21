import pytest
from django.urls import reverse
from django_scopes import scope
from eventyay.base.models import Team


@pytest.fixture
def orga_client(client, event, user, settings):
    settings.SITE_URL = "https://testserver"
    with scope(event=event):
        team = Team.objects.create(
            organizer=event.organizer,
            name="Orga Team",
            can_change_event_settings=True,
            all_events=True,
        )
        team.members.add(user)
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_schedule_grid_provides_the_shared_editor_host_contract(orga_client, event, settings):
    settings.VITE_DEV_MODE = True
    url = reverse("plugins:teamshifts:schedule_grid", kwargs={"organizer": event.organizer.slug, "event": event.slug})
    response = orga_client.get(url)

    assert response.status_code == 200
    content = response.content.decode()
    for marker in (
        'class="schedule-editor-container"',
        'id="schedule-action-wrapper"',
        'id="schedule-timezone-mount"',
        'id="schedule-fullscreen-mount"',
        'id="app"',
    ):
        assert marker in content, marker
    assert content.index('class="schedule-editor-container"') < content.index('id="app"')
