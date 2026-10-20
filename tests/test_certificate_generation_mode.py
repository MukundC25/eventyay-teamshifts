from datetime import timedelta
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup
from django.urls import reverse
from django.utils.timezone import now
from django_scopes import scope
from eventyay.base.models import Event, Team, User

from teamshifts.forms import CertificateSettingsForm
from teamshifts.models import (
    ApplicationStatus,
    CallForTeamMembers,
    CertificateSettings,
    CertificateStatus,
    CertificateTrigger,
    MemberCertificate,
    TeamMemberApplication,
)
from teamshifts.services.certificates import (
    event_has_ended,
    events_awaiting_certificates,
    generate_certificate,
    generate_pending_certificates,
    get_certificate_settings,
    issue_event_end_certificates_task,
    maybe_auto_issue_certificate,
    member_qualifies,
    send_certificates,
)


@pytest.fixture(autouse=True)
def active_scope(event):
    with scope(event=event, organizer=event.organizer):
        yield


@pytest.fixture(autouse=True)
def sent_emails():
    with (
        patch("teamshifts.services.certificates.transaction") as transaction,
        patch("teamshifts.services.certificates._send_certificate_email") as send_email,
    ):
        transaction.on_commit.side_effect = lambda callback: callback()
        yield send_email


@pytest.fixture
def orga_client(client, event, user, settings):
    settings.SITE_URL = "https://testserver"
    team = Team.objects.create(organizer=event.organizer, name="Orga Team", can_change_event_settings=True, all_events=True)
    team.members.add(user)
    client.force_login(user)
    return client


def _member(event, name="member", arrived=True):
    user = User.objects.create_user(email=f"{name}@example.com", password="secret", fullname=name)
    CallForTeamMembers.objects.get_or_create(event=event)
    return TeamMemberApplication.objects.create(event=event, user=user, status=ApplicationStatus.ACCEPTED, arrived=arrived)


@pytest.fixture
def application(event):
    return _member(event)


def _configure(event, ended=None, **fields):
    settings = get_certificate_settings(event)
    for key, value in fields.items():
        setattr(settings, key, value)
    settings.save()
    if ended is not None:
        days = -5 if ended else 0
        event.date_from = now() + timedelta(days=days - 1)
        event.date_to = now() + timedelta(days=days + 1)
        event.save(update_fields=["date_from", "date_to"])
    return settings


def _url(event, name, **kwargs):
    return reverse(f"plugins:teamshifts:{name}", kwargs={"organizer": event.organizer.slug, "event": event.slug, **kwargs})


def _fail_for(application):
    real_generate = generate_certificate

    def generate(target, *args, **kwargs):
        if target.pk == application.pk:
            raise OSError("storage unavailable")
        return real_generate(target, *args, **kwargs)

    return patch("teamshifts.services.certificates.generate_certificate", side_effect=generate)


@pytest.mark.django_db
def test_new_and_untouched_events_stay_manual(event, application):
    settings = get_certificate_settings(event)
    assert settings.trigger == CertificateTrigger.MANUAL
    assert settings.require_arrived is True
    assert settings.require_after_event_end is False
    assert maybe_auto_issue_certificate(application) is None
    assert not MemberCertificate.objects.filter(application=application).exists()


@pytest.mark.django_db
def test_enabling_automatic_generation_only_covers_later_qualifiers(event, application):
    form = CertificateSettingsForm(
        data={"require_arrived": "on", "min_shifts": "1", "match_mode": "all", "generate_automatically": "on"},
        instance=get_certificate_settings(event),
    )
    assert form.is_valid()
    form.save()
    assert CertificateSettings.objects.get(event=event).trigger == CertificateTrigger.AUTO
    assert not MemberCertificate.objects.filter(application=application).exists()

    assert maybe_auto_issue_certificate(application) is not None


@pytest.mark.django_db
def test_after_event_end_gate_uses_last_day_in_event_timezone(event, application):
    settings = _configure(event, ended=False, require_after_event_end=True)
    assert event_has_ended(event) is False
    assert member_qualifies(application, settings) is False

    _configure(event, ended=True)
    assert event_has_ended(event) is True
    assert member_qualifies(application, settings) is True

    Event.objects.filter(pk=event.pk).update(timezone="Pacific/Auckland")
    event = Event.objects.get(pk=event.pk)
    local_now = now().astimezone(event.tz)
    event.date_to = local_now.replace(hour=23, minute=59)
    event.date_from = event.date_to - timedelta(days=1)
    event.save(update_fields=["date_from", "date_to"])
    assert event_has_ended(event) is False


