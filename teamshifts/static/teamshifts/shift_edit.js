function bindRemoveButtons() {
    document.querySelectorAll(".remove-role-btn").forEach((btn) => {
        const newBtn = btn.cloneNode(true);
        btn.parentNode.replaceChild(newBtn, btn);

        newBtn.addEventListener("click", () => {
            const row = newBtn.closest("tr");
            if (!row) return;
            const deleteCheckbox = row.querySelector('.delete-checkbox input[type="checkbox"]');
            if (deleteCheckbox) {
                deleteCheckbox.checked = true;
                row.style.display = "none";
            } else {
                row.remove();
            }
        });
    });
}

function setupDynamicFormset() {
    const addRoleBtn = document.getElementById("add-role-btn");
    const rolesBody = document.getElementById("roles-body");
    const totalFormsInput = document.getElementById("id_roles-TOTAL_FORMS");
    const emptyFormContainer = document.getElementById("empty-role-form");

    if (!addRoleBtn || !rolesBody || !totalFormsInput || !emptyFormContainer) {
        return;
    }

    const emptyRowTemplate = emptyFormContainer.querySelector("tr");
    if (!emptyRowTemplate) {
        return;
    }

    addRoleBtn.addEventListener("click", () => {
        const formCount = parseInt(totalFormsInput.value, 10);

        const newRow = emptyRowTemplate.cloneNode(true);
        newRow.innerHTML = newRow.innerHTML.replace(/__prefix__/g, String(formCount));

        newRow.querySelectorAll("input, select").forEach((input) => {
            if (input.type === "checkbox") {
                input.checked = false;
            } else if (input.tagName === "SELECT") {
                input.selectedIndex = 0;
            } else if (!input.name.endsWith("-id")) {
                input.value = input.name.endsWith("-capacity") ? "1" : "";
            }
        });

        rolesBody.appendChild(newRow);
        totalFormsInput.value = formCount + 1;

        bindRemoveButtons();
    });
}

document.addEventListener("DOMContentLoaded", () => {
    setupDynamicFormset();
    bindRemoveButtons();
});
