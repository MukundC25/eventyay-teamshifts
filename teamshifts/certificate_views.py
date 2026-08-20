import json
import mimetypes
from io import BytesIO

from django.contrib import messages
from django.core.files.base import ContentFile
from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _, ngettext
from django.views.generic import View
from django_scopes import scope
from eventyay.base.models import CachedFile
from eventyay.control.views.pdf import BaseEditorView

from .forms import CertificateSettingsForm
from .models import ApplicationStatus, MemberCertificate, TeamMemberApplication
from .pdf import (
    CERTIFICATE_PLACEHOLDERS,
    default_certificate_pdf,
    default_layout,
    editor_variables,
    image_file_to_pdf,
    preview_context,
    render_certificate_pdf,
)
from .permissions import TeamShiftsPermissionRequiredMixin, can_view_email_addresses
from .services.certificates import (
    completed_shift_count,
    generate_all_certificates,
    get_certificate_settings,
    member_qualifies,
    zip_generated_certificates,
)
from .views import PluginActiveMixin

IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg"}


def _store_uploaded_background(settings, uploaded):
    content_type = (uploaded.content_type or mimetypes.guess_type(uploaded.name)[0] or "").lower()
    if content_type in IMAGE_TYPES or (uploaded.name or "").lower().endswith((".png", ".jpg", ".jpeg")):
        pdf_buffer = image_file_to_pdf(uploaded)
        uploaded = ContentFile(pdf_buffer.read(), name="background.pdf")
    elif content_type not in {"application/pdf", "application/x-pdf"} and not (uploaded.name or "").lower().endswith(".pdf"):
        raise ValueError(_("Please upload a PDF, PNG, or JPEG file."))
    if settings.background:
        settings.background.delete(save=False)
    settings.background.save("background.pdf", uploaded, save=True)


class CertificateSettingsView(PluginActiveMixin, TeamShiftsPermissionRequiredMixin, View):
    permission = "can_teamshifts_manage_applicants"
    template_name = "teamshifts/certificates.html"

    def get(self, request, *args, **kwargs):
        settings = get_certificate_settings(request.event)
        form = CertificateSettingsForm(instance=settings)
        return render(request, self.template_name, self._context(request, form, settings))

    def post(self, request, *args, **kwargs):
        settings = get_certificate_settings(request.event)
        action = request.POST.get("action")
        if action == "generate_all":
            count = generate_all_certificates(request.event)
            messages.success(
                request,
                ngettext(
                    "Generated certificates for %(count)s member.",
                    "Generated certificates for %(count)s members.",
                    count,
                )
                % {"count": count},
            )
            return redirect(self._url(request))
        if action == "download_all":
            archive = zip_generated_certificates(request.event)
            if not archive:
                messages.error(request, _("No generated certificates are available to download yet."))
                return redirect(self._url(request))
            response = FileResponse(archive, content_type="application/zip")
            response["Content-Disposition"] = f'attachment; filename="certificates-{request.event.slug}.zip"'
            return response

        form = CertificateSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            settings = form.save()
            uploaded = request.FILES.get("background")
            if uploaded:
                try:
                    _store_uploaded_background(settings, uploaded)
                except ValueError as exc:
                    messages.error(request, str(exc))
                    return render(request, self.template_name, self._context(request, form, settings))
            messages.success(request, _("Certificate settings have been saved."))
            return redirect(self._url(request))
        messages.error(request, _("We could not save your changes. See below for details."))
        return render(request, self.template_name, self._context(request, form, settings))

    def _url(self, request):
        return reverse(
            "plugins:teamshifts:certificates",
            kwargs={"organizer": request.organizer.slug, "event": request.event.slug},
        )

    def _context(self, request, form, settings):
        event = request.event
        with scope(event=event):
            members = list(TeamMemberApplication.objects.filter(event=event, status=ApplicationStatus.ACCEPTED).select_related("user"))
            certs = {certificate.application_id: certificate for certificate in MemberCertificate.objects.filter(application__in=members)}
        rows = []
        for member in members:
            certificate = certs.get(member.pk)
            rows.append(
                {
                    "member": member,
                    "qualifies": member_qualifies(member, settings),
                    "completed": completed_shift_count(member),
                    "generated": bool(certificate and certificate.file),
                    "downloaded": bool(certificate and certificate.downloaded_at),
                }
            )
        return {
            "form": form,
            "settings": settings,
            "placeholders": CERTIFICATE_PLACEHOLDERS,
            "rows": rows,
            "can_view_email": can_view_email_addresses(request.user, request.organizer, event, request=request),
        }


