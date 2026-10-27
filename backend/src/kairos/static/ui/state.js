/** Shared UI state; contains no transport or provider logic. */
export const state = {
  session: null,
  client: null,
  language: "it",
  isDemo: false,
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

export const $ = (selector) => document.querySelector(selector);
export const conversation = $("#conversation");
export const conversationEmpty = $("#conversation-empty");
export const messageInput = $("#message-input");
export const sendButton = $("#send-message");
export const turnStatus = $("#turn-status");
