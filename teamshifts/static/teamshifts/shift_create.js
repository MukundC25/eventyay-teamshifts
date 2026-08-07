import { bindRemoveRowHandler, markFormsetJsEnabled, setupDynamicFormset } from "./shift_role_formset.js";

function gettext(msgid) {
    return typeof window.gettext === "function" ? window.gettext(msgid) : msgid;
}

function setupModeToggle() {
    const modeRadios = document.querySelectorAll('input[name="mode"]');
    const repeatOptionsDiv = document.getElementById("repeat-options");
    if (!modeRadios.length || !repeatOptionsDiv) {
        return;
    }

    function toggleRepeatOptions() {
        let isRepeating = false;
        modeRadios.forEach((radio) => {
            if (radio.checked && radio.value === "repeating") {
                isRepeating = true;
            }
        });
        repeatOptionsDiv.style.display = isRepeating ? "block" : "none";
    }

    modeRadios.forEach((radio) => radio.addEventListener("change", toggleRepeatOptions));
    toggleRepeatOptions();
}

function setupPreviewOccurrences() {
    const previewBtn = document.getElementById("preview-occurrences-btn");
    const previewDiv = document.getElementById("occurrences-preview");
    const startTimeInput = document.getElementById("id_start_time");
    const endTimeInput = document.getElementById("id_end_time");
    const lengthInput = document.getElementById("id_shift_length_minutes");

    if (!previewBtn || !previewDiv || !startTimeInput || !endTimeInput || !lengthInput) {
        return;
    }

    function formatDt(dt) {
        const year = dt.getFullYear();
        const month = String(dt.getMonth() + 1).padStart(2, "0");
        const day = String(dt.getDate()).padStart(2, "0");
        const hrs = String(dt.getHours()).padStart(2, "0");
        const mins = String(dt.getMinutes()).padStart(2, "0");
        return `${year}-${month}-${day} ${hrs}:${mins}`;
    }

    previewBtn.addEventListener("click", () => {
        const startStr = startTimeInput.value;
        const endStr = endTimeInput.value;
        const lengthStr = lengthInput.value;

        if (!startStr || !endStr || !lengthStr) {
            previewDiv.innerHTML = `<p class="text-danger">${gettext("Please fill in Start Time, End Time, and Shift Length.")}</p>`;
            previewDiv.style.display = "block";
            return;
        }

        const startDate = new Date(startStr);
        const endDate = new Date(endStr);
        const lengthMins = parseInt(lengthStr, 10);

        if (endDate <= startDate) {
            previewDiv.innerHTML = `<p class="text-danger">${gettext("End Time must be after Start Time.")}</p>`;
            previewDiv.style.display = "block";
            return;
        }

        if (lengthMins <= 0) {
            previewDiv.innerHTML = `<p class="text-danger">${gettext("Shift Length must be greater than 0.")}</p>`;
            previewDiv.style.display = "block";
            return;
        }

        const durationMins = (endDate - startDate) / (1000 * 60);
        if (durationMins % lengthMins !== 0) {
            previewDiv.innerHTML = `<p class="text-warning">${gettext("Warning: The shift length does not divide evenly into the total duration.")}</p>`;
        } else {
            previewDiv.innerHTML = "";
        }

        let curr = new Date(startDate);
        const occurrences = [];
        let safetyCounter = 0;

        while (curr < endDate && safetyCounter < 100) {
            const next = new Date(curr.getTime() + lengthMins * 60000);
            if (next > endDate) {
                break;
            }
            occurrences.push(`${formatDt(curr)} \u2013 ${formatDt(next)}`);
            curr = next;
            safetyCounter++;
        }

        if (safetyCounter >= 100) {
            previewDiv.innerHTML += `<p class="text-warning">${gettext("Too many occurrences (limited to 100 for preview).")}</p>`;
        } else {
            previewDiv.innerHTML += `<strong>${gettext("Will create")} ${occurrences.length} ${gettext("shifts:")}</strong><br/>${occurrences.join("<br/>")}`;
        }
        previewDiv.style.display = "block";
    });
}

document.addEventListener("DOMContentLoaded", () => {
    setupModeToggle();
    setupPreviewOccurrences();
    setupDynamicFormset();
    bindRemoveRowHandler();
    markFormsetJsEnabled();
});
