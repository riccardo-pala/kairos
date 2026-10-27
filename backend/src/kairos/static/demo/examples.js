/** Guided messages live inside the shared chat, not in a separate demo page. */
import { $, state } from "../ui/state.js";

export class ExampleMessages {
  constructor(resetSession, sendMessage) {
    this.resetSession = resetSession;
    this.sendMessage = sendMessage;
    this.examples = [];
    this.selected = null;
    this.next = 0;
  }
  reset(examples) { this.examples = examples; this.selected = null; this.next = 0; this.render(); }
  localize(examples) {
    const selectedId = this.selected?.id;
    this.examples = examples;
    this.selected = examples.find(example => example.id === selectedId) || null;
    this.render();
  }
  complete(message) {
    if (message && this.selected?.messages[this.next] === message) this.next += 1;
    this.render();
  }
  render() {
    const root = $("#demo-examples");
    root.replaceChildren(); root.classList.remove("hidden");
    const italian = state.session?.language === "it";
    const label = document.createElement("p");
    label.textContent = italian ? "Prova una conversazione guidata" : "Try a guided conversation";
    root.append(label);
    const options = document.createElement("div"); options.className = "demo-example-options";
    for (const example of this.examples) {
      const button = document.createElement("button"); button.type = "button";
      button.className = "chat-option"; button.textContent = example.label;
      button.disabled = state.busy;
      button.addEventListener("click", async () => {
        const session = await this.resetSession();
        if (!session) return;
        this.selected = example; this.next = 0;
        this.sendMessage(example.messages[0]);
      });
      options.append(button);
    }
    root.append(options);
    if (this.selected && this.next < this.selected.messages.length) {
      const next = document.createElement("button"); next.type = "button";
      next.className = "button button-secondary demo-next-message";
      next.textContent = `${italian ? "Invia" : "Send"}: ${this.selected.messages[this.next]}`;
      next.disabled = state.busy;
      next.addEventListener("click", () => this.sendMessage(this.selected.messages[this.next]));
      root.append(next);
    } else if (this.selected) {
      const done = document.createElement("p");
      done.textContent = italian ? "Esempio completato. Puoi continuare con i controlli della bozza." : "Example complete. Keep exploring with the draft controls.";
      root.append(done);
    }
  }
}
