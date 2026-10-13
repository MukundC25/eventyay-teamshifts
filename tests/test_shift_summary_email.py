import datetime

import pytest
from django.utils.timezone import now
from django_scopes import scope

from teamshifts.models import (
    CallForTeamMembers,
    EmailTemplateRoles,
    Shift,
    ShiftAssignment,
    TeamRole,
    TeamShiftsEmailQueue,
)
from teamshifts.services.email import SHIFT_SUMMARY_SEND_TIME, next_shift_summary_time, queue_shift_summary_email
from teamshifts.services.shift_summary import build_shift_summary, build_shift_summary_sample


@pytest.fixture
def volunteer(django_user_model):
    return django_user_model.objects.create_user(email="vol@example.com", password="x", fullname="Vol", locale="en")


@pytest.fixture
def cfm(event):
    with scope(event=event):
        return CallForTeamMembers.objects.create(event=event, shift_schedule_published=True)


@pytest.fixture
def role(event):
    with scope(event=event):
        return TeamRole.objects.create(event=event, name="Greeter")


def _shift(event, name, start):
    with scope(event=event):
        return Shift.objects.create(event=event, name=name, start_time=start, end_time=start + datetime.timedelta(hours=2))


def _summary_queues(event):
    with scope(event=event):
        return list(TeamShiftsEmailQueue.objects.filter(is_shift_summary=True).order_by("pk"))


@pytest.mark.django_db
def test_first_change_queues_summary_for_next_send_time(event, cfm, volunteer):
    queue_shift_summary_email(event, volunteer)
    (queue,) = _summary_queues(event)
    local = queue.send_after.astimezone(event.tz)
    assert local.time() == SHIFT_SUMMARY_SEND_TIME
    assert queue.send_after > now()
    assert queue.send_after - now() <= datetime.timedelta(hours=24, minutes=1)


@pytest.mark.django_db
def test_changes_on_the_same_day_share_one_summary(event, cfm, volunteer):
    first = queue_shift_summary_email(event, volunteer)
    second = queue_shift_summary_email(event, volunteer)
    assert first.pk == second.pk
    assert len(_summary_queues(event)) == 1
    assert _summary_queues(event)[0].send_after == first.send_after


@pytest.mark.django_db
def test_new_summary_after_previous_was_sent(event, cfm, volunteer):
    queue_shift_summary_email(event, volunteer)
    with scope(event=event):
        TeamShiftsEmailQueue.objects.update(sent_at=now())
    queue_shift_summary_email(event, volunteer)
    assert len(_summary_queues(event)) == 2


@pytest.mark.django_db
def test_other_volunteers_are_not_merged(event, cfm, volunteer, django_user_model):
    other = django_user_model.objects.create_user(email="o@example.com", password="x", fullname="O", locale="en")
    queue_shift_summary_email(event, volunteer)
    queue_shift_summary_email(event, other)
    assert len(_summary_queues(event)) == 2


@pytest.mark.django_db
def test_nothing_is_queued_without_a_change(event, cfm, volunteer):
    assert _summary_queues(event) == []


def test_send_time_is_today_before_cutoff_and_tomorrow_after(event):
    tz = event.tz
    morning = datetime.datetime(2026, 3, 10, 9, 30, tzinfo=tz)
    evening = datetime.datetime(2026, 3, 10, 21, 0, tzinfo=tz)
    exactly = datetime.datetime(2026, 3, 10, 20, 0, tzinfo=tz)
    assert next_shift_summary_time(event, morning) == datetime.datetime(2026, 3, 10, 20, 0, tzinfo=tz)
    assert next_shift_summary_time(event, evening) == datetime.datetime(2026, 3, 11, 20, 0, tzinfo=tz)
    assert next_shift_summary_time(event, exactly) == datetime.datetime(2026, 3, 11, 20, 0, tzinfo=tz)


@pytest.mark.django_db
def test_skipped_when_schedule_unpublished(event, cfm, volunteer):
    with scope(event=event):
        cfm.shift_schedule_published = False
        cfm.save()
    assert queue_shift_summary_email(event, volunteer) is None
    assert _summary_queues(event) == []


@pytest.mark.django_db
def test_summary_lists_all_current_shifts_sorted(event, cfm, volunteer, role):
    base = now() + datetime.timedelta(days=3)
    late = _shift(event, "Teardown", base + datetime.timedelta(days=1))
    early = _shift(event, "Setup", base)
    with scope(event=event):
        ShiftAssignment.objects.create(shift=late, team_member=volunteer, role=role)
        ShiftAssignment.objects.create(shift=early, team_member=volunteer, role=role)
    text = build_shift_summary(event, volunteer)
    assert text.index("Setup") < text.index("Teardown")
    assert "Role: Greeter" in text


@pytest.mark.django_db
def test_summary_without_shifts_links_to_schedule(event, cfm, volunteer):
    text = build_shift_summary(event, volunteer)
    assert "no shifts" in text
    assert "/teamshifts/shifts/" in text


@pytest.mark.django_db
def test_summary_template_is_editable_role(event, cfm):
    with scope(event=event):
        template = cfm.get_mail_template(EmailTemplateRoles.SHIFT_SUMMARY)
    assert "{shift_summary}" in str(template.body)
    assert "{my_shifts_url}" in str(template.body)
    assert "{shift_schedule_url}" in str(template.body)
    assert str(template.subject) == "Your shifts for {event_name}"


@pytest.mark.django_db
def test_summary_sample_uses_the_events_own_shifts(event, cfm):
    _shift(event, "Registration Desk", now() + datetime.timedelta(days=3))
    assert "Registration Desk" in build_shift_summary_sample(event)


@pytest.mark.django_db
def test_summary_sample_without_shifts_falls_back(event, cfm):
    assert "no shifts" in build_shift_summary_sample(event)
