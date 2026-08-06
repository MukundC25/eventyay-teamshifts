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

    if (!addRoleBtn || !rolesBody || !totalFormsInput) {
        return;
    }

    addRoleBtn.addEventListener("click", () => {
        const formCount = parseInt(totalFormsInput.value, 10);
        const rows = rolesBody.querySelectorAll(".role-form-row");
        if (rows.length === 0) {
            return;
        }

        const lastRow = rows[rows.length - 1];
        const newRow = lastRow.cloneNode(true);

        const regex = /roles-(\d+)-/g;
        newRow.innerHTML = newRow.innerHTML.replace(regex, `roles-${formCount}-`);

        newRow.querySelectorAll("input, select").forEach((input) => {
            if (input.type === "checkbox") {
                input.checked = false;
            } else if (input.tagName === "SELECT") {
                input.selectedIndex = 0;
            } else if (input.type !== "hidden" || input.name.endsWith("-id")) {
                input.value = input.name.endsWith("-capacity") ? "1" : "";
            }
        });

        newRow.querySelectorAll(".help-block").forEach((err) => err.remove());
        newRow.querySelectorAll(".has-error").forEach((cell) => cell.classList.remove("has-error"));
        newRow.style.display = "";

        rolesBody.appendChild(newRow);
        totalFormsInput.value = formCount + 1;

        bindRemoveButtons();
    });
}

document.addEventListener("DOMContentLoaded", () => {
    setupDynamicFormset();
    bindRemoveButtons();
});
