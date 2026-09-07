import logging
from collections.abc import Sequence
from typing import TypedDict

from django.db import transaction
from django.utils.timezone import now
from django_scopes import scope
from eventyay.base.email import get_email_context
from eventyay.base.models import Event, Voucher
from eventyay.base.services.mail import SendMailException, mail
from eventyay.multidomain.urlreverse import build_absolute_uri
from i18nfield.strings import LazyI18nString

from ..models import (
    CallForTeamMembers,
    EmailTemplateRoles,
    MemberVoucher,
    TeamMemberApplication,
    VolunteerVoucherSettings,
    VoucherStatus,
)

logger = logging.getLogger(__name__)


class SendResult(TypedDict):
    sent: int
    resent: int
    skipped_claimed: int
    skipped_no_vouchers: int


def allocate_and_send_vouchers(
    event: Event,
    settings: VolunteerVoucherSettings,
    applications: Sequence[TeamMemberApplication],
) -> SendResult:
    """Allocate voucher codes and send emails for selected members.

    Behaviour per member:
    - Not sent → pick an unused voucher from the batch, send email, status = sent
    - Sent — not claimed → resend the same code, no new voucher allocated
    - Claimed → skip silently
    """
    result: SendResult = {"sent": 0, "resent": 0, "skipped_claimed": 0, "skipped_no_vouchers": 0}

    try:
        cfm = event.call_for_team_members
    except CallForTeamMembers.DoesNotExist:
        cfm = None

    if cfm is None:
        logger.warning("[TeamShifts] No CFM for event %s, cannot resolve voucher email template", event.slug)
        return result

    template = cfm.get_mail_template(EmailTemplateRoles.VOUCHER_SENT)
    locale = event.settings.locale

    for application in applications:
        user = application.user
        if not user or not user.email:
            continue

        with scope(event=event):
            existing = MemberVoucher.objects.filter(application=application).select_related("voucher").first()

        if existing is not None:
            existing.refresh_claimed_status()
            if existing.status == VoucherStatus.CLAIMED:
                result["skipped_claimed"] += 1
                continue

            if _send_voucher_email(event, user, existing.voucher, template, locale):
                if existing.status == VoucherStatus.NOT_SENT:
                    existing.status = VoucherStatus.SENT
                existing.sent_at = now()
                existing.save(update_fields=["status", "sent_at"])
                result["resent"] += 1
            continue

        with scope(event=event), transaction.atomic():
            voucher = _claim_next_voucher(settings)
            if voucher is None:
                result["skipped_no_vouchers"] += 1
                continue

            member_voucher = MemberVoucher.objects.create(
                application=application,
                voucher=voucher,
                status=VoucherStatus.NOT_SENT,
                sent_at=None,
            )

        if _send_voucher_email(event, user, voucher, template, locale):
            member_voucher.status = VoucherStatus.SENT
            member_voucher.sent_at = now()
            member_voucher.save(update_fields=["status", "sent_at"])
            result["sent"] += 1

    return result


def _claim_next_voucher(settings: VolunteerVoucherSettings) -> Voucher | None:
    """Pick and lock one unused voucher from the batch.

    Must be called inside a transaction.atomic() block so the row lock
    is held until the caller creates the MemberVoucher assignment.
    """
    assigned_ids = MemberVoucher.objects.filter(
        application__event=settings.event,
    ).values_list("voucher_id", flat=True)

    return (
        Voucher.objects.filter(
            event=settings.event,
            tag=settings.voucher_tag,
            redeemed=0,
        )
        .exclude(pk__in=assigned_ids)
        .select_for_update(skip_locked=True)
        .first()
    )


def _send_voucher_email(event, user, voucher, template, locale) -> bool:
    redeem_base = build_absolute_uri(event, "presale:event.index")
    ticket_claim_url = f"{redeem_base}?voucher={voucher.code}"

    context = get_email_context(event=event, user=user)
    context["voucher_code"] = voucher.code
    context["ticket_claim_url"] = ticket_claim_url

    subject = LazyI18nString(template.subject)
    body = LazyI18nString(template.body)

    try:
        mail(
            email=user.email,
            subject=subject,
            template=body,
            context=context,
            event=event,
            locale=locale,
            user=user,
            auto_email=False,
            sync_send=True,
        )
    except SendMailException:
        logger.exception("[TeamShifts] Failed to send voucher email to %s", user.email)
        return False
    return True
