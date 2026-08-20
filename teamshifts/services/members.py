from django.db import transaction
from django_scopes import scope
from eventyay.base.models import User
from eventyay.person.services import create_user

from ..models import ApplicationStatus, TeamApplicationAnswer, TeamMemberApplication


class AlreadyMemberError(Exception):
    def __init__(self, application: TeamMemberApplication):
        self.application = application
        super().__init__("User is already an accepted team member for this event.")


def resolve_or_create_user(*, email: str, full_name: str = "") -> tuple[User, bool]:
    email = email.lower().strip()
    full_name = (full_name or "").strip()
    existing = User.objects.filter(email__iexact=email).first()
    if existing:
        if full_name and full_name != (existing.fullname or ""):
            existing.fullname = full_name
            existing.save(update_fields=["fullname"])
        return existing, False
    return create_user(email=email, name=full_name, event=None), True


def add_member_from_organizer(*, event, form) -> TeamMemberApplication:
    """Create or accept a team member application from organizer-provided form data."""
    email = form.cleaned_data["email"]
    full_name = form.cleaned_data.get("full_name", "")
    phone = form.cleaned_data.get("phone", "")
    availability_notes = form.cleaned_data.get("availability_notes", "")
    answers = form.get_question_answers()

    with transaction.atomic():
        user, _created = resolve_or_create_user(email=email, full_name=full_name)
        with scope(event=event):
            application = TeamMemberApplication.objects.filter(event=event, user=user).first()
            if application and application.status == ApplicationStatus.ACCEPTED:
                raise AlreadyMemberError(application)

            if application:
                application.status = ApplicationStatus.ACCEPTED
                application.phone = phone
                application.availability_notes = availability_notes
                application.save(update_fields=["status", "phone", "availability_notes", "updated_at"])
                application.answers.all().delete()
            else:
                application = TeamMemberApplication.objects.create(
                    event=event,
                    user=user,
                    status=ApplicationStatus.ACCEPTED,
                    phone=phone,
                    availability_notes=availability_notes,
                )

            for question, answer_text in answers:
                TeamApplicationAnswer.objects.create(
                    application=application,
                    question=question,
                    answer=answer_text,
                )

    return application
