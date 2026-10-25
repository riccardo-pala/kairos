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
6. **Copertura multilingua dei testi e delle domande.** L’utente richiede che testi e domande siano gestiti per codice lingua e rispettino un contratto che garantisca copertura per tutte le lingue supportate.
7. **Architettura estendibile a più tool.** Il modello deve poter scegliere fra più tool disponibili, mantenendo il flusso per turno definito dall’app.

### Chiarimento esplicito sui widget

- Per “widget” si intendono componenti interattivi dentro l’app.
- I widget della schermata Home Android sono esclusi per ora.

## Idee future — idee esplicite dell’utente

- **Lista della spesa per una ricetta:** in precedenza proposta tra i requisiti v1, ora rimossa dalla prima POC per evitare un’accozzaglia di funzionalità. Da conservare come possibilità futura e rivalutare per capire come integrarla in modo sensato con un’app per persone che procrastinano. L’idea originaria prevedeva una lista modificabile con articoli ricorrenti e acquisti una tantum distinti.
- **Feedback su bug e miglioramenti:** sezione in cui l’utente può segnalare bug o proporre miglioramenti; un agente raccoglie, riordina, struttura e filtra i feedback in base alla loro utilità.
- **Guardrail dei modelli:** l’utente li considera molto importanti. La collocazione temporale indicata dall’utente è “pro futuro”.

## Proposte UI future — da valutare

- Durante la revisione, il frontend potrebbe proporre titoli alternativi selezionabili e un mini calendario per la data.
- Il luogo potrebbe iniziare come campo semplice; una mappa o selezione geografica restano un possibile sviluppo futuro. Nessuna di queste proposte è inclusa nell'implementazione corrente.

## Proposta del coordinatore — da valutare

- Anticipare i guardrail dei modelli fin dalla prima versione, pur avendo l’utente indicato il tema come pro futuro. È una proposta del coordinatore, non una decisione dell’utente.

## Decisioni del 25 ottobre 2026 — implementate nel backend e nella CLI

- Mantenere completo il catalogo statico di stringhe localizzate in italiano e inglese; generare i chiarimenti LLM in una sola lingua per turno, senza agente o chiamata aggiuntiva.
- Ricavare la preferenza iniziale dal contesto e mantenere la lingua precedente per risposte brevi (“ok”), date e numeri. Un cambio esplicito o chiaramente espresso nella stessa chiamata determina la lingua del turno.
- Decisione aggiuntiva del 25 ottobre: se la chat indica una lingua non supportata, usare l’inglese come default della chat nella chiamata LLM già prevista. Una richiesta esplicita in italiano o inglese prevale; anche un successivo messaggio sostanziale in una di queste lingue può cambiare la lingua conversazionale. Saluti chiaramente riconosciuti possono indicare la lingua; input brevi, ambigui o neutri mantengono quella precedente. Nessun agente o rilevamento separato. Regola nel prompt implementata e test simulati passati; una prova limitata su Ollama `qwen3:8b` Q4_K_M ha mostrato esiti linguistici non conformi in quella configurazione, senza conclusioni generali sul modello.
- Consentire lo streaming testuale come capacità opzionale, distinta dalle tool call. Raccogliere e validare gli argomenti; presentare la bozza validata, mai JSON parziale o reasoning.
- Produrre dal codice messaggi di progresso riferiti a fasi realmente osservabili, statici nella lingua dell’interfaccia CLI. Non simulare attese, esporre pensieri del modello o aggiungere chiamate LLM per generare aggiornamenti. Il testo LLM e i chiarimenti seguono invece la lingua della conversazione.
- Limitare questa implementazione a backend e CLI. API, app mobile, persistenza e notifiche non rientrano nella decisione.
- Una valutazione reale, limitata a `qwen3:8b` Q4_K_M con `think=False`, temperatura 0 e seed 42, ha coperto 6 scenari e 9 turni per variante. La baseline ha fallito alcuni casi di scelta e mantenimento lingua; il candidato compatto ha avuto 3/6 check contro 2/6 della baseline, ma è stato scartato per regressioni semantiche nei casi con injection. Il runtime mantiene il prompt baseline di 354 parole; questi risultati non descrivono ogni configurazione né dimostrano un’incapacità generale del modello.

Queste decisioni sono state approvate dall’utente il 25 ottobre 2026 e implementate nel perimetro sopra indicato. I test simulati passano; la valutazione reale limitata ha dato esiti non conformi per la selezione della lingua in quella configurazione. Nessun candidato alternativo è stato promosso.

## Contesto di progetto riportato

