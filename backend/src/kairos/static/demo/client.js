/** Browser-local API transport. No access to real API/provider endpoints. */
export class DemoClient {
  constructor(onStatus) {
    this.pending = new Map();
    this.worker = new Worker(new URL("./worker.js", import.meta.url), { type: "module" });
    this.ready = new Promise((resolve, reject) => {
      this.readyTimer = setTimeout(() => reject(new Error("Caricamento demo scaduto. Ricarica la pagina per riprovare.")), 120000);
      this.worker.onmessage = ({ data }) => {
        if (data.type === "status") onStatus(data.message);
        if (data.type === "ready") { clearTimeout(this.readyTimer); resolve(); }
        if (data.type === "fatal") { clearTimeout(this.readyTimer); reject(new Error(data.message)); }
        const job = this.pending.get(data.id);
        if (!job) return;
        if (data.type === "event") job.onEvent?.(data.event);
        if (data.type === "result" || data.type === "error") {
          clearTimeout(job.timer); this.pending.delete(data.id);
          if (data.type === "error") job.reject(new Error(data.message));
          else job.resolve(data.result);
        }
      };
      this.worker.onerror = () => {
        const error = new Error("Impossibile avviare la demo. Ricarica la pagina per riprovare.");
        clearTimeout(this.readyTimer); reject(error);
        for (const job of this.pending.values()) { clearTimeout(job.timer); job.reject(error); }
        this.pending.clear();
      };
    });
  }
  async request(operation, payload, sessionId, onEvent) {
    await this.ready;
    const id = crypto.randomUUID();
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id); reject(new Error("La demo non ha risposto. Crea una nuova sessione per riprovare."));
      }, 30000);
      this.pending.set(id, { resolve, reject, onEvent, timer });
      this.worker.postMessage({ id, operation, payload, session_id: sessionId });
    });
  }
  async createSession(payload) {
    return { body: await this.request("create_session", payload) };
  }
  async changeLanguage(sessionId, language) {
    return { body: await this.request("change_language", { language }, sessionId) };
  }
  async turn(sessionId, payload) {
    await this.ready;
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start: (controller) => {
        this.request("turn", payload, sessionId, ({ event, data }) => {
          controller.enqueue(encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`));
        }).then(() => controller.close(), error => controller.error(error));
      },
    });
    return new Response(stream, { headers: { "Content-Type": "text/event-stream", "X-Request-ID": crypto.randomUUID() } });
  }
}
