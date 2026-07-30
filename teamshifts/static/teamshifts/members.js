function gettext(msgid) {
    return typeof window.gettext === "function" ? window.gettext(msgid) : msgid;
}

/**
 * @throws {Error} when the network request fails
 */
async function toggleArrived(form) {
    const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        headers: {
            "X-Requested-With": "XMLHttpRequest",
        },
    });
    return response.json();
}

function setButtonState(button, arrived) {
    if (arrived) {
        button.className = "btn btn-sm btn-success";
        button.innerHTML = `<i class="fa fa-check"></i> ${gettext("Arrived")}`;
    } else {
        button.className = "btn btn-sm btn-default";
        button.innerHTML = `<i class="fa fa-times"></i> ${gettext("Not arrived")}`;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".toggle-arrived-form").forEach((form) => {
        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            const button = form.querySelector("button");
            const originalHtml = button.innerHTML;
            button.disabled = true;
            button.innerHTML = '<i class="fa fa-spinner fa-spin"></i>';

            try {
                const data = await toggleArrived(form);
                if (data.success) {
                    setButtonState(button, data.arrived);
                } else {
                    button.innerHTML = originalHtml;
                    alert(gettext("An error occurred."));
                }
            } catch (error) {
                console.error("Failed to toggle arrived status", error);
                button.innerHTML = originalHtml;
            } finally {
                button.disabled = false;
            }
        });
    });
});
