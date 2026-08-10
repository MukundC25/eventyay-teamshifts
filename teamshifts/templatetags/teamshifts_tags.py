from django import template
from django_scopes import scope

from ..models import TeamShiftsEmailQueue

register = template.Library()


@register.simple_tag(takes_context=True)
def teamshifts_outbox_count(context):
    request = context.get("request")
    if not request or not hasattr(request, "event"):
        return 0
    with scope(event=request.event):
        return TeamShiftsEmailQueue.objects.filter(event=request.event, sent_at__isnull=True, user__isnull=False).count()
