import { tr } from "./i18n.js";
import { state, $, conversation, conversationEmpty, messageInput, sendButton, turnStatus } from "./state.js";

let submitStructuredAction;
export function configureDraft(onAction) { submitStructuredAction = onAction; }

export function formatDuration(totalMinutes, language = state.language || "it") {
  const labels = language === "it"
    ? [["giorno", "giorni"], ["ora", "ore"], ["minuto", "minuti"]]
    : [["day", "days"], ["hour", "hours"], ["minute", "minutes"]];
  const parts = [
    Math.floor(totalMinutes / 1440),
    Math.floor((totalMinutes % 1440) / 60),
    totalMinutes % 60,
  ];
  return parts.flatMap((amount, index) => amount > 0
    ? [`${amount} ${labels[index][amount === 1 ? 0 : 1]}`]
    : []).join(" ");
}

export function formatReminder(minutes, language = state.language || "it") {
  if (minutes === 0) return language === "it" ? "All’inizio dell’impegno" : "At the start of the event";
  return `${formatDuration(minutes, language)} ${language === "it" ? "prima" : "before"}`;
}

export function formatValue(value, field) {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) {
    if (!value.length) return tr("none");
    return value.map((item) => {
      if (typeof item === "object" && item !== null) {
        if ("description" in item) return `${item.description} (${state.language === "it" ? (item.timing === "before" ? "prima" : "dopo") : item.timing})`;
        if ("minutes_before" in item) return formatReminder(item.minutes_before);
      }
      return String(item);
    }).join("\n");
  }
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  if (field === "duration_minutes") return formatDuration(value);
  return String(value);
}

export function renderSession(session) {
  state.session = session;
  $("#session-id").textContent = session.id;
  $("#draft-status").textContent = session.state.status === "ready_for_review" ? tr("readyReview") : tr("collecting");
  $("#draft-status").classList.toggle("ready", session.state.status === "ready_for_review");
  renderGuidance(session);
  const draft = session.state.draft;
  const values = {
    title: draft.title,
    start_date: draft.start_date,
    start_time: draft.start_time,
    timezone: draft.timezone || session.timezone,
    location: draft.location,
    duration_minutes: draft.duration_minutes,
    tasks: draft.tasks,
    reminders: draft.reminders,
  };
  document.querySelectorAll("[data-field]").forEach((element) => {
    element.textContent = formatValue(values[element.dataset.field], element.dataset.field);
  });
  sendButton.disabled = state.busy;
  messageInput.disabled = state.busy;
  if (!state.busy) messageInput.focus();
}

export function renderGuidance(session, focusSuggestionId = null) {
  const guidance = session.guidance || { required_missing: [], suggestions: [] };
  const section = $("#chat-guidance");
  const requiredFields = guidance.required_missing || [];
  const suggestions = guidance.suggestions || [];
  const pendingTasks = getPendingRemovalTasks(session.state);
  section.replaceChildren();

  if (!suggestions.length && !pendingTasks.length && !requiredFields.length) {
    section.classList.add("hidden");
    state.activeSuggestionId = null;
    return;
  }

  const activeSuggestion = suggestions.find((suggestion) => suggestion.id === state.activeSuggestionId);
  if (state.activeSuggestionId && !activeSuggestion) {
    delete state.guidanceValues[state.activeSuggestionId];
    state.activeSuggestionId = null;
  }
  section.classList.remove("hidden");

  const panel = document.createElement("section");
  panel.className = "chat-guidance-panel";
  panel.setAttribute("aria-label", session.language === "it" ? "Opzioni per la bozza" : "Draft options");

  const message = document.createElement("p");
  message.className = "chat-guidance-copy";
  const missing = requiredFields.map((field) => field.label).join(", ");
  message.textContent = missing
    ? (session.language === "it"
      ? `${guidance.required_title}: ${missing}. Scegli un’opzione oppure continua a scrivere in chat.`
      : `${guidance.required_title}: ${missing}. Choose an option or keep writing in the chat.`)
    : (session.language === "it"
      ? "Puoi aggiungere questi dettagli quando vuoi, oppure continuare a scrivere in chat."
      : "Add any of these details whenever you like, or keep writing in the chat.");
  panel.append(message);

  const options = document.createElement("div");
  options.className = "chat-guidance-options";
  options.setAttribute("role", "group");
  options.setAttribute("aria-label", session.language === "it" ? "Scegli un dettaglio" : "Choose a detail");
  for (const suggestion of suggestions) {
    const button = document.createElement("button");
    const selected = suggestion.id === state.activeSuggestionId;
    button.type = "button";
    button.className = `chat-option${selected ? " selected" : ""}`;
    button.textContent = guidanceOptionLabel(suggestion.id, session.language);
    button.dataset.suggestionId = suggestion.id;
    button.setAttribute("aria-expanded", String(selected));
    button.setAttribute("aria-controls", `guidance-widget-${suggestion.id}`);
    button.addEventListener("click", () => {
      state.activeSuggestionId = selected ? null : suggestion.id;
      renderGuidance(state.session, selected ? null : suggestion.id);
      if (selected) {
        section.querySelector(`[data-suggestion-id="${suggestion.id}"]`)?.focus();
      }
    });
    options.append(button);
  }
  panel.append(options);

  if (activeSuggestion) {
    panel.append(renderSuggestionWidget(activeSuggestion, session.language));
  }
  if (pendingTasks.length) {
    panel.append(renderTaskRemovalOptions(pendingTasks, session.language));
  }
  section.append(panel);
  conversation.scrollTop = conversation.scrollHeight;

  if (focusSuggestionId) {
    section.querySelector(`#guidance-widget-${focusSuggestionId} input`)?.focus();
  }
}

