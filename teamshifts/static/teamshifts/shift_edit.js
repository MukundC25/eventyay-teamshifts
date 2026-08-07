import { bindRemoveRowHandler, markFormsetJsEnabled, setupDynamicFormset } from "./shift_role_formset.js";

document.addEventListener("DOMContentLoaded", () => {
    setupDynamicFormset();
    bindRemoveRowHandler();
    markFormsetJsEnabled();
});