@pytest.mark.django_db
def test_after_event_end_alone_qualifies_every_accepted_member(event, orga_client):
    absent = _member(event, "absent", arrived=False)
    settings = _configure(event, ended=False, require_arrived=False, require_after_event_end=True)
    assert member_qualifies(absent, settings) is False

    _configure(event, ended=True)
    assert member_qualifies(absent, settings) is True

    form = CertificateSettingsForm(data={"require_after_event_end": "on", "min_shifts": "1", "match_mode": "all"}, instance=settings)
    assert form.is_valid()

    response = orga_client.post(_url(event, "certificates"), {"min_shifts": "1", "match_mode": "all"})
    fieldsets = BeautifulSoup(response.content, "html.parser").find_all("fieldset")
    conditions = next(fieldset for fieldset in fieldsets if "Qualification conditions" in fieldset.legend.get_text())
    assert "Select at least one qualification condition." in conditions.get_text()
    assert "Select at least one qualification condition." not in fieldsets[0].get_text()


@pytest.mark.django_db
def test_existing_certificate_is_not_revoked_before_event_end(event, application):
    generate_certificate(application)
    _configure(event, ended=False, trigger=CertificateTrigger.AUTO, require_after_event_end=True)

    assert maybe_auto_issue_certificate(application) is None
    assert MemberCertificate.objects.filter(application=application).exists()


@pytest.mark.django_db
def test_scheduled_issuing_after_event_end(event, application, sent_emails):
    _configure(
        event,
        ended=False,
        trigger=CertificateTrigger.AUTO,
        require_after_event_end=True,
        after_event_end_issuing_since=now() - timedelta(days=30),
    )
    assert generate_pending_certificates(event) == 0

    _configure(event, ended=True)
    assert event.pk in events_awaiting_certificates()
    issue_event_end_certificates_task(event.pk)
    assert MemberCertificate.objects.filter(application=application, notified_at__isnull=False).exists()
    assert event.pk not in events_awaiting_certificates()

    MemberCertificate.objects.filter(application=application).update(notified_at=None)
    assert event.pk in events_awaiting_certificates()
    assert generate_pending_certificates(event) == 1
    assert sent_emails.call_count == 2

    _configure(event, trigger=CertificateTrigger.MANUAL)
    MemberCertificate.objects.filter(application=application).update(notified_at=None)
    assert event.pk not in events_awaiting_certificates()


@pytest.mark.django_db
@pytest.mark.parametrize(("ended_before_enabling", "issued"), [(False, 1), (True, 0)])
def test_scheduled_issuing_is_not_retroactive(event, application, ended_before_enabling, issued):
    settings = _configure(event, ended=ended_before_enabling)
    form = CertificateSettingsForm(
        data={"require_arrived": "on", "require_after_event_end": "on", "min_shifts": "1", "match_mode": "all", "generate_automatically": "on"},
        instance=settings,
    )
    assert form.is_valid()
    settings = form.save()
    assert settings.after_event_end_issuing_since is not None
    if not ended_before_enabling:
        settings.after_event_end_issuing_since = now() - timedelta(days=30)
        settings.save(update_fields=["after_event_end_issuing_since"])
        _configure(event, ended=True)

    assert (event.pk in events_awaiting_certificates()) is bool(issued)
    assert generate_pending_certificates(event) == issued

    form = CertificateSettingsForm(data={"require_arrived": "on", "min_shifts": "1", "match_mode": "all"}, instance=settings)
    assert form.is_valid()
    assert form.save().after_event_end_issuing_since is None


@pytest.mark.django_db
def test_send_certificates_skips_non_qualifying_and_resends(event, application, sent_emails):
    not_arrived = _member(event, "absent", arrived=False)

    result = send_certificates(event, [application, not_arrived])
    send_certificates(event, [application])

    assert result == {"sent": 1, "not_qualified": 1, "no_email": 0, "failed": 0}
    assert not MemberCertificate.objects.filter(application=not_arrived).exists()
    assert sent_emails.call_count == 2


@pytest.mark.django_db
@pytest.mark.parametrize("bulk_action", ["send", "scheduled"])
def test_bulk_actions_continue_after_a_failure(event, application, bulk_action):
    other = _member(event, "other")
    _configure(
        event,
        ended=True,
        trigger=CertificateTrigger.AUTO,
        require_after_event_end=True,
        after_event_end_issuing_since=now() - timedelta(days=30),
    )

    with _fail_for(application):
        if bulk_action == "send":
            assert send_certificates(event, [application, other]) == {"sent": 1, "not_qualified": 0, "no_email": 0, "failed": 1}
        else:
            assert generate_pending_certificates(event) == 1

    assert not MemberCertificate.objects.filter(application=application).exists()
    assert MemberCertificate.objects.filter(application=other).exists()


