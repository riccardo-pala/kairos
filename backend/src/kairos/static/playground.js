"use strict";

const state = {
  session: null,
  busy: false,
  assistantNode: null,
  assistantText: "",
  progressNode: null,
  requestId: "",
  selectedTaskId: null,
  activeSuggestionId: null,
  guidanceValues: {},
  pendingSuggestionId: null,
};

const $ = (selector) => document.querySelector(selector);
const conversation = $("#conversation");
const conversationEmpty = $("#conversation-empty");
const messageInput = $("#message-input");
const sendButton = $("#send-message");
const turnStatus = $("#turn-status");

function setStatus(element, message, kind = "") {
  element.textContent = message;
  element.classList.toggle("error", kind === "error");
}

function setBusy(busy, message = "") {
  state.busy = busy;
  $("#create-session").disabled = busy;
  sendButton.disabled = busy || !state.session;
  messageInput.disabled = busy || !state.session;
  document.querySelectorAll(".task-removal-option").forEach((button) => { button.disabled = busy; });
  document.querySelectorAll(".chat-guidance button, .chat-guidance input, .chat-guidance select").forEach((control) => { control.disabled = busy; });
  turnStatus.classList.toggle("busy", busy);
  const label = turnStatus.querySelector("span:last-child");
  label.textContent = message || (busy ? "In corso…" : "In attesa");
  if (!busy && state.session) messageInput.focus();
}

function addMessage(role, text, kind = "") {
  conversationEmpty.classList.add("hidden");
  const article = document.createElement("article");
  article.className = `message ${role}${kind ? ` ${kind}` : ""}`;
  const meta = document.createElement("p");
  meta.className = "message-meta";
  meta.textContent = role === "user" ? "Tu" : (kind === "error" ? "Errore del workflow" : kind === "progress" ? "Stato del turno" : "kAIros");
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.textContent = text;
  article.append(meta, bubble);
  conversation.insertBefore(article, $("#chat-guidance"));
  conversation.scrollTop = conversation.scrollHeight;
  return bubble;
}

function setProgressMessage(message) {
  if (!state.progressNode) {
    state.progressNode = addMessage("assistant", message, "progress");
    return;
  }
  state.progressNode.textContent = message;
  conversation.scrollTop = conversation.scrollHeight;
}

function clearProgressMessage() {
  state.progressNode?.parentElement.remove();
  state.progressNode = null;
}

function formatDuration(totalMinutes, language = state.session?.language || "it") {
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

function formatReminder(minutes, language = state.session?.language || "it") {
  if (minutes === 0) return language === "it" ? "All’inizio dell’impegno" : "At the start of the event";
  return `${formatDuration(minutes, language)} ${language === "it" ? "prima" : "before"}`;
}

function formatValue(value, field) {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) {
    if (!value.length) return "Nessuna";
    return value.map((item) => {
      if (typeof item === "object" && item !== null) {
        if ("description" in item) return `${item.description} (${item.timing})`;
        if ("minutes_before" in item) return formatReminder(item.minutes_before);
      }
      return String(item);
    }).join("\n");
  }
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  if (field === "duration_minutes") return formatDuration(value);
  return String(value);
}

