# Primo workflow: da una frase a una bozza di evento

Schema proposto dal coordinatore il 24 ottobre 2026, sulla base del [registro delle idee](../working/ideas.md). Il primo incremento è ora implementato nel backend: modelli Pydantic, workflow asincrono, provider simulato, adattatore Ollama e CLI. Lo stato operativo e i comandi sono nel [README](../../README.md). Salvataggio, notifiche, API e frontend restano incrementi successivi; lo schema seguente mostra anche queste tappe future.

## Obiettivo

Ricevere una frase in italiano o inglese e ottenere una bozza strutturata di evento, attività prima/dopo e promemoria. Il primo esercizio parte da testo; voce, salvataggio e notifiche sono incrementi successivi dello stesso flusso.

```mermaid
flowchart TD
    A["Testo IT/EN o futura trascrizione vocale"] --> B["LLM: estrazione della bozza"]
    B --> C["Python: validazione dei dati e del contesto temporale"]
    C --> D{"Mancano dati necessari o ci sono ambiguità?"}
    D -->|Sì| E["Domanda mirata e opzioni in app"]
    E --> B
    D -->|No| F["Scheda evento modificabile e scelta promemoria"]
    F --> G["Conferma e salvataggio: incremento successivo"]
    G --> H["Pianificazione avvisi: incremento successivo"]
```

Il ciclo mantiene la bozza precedente e applica le nuove risposte: non perde i dati già raccolti. I promemoria non specificati richiedono una scelta esplicita; fra le opzioni si propone anche di non riceverne. La conferma finale è una proposta di interazione da valutare.

## Dati da rappresentare

| Oggetto | Contenuto proposto |
| --- | --- |
| Evento in bozza | Titolo, data e ora, fuso orario di riferimento, luogo e durata quando disponibili |
| Attività collegata | Descrizione, relazione prima/dopo, eventuale scadenza esplicita |
| Promemoria | Momento assoluto oppure anticipo rispetto all'evento; zero o più dopo la scelta dell'utente |
| Stato del flusso | Bozza corrente, informazioni mancanti, domanda in attesa, pronto alla revisione |
| Contesto della richiesta | Istante di riferimento, lingua e fuso noti o da chiarire |

Una visita non autorizza a inferire diagnosi o istruzioni mediche. Una relazione prima/dopo non assegna automaticamente una scadenza precisa. Informazioni mancanti restano tali; il codice verifica date, durata e orari, e chiede chiarimenti quando necessari. L'istante di riferimento e il fuso sono forniti dall'applicazione, non inventati dal modello.

## Italiano e inglese

Requisiti confermati: entrambe le lingue fin dall'inizio e componenti interattivi dentro l'app; widget Home Android esclusi per ora.

Proposta: separare lingua dell'interfaccia, lingua della conversazione e fuso orario. Tradurre le stringhe statiche tramite risorse dell'app; usare gli stessi dati strutturati per entrambe le lingue. Date numeriche ambigue richiedono chiarimento quando il contesto non basta. La lingua non determina da sola il fuso orario.

Nel backend il contratto è ora implementato con `Language`, `MessageCatalog` e `LocalizedText`: le traduzioni sono indicizzate per codice lingua e la copertura è verificata all'avvio e per le domande generate dal modello. Per leggere una domanda si usa `state.question.text(context.language)`. Il registro `ToolRegistry` espone i tool disponibili e collega ciascuna scelta a schema e gestore: attualmente `update_event_draft` e `ask_event_clarification`. Il modello sceglie una chiamata per turno, mentre il codice conserva il controllo sull'esecuzione.

## Primo esercizio hands-on

1. Definire insieme i modelli Python della bozza e costruire due esempi equivalenti IT/EN senza chiamare un LLM.
2. Scrivere le validazioni di base e pochi test significativi: richiesta completa, dati mancanti, data ambigua, più promemoria e correzione di una bozza.
3. Collegare un singolo provider LLM per produrre la bozza; validarne sempre l'output prima di usarlo. La scelta fra locale e API cloud è ancora aperta.
4. Esporre il flusso via API e collegare una prima scheda mobile, poi aggiungere persistenza, notifiche e voce.

Il primo esercizio termina quando gli esempi equivalenti producono strutture equivalenti e i dati incompleti restano espliciti. Il provider LLM può essere sostituito con risposte fisse nei test delle regole; la qualità dell'estrazione reale va verificata separatamente.

L'utente mantiene la parte hands-on su Python e workflow; il coordinatore prepara esercizi, spiegazioni, review e frontend. Confini iniziali proposti per il modello: nessuna azione esterna durante l'estrazione, output validato e numero limitato di passaggi. Guardrail e flussi completi sono descritti nelle [proposte di prodotto](../working/product-proposals.md).

## Scelte aperte prima dell'integrazione completa

- Provider LLM iniziale e risorse disponibili per un eventuale modello locale.
- Conferma dello stack discusso: Flutter, FastAPI/Pydantic, SQLite.
- Eventi conservati solo in Kairos oppure sincronizzati con un calendario esterno.
- Dove pianificare le notifiche e quale comportamento garantire quando backend o telefono non sono raggiungibili.