@pytest.mark.django_db
def test_regenerating_saves_new_file_before_removing_old_one(application):
    old_name = generate_certificate(application).file.name
    certificate = generate_certificate(application, resend=True)

    assert certificate.file.name != old_name
    assert not certificate.file.storage.exists(old_name)
    assert certificate.file.storage.exists(certificate.file.name)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("arrived", "generated", "can_generate", "hint"),
    [
        (False, False, False, "No member meets the qualification conditions yet."),
        (True, False, True, "1 member qualifies but has no certificate yet."),
        (True, True, True, None),
    ],
)
def test_settings_page_generation_hint(orga_client, event, arrived, generated, can_generate, hint):
    application = _member(event, arrived=arrived)
    if generated:
        generate_certificate(application)

    response = orga_client.get(_url(event, "certificates"))
    button = BeautifulSoup(response.content, "html.parser").find("button", attrs={"value": "generate_all"})

    assert button.has_attr("disabled") is not can_generate
    if hint is None:
        assert response.context["generation_hint"] is None
    else:
        assert str(response.context["generation_hint"]).startswith(hint)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("trigger", "hint", "manual_hint_hidden"),
    [
        (CertificateTrigger.MANUAL, "Certificates can be generated once the event has ended on", False),
        (CertificateTrigger.AUTO, "Certificates will be generated and emailed automatically once the event has ended on", True),
    ],
)
def test_settings_page_before_event_end(orga_client, event, application, trigger, hint, manual_hint_hidden):
    _configure(event, ended=False, trigger=trigger, require_after_event_end=True)

    response = orga_client.get(_url(event, "certificates"))
    soup = BeautifulSoup(response.content, "html.parser")

    assert soup.find("button", attrs={"value": "generate_all"}).has_attr("disabled")
    assert str(response.context["generation_hint"]).startswith(hint)
    manual_hint = soup.find(id="certificate-manual-hint")
    assert manual_hint.has_attr("hidden") is manual_hint_hidden
    assert manual_hint.find("a")["href"] == _url(event, "members")
    assert soup.find(id="id_generate_automatically") is not None
    assert "teamshifts/certificates.js" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_members_certificate_column_and_filter(orga_client, event):
    _member(event, "pending")
    generate_certificate(_member(event, "sent"))
    generate_certificate(_member(event, "downloaded"))
    generate_certificate(_member(event, "failed"))
    MemberCertificate.objects.filter(application__user__fullname="downloaded").update(downloaded_at=now())
    MemberCertificate.objects.filter(application__user__fullname="failed").update(notified_at=None)

    soup = BeautifulSoup(orga_client.get(_url(event, "members")).content, "html.parser")
    column = [th.get_text(strip=True) for th in soup.select("thead th")].index("Certificate")
    cells = {row.select("td")[1].get_text(strip=True): row.select("td")[column] for row in soup.select("tbody tr")}

    assert cells["pending"].get_text(" ", strip=True) == str(CertificateStatus.NOT_SENT.label)
    assert cells["failed"].get_text(" ", strip=True) == str(CertificateStatus.NOT_SENT.label)
    assert cells["sent"].find(class_="label")["class"] == ["label", CertificateStatus.SENT.label_class]
    assert cells["sent"].find(class_="ts-certificate-sent-date") is not None
    assert cells["downloaded"].find(class_="label")["class"] == ["label", CertificateStatus.DOWNLOADED.label_class]

    expected = {
        CertificateStatus.NOT_SENT: {"pending", "failed"},
        CertificateStatus.SENT: {"sent"},
        CertificateStatus.DOWNLOADED: {"downloaded"},
    }
    for status, names in expected.items():
        response = orga_client.get(_url(event, "members"), {"certificate": status})
        assert {member.user.fullname for member in response.context["members"]} == names
        assert f"certificate={status}" in response.context["download_csv_url"]


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["bulk_send", "automatic"])
def test_manual_and_automatic_sending_update_members_column(orga_client, event, path):
    application = _member(event, arrived=path == "bulk_send")
    if path == "bulk_send":
        orga_client.post(_url(event, "bulk_send_certificates"), {"member_ids": [application.pk]})
    else:
        _configure(event, trigger=CertificateTrigger.AUTO)
        orga_client.post(_url(event, "member_toggle_arrived", pk=application.pk))

    application.refresh_from_db()
    assert application.certificate_status == CertificateStatus.SENT
