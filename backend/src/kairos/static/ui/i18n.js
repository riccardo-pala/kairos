/** Interface copy shared by live and demo modes. Historical chat is preserved. */
import { state, $ } from "./state.js";
const copy = {
  you: ["Tu", "You"], error: ["Errore del workflow", "Workflow error"], progress: ["Stato del turno", "Turn progress"],
  busy: ["In corso…", "Working…"], waiting: ["In attesa", "Waiting"], creating: ["Creo sessione…", "Creating session…"],
  sessionReady: ["Sessione pronta", "Session ready"], createError: ["Creazione non riuscita", "Could not create session"],
  sending: ["Invio messaggio…", "Sending message…"], updating: ["Aggiorno la bozza…", "Updating draft…"],
  turnError: ["Turno non completato", "Turn not completed"], updated: ["Bozza aggiornata", "Draft updated"],
  ready: ["Bozza pronta", "Draft ready"], collecting: ["In raccolta", "Collecting details"],
  readyReview: ["Pronta da rivedere", "Ready for review"], none: ["Nessuna", "None"],
  newSession: ["Sessione creata. Descrivi l’impegno che vuoi preparare.", "Session created. Describe the event you want to draft."],
  changingLanguage: ["Cambio lingua…", "Changing language…"],
  demoReady: ["Demo pronta. I dati restano in questa scheda.", "Demo ready. Your data stays in this tab."],
  demoReadyShort: ["Demo pronta", "Demo ready"],
  demoLoading: ["Carico la demo…", "Loading demo…"], demoUnavailable: ["Demo non disponibile", "Demo unavailable"],
};
export function tr(key) { return copy[key]?.[state.language === "en" ? 1 : 0] || key; }
const labels = {
  title: ["Titolo", "Title"], start_date: ["Data", "Date"], start_time: ["Ora", "Time"],
  timezone: ["Fuso", "Timezone"], location: ["Luogo", "Location"], duration_minutes: ["Durata", "Duration"],
  tasks: ["Attività", "Activities"], reminders: ["Promemoria", "Reminders"],
};
export function applyUiLanguage() {
  const en = state.language === "en";
  document.documentElement.lang = state.language;
  const set = (selector, it, english) => { const node = $(selector); if (node) node.textContent = en ? english : it; };
  set(".language-picker .sr-only", "Lingua", "Language");
  if (!state.session && !state.busy) {
    $("#turn-status span:last-child").textContent = state.isDemo ? tr("demoReadyShort") : tr("waiting");
  }
  const title = $("#page-title");
  const accent = document.createElement("span"); accent.textContent = en ? "for what matters." : "al tuo tempo.";
  title.replaceChildren(document.createTextNode(en ? "Make time " : "Dai forma "), accent);
  const eyebrow = $(".welcome-eyebrow");
  eyebrow.replaceChildren(eyebrow.querySelector(".brand-wave"), document.createTextNode(en ? " YOUR TIME, YOUR IDEAS" : " IL TUO TEMPO, LE TUE IDEE"));
  set(".intro", "Racconta il tuo impegno. kAIros raccoglie i dettagli, tu scegli come completarli.", "Describe your plans. kAIros gathers the details; you decide how to complete them.");
  set("#session-title", "La tua sessione", "Your session");
  set("#create-session", "＋ Crea sessione", "＋ Create session");
  const timezoneLabel = $(".session-timezone label");
  if (timezoneLabel?.firstChild?.nodeType === Node.TEXT_NODE) timezoneLabel.firstChild.textContent = en ? "Timezone" : "Fuso orario";
  set(".session-id-line > span", "Sessione", "Session");
  if (!state.session) { set("#session-id", "Nessuna sessione", "No session"); set("#draft-status", "In attesa", "Waiting"); }
  set("#conversation-title", "Conversazione", "Conversation");
  set(".conversation-heading .eyebrow", "IL TUO SPAZIO", "YOUR SPACE");
  set("#draft-title", "Bozza corrente", "Current draft");
  set(".draft-card .eyebrow", "I TUOI DETTAGLI", "YOUR DETAILS");
  for (const [field, text] of Object.entries(labels)) {
    const node = document.querySelector(`[data-field="${field}"]`)?.previousElementSibling;
    if (node) node.textContent = text[en ? 1 : 0];
  }
  set(".empty-state strong", "Da un pensiero a un impegno.", "From an idea to a plan.");
  set(".empty-state p:not(.empty-example)", "Crea una sessione, poi racconta cosa hai in programma.", "Create a session, then describe what you have planned.");
  set(".empty-example", "“Devo andare dal meccanico domani”", "“I need to go to the mechanic tomorrow”");
  $("#message-input").placeholder = en ? "Write a message or add more details…" : "Scrivi un messaggio o aggiungi altri dettagli…";
  set(".composer .sr-only", "Il tuo messaggio", "Your message");
  set(".composer .hint", "Invio per spedire · Maiusc+Invio per andare a capo", "Enter to send · Shift+Enter for a new line");
  set("#send-message", "Invia ↗", "Send ↗");
  set(".provider-controls label", "Provider attivo", "Active provider");
  set("#activate-provider", "Attiva", "Activate");
  set("#diagnostics-title", "Diagnostica", "Diagnostics");
  set(".diagnostics-heading .eyebrow", "DIETRO LA CONVERSAZIONE", "BEHIND THE CONVERSATION");
  set(".section-description", "Log recenti API, workflow e connettore. Restano in memoria solo finché il processo è attivo.", "Recent API, workflow and connector logs. Kept in memory while the process is running.");
  set("#refresh-diagnostics", "Aggiorna", "Refresh"); set("#clear-diagnostics", "Svuota log", "Clear logs");
  set("#apply-filter", "Filtra", "Filter"); set(".filter-row label", "Filtra per request ID", "Filter by request ID");
  set("#raw-panel summary strong", "Eventi della risposta", "Response events");
  set(".privacy-note", "La diagnostica può contenere messaggi, prompt e bozze. API amministrative e playground sono senza autenticazione: mantieni il servizio su localhost.", "Diagnostics may contain messages, prompts and drafts. Admin APIs and the playground have no authentication: keep the service on localhost.");
  set(".footer > span", "Uno spazio per sperimentare, un impegno alla volta.", "A space to experiment, one plan at a time.");
  set("#environment-label", state.isDemo ? "Demo simulata" : "Ambiente locale", state.isDemo ? "Simulated demo" : "Local environment");
  const notice = $("#demo-notice");
  if (notice) {
    const runtime = $("#demo-runtime-status");
    const strong = document.createElement("strong"); strong.textContent = en ? "Simulated public demo. " : "Demo pubblica simulata. ";
    notice.replaceChildren(strong, document.createTextNode(en
      ? "Choose an example or use the draft controls. Responses and waiting time are simulated; no model is called. "
      : "Scegli un esempio o usa i controlli della bozza. Risposte e attesa sono simulate; nessun modello viene chiamato. "), runtime);
    if (state.client && !state.busy) runtime.textContent = tr("demoReady");
  }
}

