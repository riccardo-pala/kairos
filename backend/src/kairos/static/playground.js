/** Application controller shared by real and Pages playgrounds. */
import { state, $, conversation, conversationEmpty, messageInput, sendButton, turnStatus } from "./ui/state.js";
import { setBusy, addMessage, setProgressMessage, clearProgressMessage } from "./ui/messages.js";
import { configureDraft, renderSession, defaultAssistantReply } from "./ui/draft.js";

import { tr, applyUiLanguage, populateTimezones } from "./ui/i18n.js";

let diagnostics = null;
let examplesView = null;

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
  setBusy(true, tr("creating"));
  try {
    const { body } = await state.client.createSession({
      language: $("#language-select").value,
      timezone: $("#timezone-select").value.trim(),
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
    addMessage("assistant", tr("newSession"));
    renderSession(body);
    diagnostics?.resetDiagnostics();
    examplesView?.reset(body.demo_examples || []);
    setBusy(false, tr("sessionReady"));
    return body;
  } catch (error) {
    turnStatus.classList.add("error");
    setBusy(false, tr("createError"));
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
  setBusy(true, requestBody.message ? tr("sending") : tr("updating"));
  turnStatus.classList.remove("error");
  const events = [];
  diagnostics?.renderRawEvents(events);
  diagnostics?.requestBadge("in attesa");
  let assistantBubble = null;
  try {
    const response = await state.client.turn(state.session.id, requestBody);
    state.requestId = response.headers.get("X-Request-ID") || "";
    diagnostics?.requestBadge(state.requestId || "ID non disponibile");
    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      throw new Error(errorBody.detail || `Richiesta non riuscita (${response.status})`);
    }
    if (!response.body) throw new Error("Il browser non ha ricevuto uno stream SSE.");

    // Model text gets a bubble only when it contains visible content.
    const result = await consumeTurnWithLazyText(response, events, () => assistantBubble, (bubble) => { assistantBubble = bubble; });
    if (result) turnStatus.classList.add("error");
    else examplesView?.complete(requestBody.message);
    await diagnostics?.updateDiagnostics(state.requestId);
  } catch (error) {
    state.pendingSuggestionId = null;
    clearProgressMessage();
    if (assistantBubble) {
      assistantBubble.textContent = error.message;
      assistantBubble.parentElement.classList.add("error");
    } else addMessage("assistant", error.message, "error");
    turnStatus.classList.add("error");
    setBusy(false, tr("turnError"));
    await diagnostics?.updateDiagnostics(state.requestId);
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
    diagnostics?.recordSseEvent(name, data, events);
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
      setBusy(false, data.session?.state?.status === "ready_for_review" ? tr("ready") : tr("updated"));
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
      setBusy(false, tr("turnError"));
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


$("#language-select").addEventListener("change", async () => {
  const previous = state.language;
  state.language = $("#language-select").value;
  applyUiLanguage(); populateTimezones();
  if (!state.session) return;
  setBusy(true, tr("changingLanguage"));
  try {
    const { body } = await state.client.changeLanguage(state.session.id, state.language);
    renderSession(body);
    examplesView?.localize(body.demo_examples || []);
  } catch (error) {
    state.language = previous; $("#language-select").value = previous; applyUiLanguage();
    addMessage("assistant", error.message, "error");
  } finally { setBusy(false, tr("updated")); }
});

$("#create-session").addEventListener("click", createSession);
$("#turn-form").addEventListener("submit", sendTurn);
messageInput.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); $("#turn-form").requestSubmit(); }
});
configureDraft(submitStructuredAction);

async function initialize() {
  $("#create-session").disabled = true;
  try {
    const response = await fetch(new URL("./playground-config.json", import.meta.url));
    if (!response.ok) throw new Error("Configurazione del playground non disponibile.");
    const config = await response.json();
    if (!["live", "demo"].includes(config.mode)) throw new Error("Modalità playground non valida.");
    state.isDemo = config.mode === "demo";
    state.language = $("#language-select").value;
    populateTimezones(); applyUiLanguage();
    if (state.isDemo) {
      document.body.dataset.mode = "demo";
      document.querySelectorAll("[data-live-only]").forEach(node => node.remove());
      $("#environment-label").textContent = "Demo simulata";
      $("#demo-notice").classList.remove("hidden");
      const { DemoClient } = await import("./demo/client.js");
      const { ExampleMessages } = await import("./demo/examples.js");
      examplesView = new ExampleMessages(createSession, message => {
        messageInput.value = message; $("#turn-form").requestSubmit();
      });
      state.client = new DemoClient(message => {
        setBusy(true, message); $("#demo-runtime-status").textContent = message;
      });
      setBusy(true, tr("demoLoading"));
      await state.client.ready;
      $("#demo-runtime-status").textContent = tr("demoReady");
      setBusy(false, "Demo pronta");
    } else {
      const { HttpClient } = await import("./clients/http.js");
      state.client = new HttpClient();
      diagnostics = await import("./ui/diagnostics.js");
      diagnostics.bindDiagnostics();
      setBusy(false);
    }
  } catch (error) {
    turnStatus.classList.add("error");
    setBusy(false, "Avvio non riuscito");
    $("#create-session").disabled = true;
    addMessage("assistant", error.message, "error");
    if (state.isDemo) $("#demo-runtime-status").textContent = error.message;
  }
}
initialize();
