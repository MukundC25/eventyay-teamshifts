// Shared dynamic-formset logic for the shift create/edit "Roles Needed" table,
// so the two pages don't duplicate (and drift out of sync with) this logic.

export function setupDynamicFormset() {
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

        const reindex = (val) => val ? val.replace(/roles-\d+-/, `roles-${formCount}-`) : val;
        newRow.querySelectorAll("input, select, label, textarea").forEach((el) => {
            if (el.name) el.name = reindex(el.name);
            if (el.id) el.id = reindex(el.id);
            if (el.htmlFor) el.htmlFor = reindex(el.htmlFor);
        });

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
    });
}

// Delegated handler on #roles-body so cloned rows work without re-binding,
// and clicks outside a role row are a no-op instead of throwing.
export function bindRemoveRowHandler() {
    const rolesBody = document.getElementById("roles-body");
    if (!rolesBody) {
        return;
    }

    rolesBody.addEventListener("click", (event) => {
        const btn = event.target.closest(".remove-role-btn");
        if (!btn) {
            return;
        }

        const row = btn.closest(".role-form-row");
        if (!row) {
            return;
        }

        const deleteCheckbox = row.querySelector('.delete-checkbox input[type="checkbox"]');
        if (deleteCheckbox) {
            deleteCheckbox.checked = true;
            row.style.display = "none";
        } else {
            row.remove();
        }
    });
}

// Switches the roles table from the no-JS checkbox fallback to the
// trash-icon-button UX, once this script has actually run (see teamshifts.css).
export function markFormsetJsEnabled() {
    const rolesTable = document.getElementById("roles-table");
    if (rolesTable) {
        rolesTable.classList.add("js-formset-enabled");
    }
}
