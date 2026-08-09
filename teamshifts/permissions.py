from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _
from django_scopes import scopes_disabled


def has_any_teamshifts_permission(user, organizer, event, request=None):
    if user.has_event_permission(organizer, event, "can_change_event_settings", request=request):
        return True
    teamshifts_perms = [
        "can_teamshifts_manage_applicants",
        "can_teamshifts_create_shifts",
        "can_teamshifts_create_roles",
        "can_teamshifts_send_emails",
        "can_teamshifts_view_email_addresses",
    ]
    return any(user.has_event_permission(organizer, event, p, request=request) for p in teamshifts_perms)


def get_allowed_role_ids(user, organizer, event, request=None):
    if user.has_event_permission(organizer, event, "can_change_event_settings", request=request):
        return None
    with scopes_disabled():
        from eventyay.base.models.organizer import Team

        teams = Team.objects.filter(
            organizer=organizer,
            members=user,
        )
        for team in teams:
            if getattr(team, "all_teamshifts_roles", True):
                return None
            limit = getattr(team, "limit_teamshifts_roles", None)
            if isinstance(limit, list) and limit:
                return set(limit)
    return set()


def can_act_on_role(user, organizer, event, role_pk, request=None):
    allowed = get_allowed_role_ids(user, organizer, event, request=request)
    if allowed is None:
        return True
    return role_pk in allowed


def teamshifts_permission_required(permission):
    def decorator(function):
        def wrapper(request, *args, **kw):
            if not request.user.is_authenticated:
                raise PermissionDenied()

            if request.user.has_event_permission(request.organizer, request.event, "can_change_event_settings", request=request):
                return function(request, *args, **kw)

            if permission:
                allowed = request.user.has_event_permission(request.organizer, request.event, permission, request=request)
                if allowed:
                    return function(request, *args, **kw)
            else:
                if has_any_teamshifts_permission(request.user, request.organizer, request.event, request=request):
                    return function(request, *args, **kw)

            raise PermissionDenied(_("You do not have permission to view this content."))

        return wrapper

    return decorator


class TeamShiftsPermissionRequiredMixin:
    permission = None

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        return teamshifts_permission_required(cls.permission)(view)
