/** HTTP transport for the real, local playground. */
export class HttpClient {
  async requestJson(url, options = {}) {
    const response = await fetch(url, {
      ...options, headers: { "Content-Type": "application/json", ...options.headers },
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : `Richiesta non riuscita (${response.status})`);
    return { body, response };
  }
  createSession(payload) {
    return this.requestJson("/sessions", { method: "POST", body: JSON.stringify(payload) });
  }
  changeLanguage(sessionId, language) {
    return this.requestJson(`/sessions/${encodeURIComponent(sessionId)}/language`, {
      method: "PATCH", body: JSON.stringify({ language }),
    });
  }
  turn(sessionId, payload) {
    return fetch(`/sessions/${encodeURIComponent(sessionId)}/turn`, {
      method: "POST", headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(payload),
    });
  }
}