export function guidanceOptionLabel(id, language) {
  const labels = {
    it: {
      set_title: "Scegli un titolo",
      set_date: "Scegli una data",
      set_time: "Scegli un orario",
      set_location: "Aggiungi un luogo",
      set_duration: "Imposta la durata",
      add_task: "Descrivi attività prima o dopo",
      add_reminder: "Aggiungi un promemoria",
    },
    en: {
      set_title: "Choose a title",
      set_date: "Choose a date",
      set_time: "Choose a time",
      set_location: "Add a location",
      set_duration: "Set the duration",
      add_task: "Describe an activity before or after",
      add_reminder: "Add a reminder",
    },
  };
  return labels[language]?.[id] || id;
}

export function renderSuggestionWidget(suggestion, language) {
  const widget = document.createElement("section");
  widget.id = `guidance-widget-${suggestion.id}`;
  widget.className = `chat-guidance-widget suggestion-${suggestion.id}`;

  const heading = document.createElement("div");
  heading.className = "chat-widget-heading";
  const title = document.createElement("strong");
  title.textContent = suggestion.label;
  const close = document.createElement("button");
  close.type = "button";
  close.className = "button button-quiet chat-widget-close";
  close.textContent = language === "it" ? "Chiudi" : "Close";
  close.addEventListener("click", () => {
    state.activeSuggestionId = null;
    renderGuidance(state.session);
    sectionFocusGuidanceOption(suggestion.id);
  });
  heading.append(title, close);
  widget.append(heading);

  const form = document.createElement("form");
  form.className = "draft-suggestion";
  const saved = state.guidanceValues[suggestion.id] || {};
  const inputId = `guidance-input-${suggestion.id}`;
  const label = document.createElement("label");
  label.htmlFor = inputId;
  label.textContent = suggestion.label;
  const input = document.createElement("input");
  input.id = inputId;
  input.type = suggestion.input_type === "date" ? "date"
    : suggestion.input_type === "time" ? "time"
      : suggestion.input_type === "duration" || suggestion.input_type === "reminder" ? "number" : "text";
  input.placeholder = suggestion.placeholder || "";
  input.autocomplete = "off";
  input.required = true;
  input.value = saved.value || "";
  if (input.type === "number") {
    input.min = suggestion.input_type === "reminder" ? "0" : "1";
    input.step = "1";
  }
  label.append(input);
  form.append(label);

  let choiceSelect = null;
  if (["duration", "reminder", "task"].includes(suggestion.input_type)) {
    choiceSelect = document.createElement("select");
    const choices = suggestion.input_type === "task" ? suggestion.timings : suggestion.units;
    const selectLabel = suggestion.input_type === "task"
      ? (language === "it" ? "Quando" : "When")
      : (language === "it" ? "Unità" : "Unit");
    choiceSelect.setAttribute("aria-label", `${suggestion.label} · ${selectLabel.toLowerCase()}`);
    for (const choice of choices || []) {
      const option = document.createElement("option");
      option.value = choice.value;
      option.textContent = choice.label;
      choiceSelect.append(option);
    }
    if (saved.choice) choiceSelect.value = saved.choice;
    form.append(choiceSelect);
  }

  const rememberValue = () => {
    state.guidanceValues[suggestion.id] = {
      value: input.value,
      ...(choiceSelect ? { choice: choiceSelect.value } : {}),
    };
  };
  input.addEventListener("input", rememberValue);
  choiceSelect?.addEventListener("change", rememberValue);

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const value = input.value.trim();
    if (!value) return;
    let action;
    let display;
    if (suggestion.id === "set_title" || suggestion.id === "set_location") {
      action = { type: suggestion.id, value };
      display = `${suggestion.label}: ${value}`;
    } else if (suggestion.id === "set_date" || suggestion.id === "set_time") {
      action = { type: suggestion.id, value };
      display = `${suggestion.label}: ${value}`;
    } else if (suggestion.id === "set_duration" || suggestion.id === "add_reminder") {
      const amount = Number(value);
      const selected = suggestion.units.find((option) => option.value === choiceSelect?.value);
      if (!Number.isSafeInteger(amount) || amount < 0 || !selected || !Number.isSafeInteger(selected.minutes)) return;
      const minutes = amount * selected.minutes;
      if (!Number.isSafeInteger(minutes) || (suggestion.id === "set_duration" && minutes <= 0)) return;
      action = suggestion.id === "set_duration"
        ? { type: "set_duration", value: minutes }
        : { type: "add_reminder", minutes_before: minutes };
      display = `${suggestion.label}: ${suggestion.id === "set_duration"
        ? formatDuration(minutes, language)
        : formatReminder(minutes, language)}`;
    } else if (suggestion.id === "add_task") {
      const selected = suggestion.timings.find((option) => option.value === choiceSelect?.value);
      if (!selected) return;
      action = { type: "add_task", description: value, timing: selected.value };
      display = `${suggestion.label} (${selected.label.toLowerCase()}): ${value}`;
    }
    if (action) submitStructuredAction(action, display, suggestion.id);
  });

  const save = document.createElement("button");
  save.type = "submit";
  save.className = "button button-secondary";
  save.textContent = suggestion.submit_label;
  form.append(save);
  if (suggestion.clear_label) {
    const clear = document.createElement("button");
    clear.type = "button";
    clear.className = "button button-quiet";
    clear.textContent = suggestion.clear_label;
    clear.addEventListener("click", () => submitStructuredAction(
      { type: "clear_reminders" }, suggestion.clear_label, suggestion.id
    ));
    form.append(clear);
  }
  widget.append(form);
  return widget;
}

