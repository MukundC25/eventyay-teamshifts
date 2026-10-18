function initManualGenerationHint() {
    const field = document.getElementById("id_generate_automatically");
    const hint = document.getElementById("certificate-manual-hint");
    if (!field || !hint) return;

    function update() {
        hint.hidden = field.checked;
    }

    field.addEventListener("change", update);
    update();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initManualGenerationHint);
} else {
    initManualGenerationHint();
}
