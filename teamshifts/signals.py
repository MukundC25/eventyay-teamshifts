from django.dispatch import receiver
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from eventyay.control.signals import event_dashboard_widgets

# event_dashboard_components was added in feat/teamshifts-plugin-support and is not
# yet merged into dev.  Import it defensively so the plugin loads cleanly against
# the current dev branch while the PR is still in review.
try:
    from eventyay.control.signals import event_dashboard_components
except ImportError:
    event_dashboard_components = None


@receiver(event_dashboard_widgets, dispatch_uid="teamshifts_dashboard_widget")
def teamshifts_dashboard_widget(sender, subevent=None, lazy=False, **kwargs):
    return [
        {
            "content": ('<div class="numwidget"><span class="num">-</span><span class="text">{}</span></div>').format(str(_("TeamShifts"))),
            "display_size": "small",
            "priority": 80,
            "url": reverse(
                "plugins:teamshifts:dashboard",
                kwargs={
                    "organizer": sender.organizer.slug,
                    "event": sender.slug,
                },
            ),
        }
    ]


def teamshifts_dashboard_component(sender, request=None, **kwargs):
    if not request or not request.user.has_event_permission(sender.organizer, sender, "can_change_event_settings", request=request):
        return ""
    url = reverse(
        "plugins:teamshifts:dashboard",
        kwargs={
            "organizer": sender.organizer.slug,
            "event": sender.slug,
        },
    )
    return format_html(
        '<div class="panel panel-default widget-container widget-small no-padding last-column">'
        '<div class="panel-heading"><h3 class="panel-title">{}</h3></div>'
        '<div class="panel-body"><p>{}</p><p>{} <a href="{}">{}</a></p></div>'
        "</div>",
        str(_("TeamShifts")),
        str(_("Manage event teams, define team roles, review team member applications, and build a shift schedule for your event staff.")),
        str(_("Go to")),
        url,
        str(_("TeamShifts Dashboard")),
    )


# Wire up the component receiver only when the signal is available.
if event_dashboard_components is not None:
    receiver(event_dashboard_components, dispatch_uid="teamshifts_dashboard_component")(teamshifts_dashboard_component)