function renderSession(session) {
  state.session = session;
  $("#session-id").textContent = session.id;
  $("#draft-status").textContent = session.state.status === "ready_for_review" ? "Pronta da rivedere" : "In raccolta";
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

function renderGuidance(session, focusSuggestionId = null) {
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

function guidanceOptionLabel(id, language) {
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

function renderSuggestionWidget(suggestion, language) {
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

function sectionFocusGuidanceOption(suggestionId) {
  const button = Array.from($("#chat-guidance").querySelectorAll("[data-suggestion-id]"))
    .find((option) => option.dataset.suggestionId === suggestionId);
  button?.focus();
}

function defaultAssistantReply(session) {
  if (session.guidance?.suggestions?.length) {
    return session.language === "it"
      ? "Bozza aggiornata. Scegli un’opzione qui sotto oppure continua a scrivere in chat."
      : "Draft updated. Choose an option below or keep writing in the chat.";
  }
  return session.language === "it"
    ? "Bozza aggiornata. Puoi continuare a scrivere in chat per aggiungere altri dettagli."
    : "Draft updated. Keep writing in the chat to add more details.";
}

function getPendingRemovalTasks(workflowState) {
  const pending = new Set(workflowState.pending_task_removal || []);
  return (workflowState.draft.tasks || []).filter((task) => pending.has(task.id));
}

function renderTaskRemovalOptions(tasks, language) {
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

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : `Richiesta non riuscita (${response.status})`;
    throw new Error(detail);
  }
  return { body, response };
}

function renderRawEvents(events) {
  const list = $("#raw-events");
  list.replaceChildren();
  if (!events.length) {
    const item = document.createElement("li");
    item.className = "muted-empty";
    item.textContent = "Nessun evento ricevuto.";
    list.append(item);
    return;
  }
  for (const item of events) {
    const row = document.createElement("li");
    const name = document.createElement("span");
    name.className = "event-name";
    name.textContent = item.name;
    const raw = document.createElement("pre");
    raw.textContent = JSON.stringify(item.data, null, 2);
    row.append(name, raw);
    list.append(row);
  }
}

function recordSseEvent(name, data, events) {
  events.push({ name, data });
  renderRawEvents(events);
}

function parseSseBlock(block, onEvent) {
  let name = "message";
  const dataLines = [];
  for (const line of block.split(/\r?\n/)) {
    if (line.startsWith("event:")) name = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
  }
  if (!dataLines.length) return;
  const raw = dataLines.join("\n");
  let data;
  try { data = JSON.parse(raw); } catch { data = { raw }; }
  onEvent(name, data);
}

async function createSession() {
  const button = $("#create-session");
  button.disabled = true;
  turnStatus.classList.remove("error");
  setBusy(true, "Creo sessione…");
  try {
    const { body } = await requestJson("/sessions", {
      method: "POST",
      body: JSON.stringify({
        language: $("#language-select").value,
        timezone: $("#timezone-input").value.trim(),
      }),
    });
    state.session = body;
    state.assistantNode = null;
    state.assistantText = "";
    state.selectedTaskId = null;
    state.activeSuggestionId = null;
    state.guidanceValues = {};
    state.pendingSuggestionId = null;
    clearProgressMessage();
    state.requestId = "";
    conversation.replaceChildren(conversationEmpty, $("#chat-guidance"));
    $("#chat-guidance").replaceChildren();
    $("#chat-guidance").classList.add("hidden");
    conversationEmpty.classList.add("hidden");
    addMessage("assistant", `Sessione creata. ${body.language === "it" ? "Descrivi l’impegno che vuoi preparare." : "Describe the event you want to draft."}`);
    renderSession(body);
    $("#raw-events").replaceChildren();
    $("#request-id-badge").textContent = "nessun turno";
    $("#request-filter").value = "";
    loadDiagnostics();
    setBusy(false, "Sessione pronta");
  } catch (error) {
    turnStatus.classList.add("error");
    setBusy(false, "Creazione non riuscita");
    addMessage("assistant", error.message, "error");
  } finally {
    button.disabled = state.busy;
  }
}

async function sendTurn(event) {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (!state.session || !message || state.busy) return;
  const taskId = state.selectedTaskId;
  state.selectedTaskId = null;
  messageInput.value = "";
  await submitTurn({ message, ...(taskId ? { task_id: taskId } : {}) }, message);
}

function submitStructuredAction(action, displayMessage, suggestionId) {
  if (!state.session || state.busy) return;
  state.pendingSuggestionId = suggestionId || null;
  return submitTurn({ action: action }, displayMessage);
}

async function submitTurn(requestBody, displayMessage) {
  if (!state.session || state.busy) return;
  addMessage("user", displayMessage);
  state.assistantText = "";
  state.assistantNode = null;
  clearProgressMessage();
  state.requestId = "";
  setBusy(true, requestBody.message ? "Invio messaggio…" : "Aggiorno la bozza…");
  turnStatus.classList.remove("error");
  const events = [];
  renderRawEvents(events);
  $("#request-id-badge").textContent = "in attesa";
  let assistantBubble = null;
  try {
    const response = await fetch(`/sessions/${encodeURIComponent(state.session.id)}/turn`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(requestBody),
    });
    state.requestId = response.headers.get("X-Request-ID") || "";
    $("#request-id-badge").textContent = state.requestId || "ID non disponibile";
    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      throw new Error(errorBody.detail || `Richiesta non riuscita (${response.status})`);
    }
    if (!response.body) throw new Error("Il browser non ha ricevuto uno stream SSE.");

    // Model text gets a bubble only when it contains visible content.
    const result = await consumeTurnWithLazyText(response, events, () => assistantBubble, (bubble) => { assistantBubble = bubble; });
    if (result) {
      turnStatus.classList.add("error");
      $("#request-filter").value = state.requestId;
      await loadDiagnostics(state.requestId);
    } else {
      $("#request-filter").value = state.requestId;
      await loadDiagnostics(state.requestId);
    }
  } catch (error) {
    state.pendingSuggestionId = null;
    clearProgressMessage();
    if (assistantBubble) {
      assistantBubble.textContent = error.message;
      assistantBubble.parentElement.classList.add("error");
    } else addMessage("assistant", error.message, "error");
    turnStatus.classList.add("error");
    setBusy(false, "Turno non completato");
    $("#request-filter").value = state.requestId;
    await loadDiagnostics(state.requestId);
  } finally {
    messageInput.focus();
  }
}

async function consumeTurnWithLazyText(response, events, getBubble, setBubble) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let terminal = false;
  let failed = false;
  const dispatch = (name, data) => {
    recordSseEvent(name, data, events);
    if (name === "progress") {
      const message = data.message || "In corso…";
      setBusy(true, message);
      setProgressMessage(message);
    }
    if (name === "text") {
      const chunk = data.text || "";
      if (!state.assistantText && !chunk.trim()) return;
      clearProgressMessage();
      let bubble = getBubble();
      if (!bubble) {
        bubble = addMessage("assistant", "");
        setBubble(bubble);
      }
      state.assistantText += chunk;
      bubble.textContent = state.assistantText;
      conversation.scrollTop = conversation.scrollHeight;
    }
    if (name === "completed") {
      terminal = true;
      clearProgressMessage();
      if (state.pendingSuggestionId) {
        delete state.guidanceValues[state.pendingSuggestionId];
        state.activeSuggestionId = null;
        state.pendingSuggestionId = null;
      }
      if (data.session) renderSession(data.session);
      const question = data.session?.state?.question;
      let bubble = getBubble();
      if (bubble && question && !state.assistantText.includes(question)) {
        state.assistantText += `${state.assistantText ? "\n\n" : ""}${question}`;
        bubble.textContent = state.assistantText;
      } else if (!bubble) addMessage("assistant", question || defaultAssistantReply(data.session));
      setBusy(false, data.session?.state?.status === "ready_for_review" ? "Bozza pronta" : "Bozza aggiornata");
    }
    if (name === "error") {
      terminal = true;
      failed = true;
      state.pendingSuggestionId = null;
      clearProgressMessage();
      let bubble = getBubble();
      if (bubble) {
        bubble.textContent = data.message || "Il turno non è stato completato.";
        bubble.parentElement.classList.add("error");
      } else addMessage("assistant", data.message || "Il turno non è stato completato.", "error");
      turnStatus.classList.add("error");
      setBusy(false, "Turno non completato");
    }
  };
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    let boundary;
    while ((boundary = buffer.search(/\r?\n\r?\n/)) !== -1) {
      const match = buffer.slice(boundary).match(/^\r?\n\r?\n/)[0];
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + match.length);
      parseSseBlock(block, dispatch);
    }
    if (done) break;
  }
  if (buffer.trim()) parseSseBlock(buffer, dispatch);
  if (!terminal) throw new Error("Lo stream si è interrotto prima dell’evento finale.");
  return failed;
}

