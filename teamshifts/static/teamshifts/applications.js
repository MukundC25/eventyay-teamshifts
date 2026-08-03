function gettext(msgid) {
    return typeof window.gettext === "function" ? window.gettext(msgid) : msgid;
}

function getConfirmMessage(newStatus, emailStatuses) {
    if (emailStatuses.includes(newStatus)) {
        return gettext("Are you sure you want to change the status? This may send an email to the applicant.");
    }
    return gettext("Are you sure you want to update the application status?");
}

function setupStatusDropdowns() {
    document.querySelectorAll(".teamshifts-status-dropdown").forEach((select) => {
        const currentStatus = select.dataset.currentStatus;
        const emailStatuses = (select.dataset.emailStatuses || "").split(",").filter(Boolean);

        select.addEventListener("change", () => {
            const newStatus = select.value;

            if (newStatus === currentStatus) {
                return;
            }

            window
                .showConfirmDialog({ message: getConfirmMessage(newStatus, emailStatuses) })
                .then((confirmed) => {
                    if (confirmed) {
                        select.form.requestSubmit();
                    } else {
                        select.value = currentStatus;
                    }
                });
        });
    });
}

function setupSelectAll() {
    const selectAll = document.getElementById("select-all");
    if (!selectAll) {
        return;
    }

    selectAll.addEventListener("change", () => {
        document.querySelectorAll(".app-checkbox:not([disabled])").forEach((checkbox) => {
            checkbox.checked = selectAll.checked;
        });
    });
}

document.addEventListener("DOMContentLoaded", () => {
    setupStatusDropdowns();
    setupSelectAll();
});
