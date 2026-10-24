# Registro delle idee — Kairos

Questo documento raccoglie le idee e le decisioni emerse per il progetto. Le proposte non approvate restano marcate come ipotesi; le questioni aperte non vanno considerate decisioni.

## Idee esplicite dell’utente

- **Data: 24 ottobre 2026 — Prodotto:** app per persone che procrastinano.
- **Data: 24 ottobre 2026 — Nome e filosofia:** “Kairos” richiama il “momento opportuno”. L’idea è non rimandare perché *ora è il momento opportuno*; tutte le funzionalità dovranno seguire questa filosofia.
- **Provenienza:** prima idea esplicita dell’utente, riportata nel contesto di avvio del progetto.

## Requisiti proposti per v1 — idee esplicite dell’utente

Questi sono casi d’uso e capacità proposti dall’utente per la prima versione; i dettagli non specificati restano aperti.

1. **Creazione di eventi e attività tramite conversazione vocale o scritta.** L’utente può descrivere un impegno (per esempio una visita medica il 31 ottobre alle 14:30, con luogo, durata, attività da svolgere prima e attività dopo). L’assistente estrae le informazioni strutturate e crea l’evento con le attività collegate prima e dopo. L’esempio è illustrativo: non va convertito in un evento reale e non autorizza a inventare anno, durata o luogo. Se l’utente non indica quando desidera un promemoria, l’assistente lo chiede. Per ciascun evento si possono impostare N promemoria.
2. **Interazione semplice e flessibile.** Il testo non deve essere obbligatorio: l’utente può interagire tramite voce, pulsanti o componenti interattivi dentro l’app (widget). I widget della schermata Home Android sono esclusi per ora.
3. **Contesto personale accumulato.** L’assistente dovrebbe conoscere progressivamente l’utente e conservare le informazioni essenziali che aiutano a personalizzare l’assistenza.
4. **Possibile onboarding guidato.** Si può valutare un avvio guidato con pulsanti, tag e selezioni, lasciando facoltativo l’inserimento manuale e senza rendere obbligatorio il testo.
5. **Supporto multilingua fin dall’inizio.** Le lingue iniziali richieste sono inglese e italiano.

### Chiarimento esplicito sui widget

- Per “widget” si intendono componenti interattivi dentro l’app.
- I widget della schermata Home Android sono esclusi per ora.

## Idee future — idee esplicite dell’utente

- **Lista della spesa per una ricetta:** in precedenza proposta tra i requisiti v1, ora rimossa dalla prima POC per evitare un’accozzaglia di funzionalità. Da conservare come possibilità futura e rivalutare per capire come integrarla in modo sensato con un’app per persone che procrastinano. L’idea originaria prevedeva una lista modificabile con articoli ricorrenti e acquisti una tantum distinti.
- **Feedback su bug e miglioramenti:** sezione in cui l’utente può segnalare bug o proporre miglioramenti; un agente raccoglie, riordina, struttura e filtra i feedback in base alla loro utilità.
- **Guardrail dei modelli:** l’utente li considera molto importanti. La collocazione temporale indicata dall’utente è “pro futuro”.

## Proposta del coordinatore — da valutare

- Anticipare i guardrail dei modelli fin dalla prima versione, pur avendo l’utente indicato il tema come pro futuro. È una proposta del coordinatore, non una decisione dell’utente.

## Contesto di progetto riportato

- App mobile di assistente personale basata su LLM.
- Android come prima piattaforma; iOS e web sono da valutare.
- Progetto didattico in Python, con integrazione agentica e workflow.
- L’utente vuole partecipare attivamente e seguire da vicino il lavoro.
- Il frontend è principalmente affidato al coordinatore.
- **Preferenza di collaborazione esplicita dell’utente:** procedere più spediti con le implementazioni e fermarsi sulle spiegazioni dei passaggi critici, in particolare workflow, chiamate ai tool e integrazione LLM. L’utente non vuole essere guidato manualmente su ogni dettaglio di base. Questa preferenza non cambia il carattere didattico e hands-on del progetto.

Questi punti sono contesto fornito dal coordinatore per avviare il registro; non aggiungono requisiti di prodotto oltre a quelli esplicitamente attribuiti all’utente sopra.

## Ipotesi architetturali discusse — non approvate

- Flutter per il client.
- FastAPI e Pydantic per il backend.
- SQLite come archivio iniziale.
- Provider LLM sostituibile.
- Partenza in locale, con costi contenuti o gratuiti.

**Stato:** opzioni discusse dal coordinatore, nessuna approvata dall’utente. Non trattarle come vincoli o decisioni finché non confermate.

## Stato implementativo iniziale — verificato dal coordinatore

- Workflow per la bozza di evento asincrono.
- Patch validate tramite il tool `update_event_draft`.
- Provider simulato.
- Adattatore Ollama opzionale.
- CLI.

Questi elementi descrivono implementazioni iniziali verificate dal coordinatore; non costituiscono una decisione di adottare definitivamente Ollama. Al momento della verifica non risultavano ancora implementate API, persistenza, notifiche o UI.

## Decisioni

- Nessuna decisione architetturale o di implementazione definitiva approvata registrata al momento. Le implementazioni iniziali sopra elencate sono stato di avanzamento, non una scelta definitiva di stack o provider.
- La filosofia esplicita dell’utente è il riferimento per valutare le funzionalità: favorire il momento opportuno e contrastare il rimandare.
- La lista della spesa è esclusa dalla prima POC e conservata come idea futura, da rivalutare per una possibile integrazione coerente con il prodotto. Il perimetro v1 restante non cambia.
- Criterio di focus esplicito: mantenere le funzionalità coerenti con il problema della procrastinazione ed evitare un insieme dispersivo di funzioni.

## Questioni aperte

- Come tradurre la filosofia di Kairos in comportamenti e funzionalità concrete?
- Quale tono e quali implicazioni di prodotto dovrebbero accompagnare questa filosofia? Da proporre e discutere; non sono decisioni dell’utente.
- Confermare o scartare le ipotesi architetturali elencate sopra.
- Quali sono i confini del progetto didattico, degli agenti e dei workflow?
- Quando valutare iOS e web rispetto alla prima versione Android?
- Per gli eventi, quali campi oltre a data e ora sono necessari per creare un evento? Come trattare informazioni mancanti diverse dal momento del promemoria? L’esempio del 31 ottobre resta privo di anno, durata e luogo effettivi.
- Come definire N promemoria per evento e il flusso per aggiungerli o modificarli?
- Quale scelta tecnica usare per l’internazionalizzazione? Non è ancora deciso se la lingua dell’interfaccia debba coincidere con quella della conversazione.
- Quali informazioni essenziali devono essere conservate nel contesto personale e come devono essere aggiornate? I dettagli di consenso e gestione dei dati non sono stati specificati.
- L’onboarding guidato sarà incluso in v1? Quali scelte o tag dovrebbe presentare?
- I guardrail restano un tema futuro o il coordinatore porterà avanti la proposta di includerli già in v1? I comportamenti specifici sono da definire.
- Come si stabilisce l’utilità dei feedback e chi può rivedere quelli filtrati dall’agente?
