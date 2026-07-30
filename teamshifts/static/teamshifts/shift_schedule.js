/**
 * Public shift schedule interaction.
 *
 * Handles:
 * - Claim form submission via AJAX so the page updates without a full reload.
 * - Confirmation prompt on withdraw (on shift_detail.html).
 *
 * Follows the no-jQuery, external-module, progressive-enhancement convention
 * used by apply.js and members.js throughout this plugin.
 *
 * @throws {Error} when the network request fails
 */

function gettext(msgid) {
    return typeof window.gettext === "function" ? window.gettext(msgid) : msgid;
}

function getCsrfToken() {
    const value = `; ${document.cookie}`;
    const parts = value.split("; csrftoken=");
    if (parts.length === 2) return parts.pop().split(";").shift();
    const parts2 = value.split("; eventyay_csrftoken=");
    if (parts2.length === 2) return parts2.pop().split(";").shift();
    return null;
}

/**
 * Submit a claim form via fetch and reload on success.
 *
 * Using a full page reload keeps all capacity counts consistent without
 * building a full reactive frontend. The claim action itself is idempotent
 * (get_or_create), so a double-submit is safe.
 */
async function handleClaimSubmit(form) {
    const button = form.querySelector("button[type='submit']");
    if (button) {
        button.disabled = true;
        button.textContent = gettext("Signing up…");
    }

    const csrfToken = getCsrfToken();
    if (!csrfToken) {
        window.location.reload();
        return;
    }

    try {
        const response = await fetch(form.action, {
            method: "POST",
            body: new FormData(form),
            headers: { "X-Requested-With": "XMLHttpRequest" },
            redirect: "follow",
        });

        // Server always redirects back to the schedule page; follow it.
        if (response.ok || response.redirected) {
            window.location.href = response.url || form.action.replace("/claim/", "/");
        } else {
            window.location.reload();
        }
    } catch {
        // Network failure — fall back to native form submission.
        if (button) button.disabled = false;
        form.submit();
    }
}

/**
 * Ask the user to confirm before submitting the withdraw form.
 */
function handleWithdrawSubmit(form, event) {
    if (!window.confirm(gettext("Are you sure you want to withdraw from this shift?"))) {
        event.preventDefault();
        return false;
    }
    const button = form.querySelector("button[type='submit']");
    if (button) {
        button.disabled = true;
        button.textContent = gettext("Withdrawing…");
    }
    return true;
}

document.addEventListener("DOMContentLoaded", () => {
    // Claim forms on the grid page
    document.querySelectorAll(".ts-claim-form").forEach((form) => {
        form.addEventListener("submit", (e) => {
            e.preventDefault();
            handleClaimSubmit(form);
        });
    });

    // Withdraw form on the detail page
    const withdrawForm = document.getElementById("ts-withdraw-form");
    if (withdrawForm) {
        withdrawForm.addEventListener("submit", (e) => {
            handleWithdrawSubmit(withdrawForm, e);
        });
    }
});
