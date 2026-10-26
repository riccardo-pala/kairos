"use strict";

const state = {
  session: null,
  busy: false,
  assistantNode: null,
  assistantText: "",
  progressNode: null,
  requestId: "",
  selectedTaskId: null,
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
  meta.textContent = role === "user" ? "Tu" : (kind === "error" ? "Errore del workflow" : kind === "progress" ? "Stato del turno" : "Kairos");
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.textContent = text;
  article.append(meta, bubble);
  conversation.append(article);
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

function formatValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) {
    if (!value.length) return "Nessuna";
    return value.map((item) => {
      if (typeof item === "object" && item !== null) {
        if ("description" in item) return `${item.description} (${item.timing})`;
        if ("minutes_before" in item) return `${item.minutes_before} min prima`;
      }
      return String(item);
    }).join("\n");
  }
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  if (Number.isInteger(value) && value > 0 && value < 10000) return `${value} min`;
  return String(value);
}

function renderSession(session) {
  state.session = session;
  $("#session-id").textContent = session.id;
  $("#draft-status").textContent = session.state.status === "ready_for_review" ? "Pronta da rivedere" : "In raccolta";
  $("#draft-status").classList.toggle("ready", session.state.status === "ready_for_review");
  const question = $("#current-question");
  question.textContent = session.state.question || "";
  question.classList.toggle("hidden", !session.state.question);
  renderTaskRemovalOptions(session.state);
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
    element.textContent = formatValue(values[element.dataset.field]);
  });
  sendButton.disabled = state.busy;
  messageInput.disabled = state.busy;
  if (!state.busy) messageInput.focus();
}

function renderTaskRemovalOptions(workflowState) {
  const container = $("#task-removal-options");
  container.replaceChildren();
  const pending = new Set(workflowState.pending_task_removal || []);
  const tasks = (workflowState.draft.tasks || []).filter((task) => pending.has(task.id));
  if (!tasks.length) {
    container.classList.add("hidden");
    return;
  }
  tasks.forEach((task, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "task-removal-option";
    button.disabled = state.busy;
    button.dataset.taskId = task.id;
    button.textContent = `${index + 1}. ${task.description}`;
    button.addEventListener("click", () => {
      state.selectedTaskId = task.id;
      messageInput.value = `Rimuovi: ${task.description}`;
      $("#turn-form").requestSubmit();
    });
    container.append(button);
  });
  container.classList.remove("hidden");
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
    clearProgressMessage();
    state.requestId = "";
    conversation.replaceChildren(conversationEmpty);
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
  addMessage("user", message);
  messageInput.value = "";
  state.assistantText = "";
  state.assistantNode = null;
  clearProgressMessage();
  state.requestId = "";
  setBusy(true, "Invio messaggio…");
  turnStatus.classList.remove("error");
  const events = [];
  renderRawEvents(events);
  $("#request-id-badge").textContent = "in attesa";
  let assistantBubble = null;
  try {
    const response = await fetch(`/sessions/${encodeURIComponent(state.session.id)}/turn`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ message, ...(taskId ? { task_id: taskId } : {}) }),
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
      if (data.session) renderSession(data.session);
      const question = data.session?.state?.question;
      let bubble = getBubble();
      if (bubble && question && !state.assistantText.includes(question)) {
        state.assistantText += `${state.assistantText ? "\n\n" : ""}${question}`;
        bubble.textContent = state.assistantText;
      } else if (!bubble) addMessage("assistant", question || "La bozza è aggiornata.");
      setBusy(false, data.session?.state?.status === "ready_for_review" ? "Bozza pronta" : "Bozza aggiornata");
    }
    if (name === "error") {
      terminal = true;
      failed = true;
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