async function loadProfiles() {
  const select = $("#provider-select");
  const button = $("#activate-provider");
  setStatus($("#provider-status"), "Carico i profili disponibili…");
  select.disabled = true;
  button.disabled = true;
  try {
    const { body: profiles } = await requestJson("/admin/provider-profiles");
    select.replaceChildren();
    if (!profiles.length) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "Nessun profilo disponibile";
      select.append(option);
      setStatus($("#provider-status"), "Nessun profilo trovato.", "error");
      return;
    }
    for (const profile of profiles) {
      const option = document.createElement("option");
      option.value = profile.id;
      option.textContent = `${profile.name}${profile.active ? " · attivo" : ""}`;
      option.dataset.active = String(profile.active);
      select.append(option);
    }
    select.value = profiles.find((profile) => profile.active)?.id || profiles[0].id;
    select.disabled = false;
    button.disabled = false;
    const active = profiles.find((profile) => profile.active);
    setStatus($("#provider-status"), active ? `In uso: ${active.name}` : "Nessun provider attivo.");
  } catch (error) {
    select.replaceChildren();
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "Impossibile caricare i profili";
    select.append(option);
    setStatus($("#provider-status"), error.message, "error");
  }
}

async function activateProvider() {
  const profileId = $("#provider-select").value;
  if (!profileId) return;
  const button = $("#activate-provider");
  button.disabled = true;
  setStatus($("#provider-status"), "Attivo il provider…");
  try {
    const { body } = await requestJson(`/admin/provider-profiles/${encodeURIComponent(profileId)}/activate`, { method: "POST" });
    setStatus($("#provider-status"), `Attivo: ${body.name}. Verrà usato dal prossimo turno.`);
    await loadProfiles();
  } catch (error) {
    setStatus($("#provider-status"), error.message, "error");
    button.disabled = false;
  }
}

