import { tr } from "./i18n.js";
import { state, $, conversation, conversationEmpty, messageInput, sendButton, turnStatus } from "./state.js";

export function setStatus(element, message, kind = "") {
  element.textContent = message;
  element.classList.toggle("error", kind === "error");
}

export function setBusy(busy, message = "") {
  state.busy = busy;
  $("#create-session").disabled = busy;
  $("#language-select").disabled = busy;
  sendButton.disabled = busy || !state.session;
  messageInput.disabled = busy || !state.session;
  document.querySelectorAll(".task-removal-option").forEach((button) => { button.disabled = busy; });
  document.querySelectorAll(".chat-guidance button, .chat-guidance input, .chat-guidance select, #demo-examples button").forEach((control) => { control.disabled = busy; });
  turnStatus.classList.toggle("busy", busy);
  const label = turnStatus.querySelector("span:last-child");
  label.textContent = message || (busy ? tr("busy") : tr("waiting"));
  if (!busy && state.session) messageInput.focus();
}

export function addMessage(role, text, kind = "") {
  conversationEmpty.classList.add("hidden");
  const article = document.createElement("article");
  article.className = `message ${role}${kind ? ` ${kind}` : ""}`;
  const meta = document.createElement("p");
  meta.className = "message-meta";
  meta.textContent = role === "user" ? tr("you") : (kind === "error" ? tr("error") : kind === "progress" ? tr("progress") : "kAIros");
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.textContent = text;
  article.append(meta, bubble);
  conversation.insertBefore(article, $("#chat-guidance"));
  conversation.scrollTop = conversation.scrollHeight;
  return bubble;
}

export function setProgressMessage(message) {
  if (!state.progressNode) {
    state.progressNode = addMessage("assistant", message, "progress");
    return;
  }
  state.progressNode.textContent = message;
  conversation.scrollTop = conversation.scrollHeight;
}

export function clearProgressMessage() {
  state.progressNode?.parentElement.remove();
  state.progressNode = null;
}
