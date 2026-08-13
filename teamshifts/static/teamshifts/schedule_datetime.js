document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-schedule-datetime]").forEach((input) => {
    const timeZone = input.dataset.eventTimezone;
    if (!timeZone) return;

    input.addEventListener("focus", () => {
      if (!input.value) {
        input.value = formatNowInTimeZone(timeZone);
      }
    }, { once: true });
  });
});

function formatNowInTimeZone(timeZone) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date());

  const lookup = Object.fromEntries(parts.map((p) => [p.type, p.value]));
  return `${lookup.year}-${lookup.month}-${lookup.day}T${lookup.hour}:${lookup.minute}`;
}