function renderDiagnostics(items) {
  const container = $("#diagnostic-logs");
  container.replaceChildren();
  if (!items.length) {
    const empty = document.createElement("p");
    empty.className = "muted-empty";
    empty.textContent = "Nessun log corrisponde al filtro. I log sono locali al processo e hanno una capacità limitata.";
    container.append(empty);
    return;
  }
  for (const item of items) {
    const entry = document.createElement("details");
    entry.className = "diagnostic-entry";
    const summary = document.createElement("summary");
    const event = document.createElement("span");
    event.className = "log-event";
    event.textContent = item.event || "log";
    const timestamp = document.createElement("time");
    timestamp.className = "log-time";
    timestamp.textContent = item.timestamp || "";
    summary.append(event, timestamp);
    const pre = document.createElement("pre");
    pre.className = "log-json";
    pre.textContent = JSON.stringify(item, null, 2);
    entry.append(summary, pre);
    container.append(entry);
  }
}

async function loadDiagnostics(requestId = $("#request-filter").value.trim()) {
  const status = $("#diagnostics-status");
  setStatus(status, "Carico log locali…");
  const query = requestId ? `?request_id=${encodeURIComponent(requestId)}` : "";
  try {
    const { body } = await requestJson(`/admin/diagnostics${query}`);
    renderDiagnostics(body.items || []);
    setStatus(status, `${(body.items || []).length} eventi${requestId ? " per questo turno" : " recenti"}`);
  } catch (error) {
    renderDiagnostics([]);
    setStatus(status, error.message, "error");
  }
}

async function clearDiagnostics() {
  if (!window.confirm("Svuotare i log diagnostici in memoria per questo processo?")) return;
  try {
    await requestJson("/admin/diagnostics", { method: "DELETE" });
    renderDiagnostics([]);
    setStatus($("#diagnostics-status"), "Log svuotati.");
  } catch (error) {
    setStatus($("#diagnostics-status"), error.message, "error");
  }
}

$("#create-session").addEventListener("click", createSession);
$("#turn-form").addEventListener("submit", sendTurn);
messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    $("#turn-form").requestSubmit();
  }
});
$("#refresh-profiles").addEventListener("click", loadProfiles);
$("#activate-provider").addEventListener("click", activateProvider);
$("#refresh-diagnostics").addEventListener("click", () => loadDiagnostics());
$("#apply-filter").addEventListener("click", () => loadDiagnostics());
$("#request-filter").addEventListener("keydown", (event) => {
  if (event.key === "Enter") loadDiagnostics();
});
$("#clear-diagnostics").addEventListener("click", clearDiagnostics);

loadProfiles();
loadDiagnostics("");