- App mobile di assistente personale basata su LLM.
- Android come prima piattaforma; iOS e web sono da valutare.
- Progetto didattico in Python, con integrazione agentica e workflow.
- L’utente vuole partecipare attivamente e seguire da vicino il lavoro.
- Il frontend è principalmente affidato al coordinatore.
- **Preferenza di collaborazione esplicita dell’utente:** procedere più spediti con le implementazioni e fermarsi sulle spiegazioni dei passaggi critici, in particolare workflow, chiamate ai tool e integrazione LLM. L’utente non vuole essere guidato manualmente su ogni dettaglio di base. Questa preferenza non cambia il carattere didattico e hands-on del progetto.
- **Organizzazione del lavoro esplicita dell’utente:** il coordinatore interpreta le richieste e le traduce in task per Luna Sviluppo, scegliendo il livello di reasoning in base alla complessità; il coordinatore non scrive codice. Non iniziare automaticamente uno sviluppo: quando utile, prima si fa brainstorming. Luna Commit, con reasoning basso, gestisce i commit locali per scope.

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
- Enum `Language` e catalogo di messaggi localizzati completo, con validazione all’avvio per verificare la copertura delle lingue.
- Alla baseline, tipo `LocalizedText` usato anche per i chiarimenti generati dal LLM; la decisione successiva richiede una sola lingua conversazionale per turno.
- Registro di tool estendibile, con schema, handler e disponibilità per ciascun tool. Sono presenti `update_event_draft` e `ask_event_clarification`; il secondo espone una capacità di chiarimento già esistente in forma separata. Il workflow sceglie una chiamata per turno.
- Alla baseline, i chiarimenti LLM erano rappresentati con `LocalizedText` completo e lo streaming era disattivato (`false`); queste parti sono state poi aggiornate secondo le decisioni del 25 ottobre.

Questi elementi descrivono implementazioni iniziali verificate dal coordinatore; l’estensione del registro non implica nuove funzioni di prodotto né autorizza azioni esterne. Non costituiscono una decisione di adottare definitivamente Ollama. Al momento della baseline non risultavano ancora implementate API, persistenza, notifiche o UI. La lingua per turno, lo streaming e i progressi sono stati aggiornati in seguito e verificati con provider simulato; la prova reale limitata sulla lingua ha dato esiti non conformi nella configurazione descritta sopra.

## Decisioni

- Nessuna decisione architetturale o di implementazione definitiva approvata registrata al momento. Le implementazioni iniziali sopra elencate sono stato di avanzamento e scelte estendibili, non una scelta definitiva di stack o provider.
- La filosofia esplicita dell’utente è il riferimento per valutare le funzionalità: favorire il momento opportuno e contrastare il rimandare.
- La lista della spesa è esclusa dalla prima POC e conservata come idea futura, da rivalutare per una possibile integrazione coerente con il prodotto. Il perimetro v1 restante non cambia.
- Criterio di focus esplicito: mantenere le funzionalità coerenti con il problema della procrastinazione ed evitare un insieme dispersivo di funzioni.
- Backend e CLI adottano stringhe statiche complete IT/EN, chiarimenti e testo LLM in una sola lingua per turno, streaming testuale opzionale separato dalle tool call e messaggi di progresso statici nella lingua UI legati a fasi osservabili; la CLI mostra la bozza validata e non espone JSON parziale o reasoning. Nessuna chiamata LLM aggiuntiva per il progresso. Test simulati, incluso mock HTTP per fallback e cambi lingua, passati; la valutazione reale linguistica limitata ha dato esiti non conformi in parte dei casi. Runtime baseline mantenuto.

## Questioni aperte

- Come tradurre la filosofia di Kairos in comportamenti e funzionalità concrete?
- Quale tono e quali implicazioni di prodotto dovrebbero accompagnare questa filosofia? Da proporre e discutere; non sono decisioni dell’utente.
- Confermare o scartare le ipotesi architetturali elencate sopra.
- Quali sono i confini del progetto didattico, degli agenti e dei workflow?
- Quando valutare iOS e web rispetto alla prima versione Android?
- Per gli eventi, quali campi oltre a data e ora sono necessari per creare un evento? Come trattare informazioni mancanti diverse dal momento del promemoria? L’esempio del 31 ottobre resta privo di anno, durata e luogo effettivi.
- Come definire N promemoria per evento e il flusso per aggiungerli o modificarli?
- Quali informazioni essenziali devono essere conservate nel contesto personale e come devono essere aggiornate? I dettagli di consenso e gestione dei dati non sono stati specificati.
- Come migliorare e rivalutare la selezione della lingua nel prompt senza introdurre regressioni semantiche? La prova reale attuale è circoscritta al modello e alla configurazione indicati e non autorizza da sola un nuovo fix o la promozione del prompt candidato.
- L’onboarding guidato sarà incluso in v1? Quali scelte o tag dovrebbe presentare?
- I guardrail restano un tema futuro o il coordinatore porterà avanti la proposta di includerli già in v1? I comportamenti specifici sono da definire.
- Come si stabilisce l’utilità dei feedback e chi può rivedere quelli filtrati dall’agente?