export function sectionFocusGuidanceOption(suggestionId) {
  const button = Array.from($("#chat-guidance").querySelectorAll("[data-suggestion-id]"))
    .find((option) => option.dataset.suggestionId === suggestionId);
  button?.focus();
}

export function defaultAssistantReply(session) {
  if (session.guidance?.suggestions?.length) {
    return session.language === "it"
      ? "Bozza aggiornata. Scegli un’opzione qui sotto oppure continua a scrivere in chat."
      : "Draft updated. Choose an option below or keep writing in the chat.";
  }
  return session.language === "it"
    ? "Bozza aggiornata. Puoi continuare a scrivere in chat per aggiungere altri dettagli."
    : "Draft updated. Keep writing in the chat to add more details.";
}

export function getPendingRemovalTasks(workflowState) {
  const pending = new Set(workflowState.pending_task_removal || []);
  return (workflowState.draft.tasks || []).filter((task) => pending.has(task.id));
}

export function renderTaskRemovalOptions(tasks, language) {
  const container = document.createElement("div");
  container.className = "task-removal-options";
  container.setAttribute("role", "group");
  container.setAttribute("aria-label", language === "it" ? "Attività da rimuovere" : "Activities to remove");
  const heading = document.createElement("p");
  heading.className = "task-removal-heading";
  heading.textContent = language === "it" ? "Scegli l’attività da rimuovere" : "Choose the activity to remove";
  container.append(heading);
  tasks.forEach((task, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "task-removal-option";
    button.disabled = state.busy;
    button.dataset.taskId = task.id;
    button.textContent = `${index + 1}. ${task.description}`;
    button.setAttribute("aria-label", language === "it" ? `Rimuovi attività: ${task.description}` : `Remove activity: ${task.description}`);
    button.addEventListener("click", () => {
      state.selectedTaskId = task.id;
      messageInput.value = `Rimuovi: ${task.description}`;
      $("#turn-form").requestSubmit();
    });
    container.append(button);
  });
  return container;
}