export function timezoneOffsetMinutes(zone, now) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: zone, year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  }).formatToParts(now);
  const values = Object.fromEntries(parts.filter(part => part.type !== "literal").map(part => [part.type, Number(part.value)]));
  const local = Date.UTC(values.year, values.month - 1, values.day, values.hour, values.minute, values.second);
  return (local - Math.floor(now.getTime() / 1000) * 1000) / 60000;
}

export function orderedTimezones(values, now = new Date()) {
  return [...new Set(values)].map(zone => ({ zone, offset: timezoneOffsetMinutes(zone, now) }))
    .sort((a, b) => a.offset - b.offset || a.zone.localeCompare(b.zone));
}

export function populateTimezones() {
  const select = $("#timezone-select");
  const selected = select.value || Intl.DateTimeFormat().resolvedOptions().timeZone || "Europe/Rome";
  const fallback = ["Europe/Rome", "Europe/London", "Europe/Paris", "Europe/Berlin", "America/New_York", "America/Los_Angeles", "Asia/Tokyo", "Asia/Kolkata", "Australia/Sydney"];
  const values = typeof Intl.supportedValuesOf === "function" ? Intl.supportedValuesOf("timeZone") : fallback;
  const zones = orderedTimezones([selected, "UTC", ...values]);
  select.replaceChildren(...zones.map(({ zone, offset }) => {
    const option = document.createElement("option"); option.value = zone;
    const absolute = Math.abs(offset);
    const hours = String(Math.floor(absolute / 60)).padStart(2, "0");
    const minutes = String(absolute % 60).padStart(2, "0");
    option.textContent = `UTC${offset < 0 ? "−" : "+"}${hours}:${minutes} · ${zone.replaceAll("_", " ")}`;
    return option;
  }));
  select.value = selected;
}
