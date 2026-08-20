import json
from io import BytesIO

from django.utils.formats import date_format
from django.utils.translation import gettext, gettext_lazy as _
from eventyay.base.i18n import language
from eventyay.base.pdf import Renderer
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas

from .models import CertificateSettings

CERTIFICATE_PLACEHOLDERS = (
    ("member_name", _("Member name"), "Jane Member"),
    ("member_email", _("Member email"), "jane@example.com"),
    ("event_name", _("Event name"), "Sample Event"),
    ("event_dates", _("Event dates"), "1–3 January 2026"),
    ("organizer_name", _("Organizer name"), "Sample Organizer"),
    ("completed_shift_count", _("Completed shift count"), "2"),
    ("assigned_shift_count", _("Assigned shift count"), "3"),
    ("roles", _("Assigned roles"), "Registration, Info desk"),
)

NAVY = [27, 54, 93, 1]

DEFAULT_CERTIFICATE_LAYOUT = [
    {
        "type": "textarea",
        "left": "40.00",
        "bottom": "124.00",
        "fontsize": "26.0",
        "color": NAVY,
        "fontfamily": "Open Sans",
        "bold": True,
        "italic": False,
        "width": "217.00",
        "content": "member_name",
        "text": "Jane Member",
        "align": "center",
    },
    {
        "type": "textarea",
        "left": "40.00",
        "bottom": "88.00",
        "fontsize": "16.0",
        "color": NAVY,
        "fontfamily": "Open Sans",
        "bold": True,
        "italic": False,
        "width": "217.00",
        "content": "event_name",
        "text": "Sample Event",
        "align": "center",
    },
    {
        "type": "textarea",
        "left": "40.00",
        "bottom": "74.00",
        "fontsize": "12.0",
        "color": [51, 51, 51, 1],
        "fontfamily": "Open Sans",
        "bold": False,
        "italic": False,
        "width": "217.00",
        "content": "event_dates",
        "text": "1–3 January 2026",
        "align": "center",
    },
    {
        "type": "textarea",
        "left": "40.00",
        "bottom": "56.00",
        "fontsize": "11.0",
        "color": [51, 51, 51, 1],
        "fontfamily": "Open Sans",
        "bold": False,
        "italic": False,
        "width": "217.00",
        "content": "organizer_name",
        "text": "Sample Organizer",
        "align": "center",
    },
]


def editor_variables():
    return {key: {"label": label, "editor_sample": sample} for key, label, sample in CERTIFICATE_PLACEHOLDERS}


def preview_context(event):
    return {
        "member_name": "Jane Member",
        "member_email": "jane@example.com",
        "event_name": str(event.name),
        "event_dates": format_event_dates(event),
        "organizer_name": str(event.organizer.name),
        "completed_shift_count": "2",
        "assigned_shift_count": "3",
        "roles": "Registration, Info desk",
    }


def format_event_dates(event):
    start = date_format(event.date_from, "DATE_FORMAT")
    if event.date_to:
        return f"{start} – {date_format(event.date_to, 'DATE_FORMAT')}"
    return start


def default_layout():
    return json.loads(json.dumps(DEFAULT_CERTIFICATE_LAYOUT))


def layout_is_initial_overlay(layout_json: str) -> bool:
    try:
        items = json.loads(layout_json or "[]")
    except json.JSONDecodeError:
        return True
    contents = [item.get("content") for item in items if item.get("type") == "textarea"]
    types = {item.get("type") for item in items}
    if types <= {"textarea", "poweredby"} and contents in (
        ["member_name", "event_name", "event_dates"],
        ["volunteer_name", "event_name", "event_dates"],
        ["member_name", "event_name", "event_dates", "organizer_name"],
    ):
        return True
    return False