class CertificatePreviewView(PluginActiveMixin, TeamShiftsPermissionRequiredMixin, View):
    permission = "can_teamshifts_manage_applicants"

    def get(self, request, *args, **kwargs):
        settings = get_certificate_settings(request.event)
        pdf = render_certificate_pdf(settings, preview_context(request.event))
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="certificate-preview.pdf"'
        return response


class CertificateDefaultPdfView(PluginActiveMixin, TeamShiftsPermissionRequiredMixin, View):
    permission = "can_teamshifts_manage_applicants"

    def get(self, request, *args, **kwargs):
        pdf = default_certificate_pdf(
            locale=request.event.settings.locale,
            region=request.event.settings.region,
        )
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="certificate-default.pdf"'
        return response


class CertificateEditorView(PluginActiveMixin, BaseEditorView):
    permission = "can_change_settings"
    accepted_formats = ("application/pdf", "image/png", "image/jpeg")
    title = _("Member certificate layout")

    @cached_property
    def certificate_settings(self):
        return get_certificate_settings(self.request.event)

    def get_variables(self):
        return editor_variables()

    def get_images(self):
        return {}

    def get_layout_settings_key(self):
        return "teamshifts_certificate_layout"

    def get_background_settings_key(self):
        return "teamshifts_certificate_background"

    def get_default_background(self):
        return reverse(
            "plugins:teamshifts:certificate_default",
            kwargs={"organizer": self.request.organizer.slug, "event": self.request.event.slug},
        )

    def get_current_layout(self):
        layout = self.certificate_settings.layout
        if layout:
            return json.loads(layout)
        return default_layout()

    def get_current_background(self):
        if self.certificate_settings.background:
            return self.certificate_settings.background.url
        return self.get_default_background()

    def save_layout(self, layout_data=None):
        if layout_data is None:
            layout_data = self._get_posted_layout_json()
        self.certificate_settings.layout = layout_data or "[]"
        self.certificate_settings.save(update_fields=["layout"])

    def save_background(self, f: CachedFile):
        if not f.file:
            return
        if f.file.name.endswith("empty.pdf"):
            return
        self.certificate_settings.background.save("background.pdf", f.file)

    def _open_saved_background_pdf(self):
        if self.certificate_settings.background and self.certificate_settings.background.name:
            return self.certificate_settings.background.open("rb")
        return BytesIO(
            default_certificate_pdf(
                locale=self.request.event.settings.locale,
                region=self.request.event.settings.region,
            )
        )

    def process_upload(self):
        uploaded = self.request.FILES.get("background")
        error = False
        if uploaded.size > self.maxfilesize:
            error = _("The uploaded file is too large.")
        if uploaded.size < self.minfilesize:
            error = _("The uploaded file is too small.")
        content_type = (mimetypes.guess_type(uploaded.name)[0] or "").lower()
        if content_type not in self.accepted_formats and not (uploaded.name or "").lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
            error = _("Please only upload PDF or image files.")
        if error:
            return error, None
        if content_type in IMAGE_TYPES or (uploaded.name or "").lower().endswith((".png", ".jpg", ".jpeg")):
            uploaded = ContentFile(image_file_to_pdf(uploaded).read(), name="background.pdf")
        return None, uploaded

    def generate(self, p, override_layout=None, override_background=None):
        background = None
        if override_background is not None:
            background = override_background.open("rb") if hasattr(override_background, "open") else override_background
        pdf = render_certificate_pdf(
            self.certificate_settings,
            preview_context(self.request.event),
            layout=override_layout,
            background_file=background,
        )
        return "certificate-preview.pdf", "application/pdf", pdf
