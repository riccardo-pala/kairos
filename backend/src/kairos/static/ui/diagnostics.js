import { state, $, conversation, conversationEmpty, messageInput, sendButton, turnStatus } from "./state.js";
import { setStatus } from "./messages.js";

export function renderRawEvents(events) {
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

export function recordSseEvent(name, data, events) {
  events.push({ name, data });
  renderRawEvents(events);
}

export async function loadProfiles() {
  const select = $("#provider-select");
  const button = $("#activate-provider");
  setStatus($("#provider-status"), "Carico i profili disponibili…");
  select.disabled = true;
  button.disabled = true;
  try {
    const { body: profiles } = await state.client.requestJson("/admin/provider-profiles");
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

export async function activateProvider() {
  const profileId = $("#provider-select").value;
  if (!profileId) return;
  const button = $("#activate-provider");
  button.disabled = true;
  setStatus($("#provider-status"), "Attivo il provider…");
  try {
    const { body } = await state.client.requestJson(`/admin/provider-profiles/${encodeURIComponent(profileId)}/activate`, { method: "POST" });
    setStatus($("#provider-status"), `Attivo: ${body.name}. Verrà usato dal prossimo turno.`);
    await loadProfiles();
  } catch (error) {
    setStatus($("#provider-status"), error.message, "error");
    button.disabled = false;
  }
}

export function renderDiagnostics(items) {
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

export async function loadDiagnostics(requestId = $("#request-filter").value.trim()) {
  const status = $("#diagnostics-status");
  setStatus(status, "Carico log locali…");
  const query = requestId ? `?request_id=${encodeURIComponent(requestId)}` : "";
  try {
    const { body } = await state.client.requestJson(`/admin/diagnostics${query}`);
    renderDiagnostics(body.items || []);
    setStatus(status, `${(body.items || []).length} eventi${requestId ? " per questo turno" : " recenti"}`);
  } catch (error) {
    renderDiagnostics([]);
    setStatus(status, error.message, "error");
  }
}

export async function clearDiagnostics() {
  if (!window.confirm("Svuotare i log diagnostici in memoria per questo processo?")) return;
  try {
    await state.client.requestJson("/admin/diagnostics", { method: "DELETE" });
    renderDiagnostics([]);
    setStatus($("#diagnostics-status"), "Log svuotati.");
  } catch (error) {
    setStatus($("#diagnostics-status"), error.message, "error");
  }
}


export function bindDiagnostics() {
  $("#refresh-profiles").addEventListener("click", loadProfiles);
  $("#activate-provider").addEventListener("click", activateProvider);
  $("#refresh-diagnostics").addEventListener("click", () => loadDiagnostics());
  $("#apply-filter").addEventListener("click", () => loadDiagnostics());
  $("#request-filter").addEventListener("keydown", event => { if (event.key === "Enter") loadDiagnostics(); });
  $("#clear-diagnostics").addEventListener("click", clearDiagnostics);
  loadProfiles(); loadDiagnostics("");
}
export function resetDiagnostics() {
  $("#raw-events").replaceChildren(); $("#request-id-badge").textContent = "nessun turno";
  $("#request-filter").value = ""; loadDiagnostics();
}
export function requestBadge(text) { $("#request-id-badge").textContent = text; }
export async function updateDiagnostics(id) { $("#request-filter").value = id; await loadDiagnostics(id); }
