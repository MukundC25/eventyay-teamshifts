function gettext(msgid) {
    return typeof window.gettext === "function" ? window.gettext(msgid) : msgid;
}

/**
 * @throws {Error} when the request fails (network error or non-2xx response)
 */
async function toggleArrived(form) {
    const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        headers: {
            "X-Requested-With": "XMLHttpRequest",
        },
    });
    if (!response.ok) {
        throw new Error(`Toggle arrived request failed with status ${response.status}`);
    }
    return response.json();
}

function setButtonState(button, arrived) {
    button.className = arrived ? "btn btn-sm btn-success" : "btn btn-sm btn-default";
    const icon = document.createElement("i");
    icon.className = arrived ? "fa fa-check" : "fa fa-times";
    button.innerHTML = "";
    button.appendChild(icon);
    button.appendChild(document.createTextNode(` ${gettext(arrived ? "Arrived" : "Not arrived")}`));
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
                alert(gettext("An error occurred."));
            } finally {
                button.disabled = false;
            }
        });
    });
});