def default_certificate_pdf(locale=None, region=None) -> bytes:
    Renderer._register_fonts()
    buffer = BytesIO()
    page_width, page_height = landscape(A4)
    canvas = Canvas(buffer, pagesize=(page_width, page_height))
    navy = HexColor("#1B365D")
    gold = HexColor("#C4A35A")
    ink = HexColor("#333333")

    with language(locale or "en", region):
        canvas.setStrokeColor(navy)
        canvas.setLineWidth(2.4)
        canvas.rect(10 * mm, 10 * mm, 277 * mm, 190 * mm, stroke=1, fill=0)

        canvas.setStrokeColor(gold)
        canvas.setLineWidth(1.1)
        canvas.rect(12.5 * mm, 12.5 * mm, 272 * mm, 185 * mm, stroke=1, fill=0)

        canvas.setStrokeColor(navy)
        canvas.setLineWidth(0.4)
        canvas.rect(14.5 * mm, 14.5 * mm, 268 * mm, 181 * mm, stroke=1, fill=0)

        canvas.setFillColor(navy)
        canvas.setFont("Open Sans B", 26)
        canvas.drawCentredString(page_width / 2, 172 * mm, str(gettext("Certificate of Participation")))

        canvas.setStrokeColor(gold)
        canvas.setLineWidth(1.15)
        canvas.line(88 * mm, 166 * mm, 209 * mm, 166 * mm)

        canvas.setFillColor(ink)
        canvas.setFont("Open Sans I", 13)
        canvas.drawCentredString(page_width / 2, 152 * mm, str(gettext("This is to certify that")))

        canvas.setStrokeColor(navy)
        canvas.setLineWidth(0.55)
        canvas.line(68 * mm, 121 * mm, 229 * mm, 121 * mm)

        canvas.setFillColor(ink)
        canvas.setFont("Open Sans I", 12)
        canvas.drawCentredString(page_width / 2, 106 * mm, str(gettext("has served as a team member at")))

        canvas.setFont("Open Sans", 10)
        canvas.setFillColor(HexColor("#666666"))
        canvas.drawCentredString(page_width / 2, 32 * mm, str(gettext("Thank you for your contribution.")))

    canvas.showPage()
    canvas.save()
    buffer.seek(0)
    return buffer.read()


def image_file_to_pdf(uploaded) -> BytesIO:
    uploaded.seek(0)
    image = ImageReader(uploaded)
    width, height = image.getSize()
    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=(width, height))
    canvas.drawImage(image, 0, 0, width=width, height=height, preserveAspectRatio=True, mask="auto")
    canvas.showPage()
    canvas.save()
    buffer.seek(0)
    return buffer


class CertificateRenderer(Renderer):
    def __init__(self, event, layout, background_file, context: dict):
        super().__init__(event, layout, background_file)
        self.context = context
        self.variables = {}
        self.images = {}

    def _get_text_content(self, op, order, o, inner=False):
        content = o.get("content")
        if not content:
            return ""
        if content == "other":
            return o.get("text") or ""
        return str(self.context.get(content, ""))

    def draw_page(self, canvas: Canvas, order=None, op=None, show_page=True):
        allowed = {"textarea", "poweredby"}
        layout = [obj for obj in self.layout if obj.get("type") in allowed]
        original = self.layout
        self.layout = layout
        try:
            super().draw_page(canvas, order, op, show_page=show_page)
        finally:
            self.layout = original


def render_certificate_pdf(settings: CertificateSettings, context: dict, layout=None, background_file=None) -> bytes:
    layout = layout if layout is not None else (json.loads(settings.layout) if settings.layout else default_layout())
    locale = getattr(getattr(settings.event, "settings", None), "locale", None)
    region = getattr(getattr(settings.event, "settings", None), "region", None)
    if background_file is not None:
        background = background_file
    elif settings.background and settings.background.name:
        background = settings.background.open("rb")
    else:
        background = BytesIO(default_certificate_pdf(locale=locale, region=region))
    Renderer._register_fonts()
    buffer = BytesIO()
    renderer = CertificateRenderer(settings.event, layout, background, context)
    canvas = Canvas(buffer, pagesize=landscape(A4))
    renderer.draw_page(canvas)
    canvas.save()
    return renderer.render_background(buffer, str(_("Member certificate"))).read()
