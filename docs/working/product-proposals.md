# Proposte di prodotto — Kairos

Queste proposte traducono le idee raccolte in `docs/working/ideas.md` in esperimenti da discutere. Le proposte funzionali qui sotto restano ipotesi, salvo le decisioni esplicite riportate come tali. Il riferimento è aiutare chi procrastina ad agire nel momento opportuno. Android è il primo contesto da considerare; iOS e web restano da valutare.

## 1. Dalla lista al primo passo

**Ipotesi:** davanti a un’attività rimandata, proporre un’azione iniziale molto piccola e concreta, da poter iniziare subito. Per esempio, “preparare la presentazione” può diventare “apri il documento e scrivi il titolo”. L’utente può accettare, modificare o rifiutare il suggerimento.

- **Valore per chi procrastina:** riduce l’incertezza su come cominciare e rende visibile un passo alla portata.
- **Primo esperimento/MVP:** schermata Android per inserire un’attività e ricevere un solo prossimo passo; pulsanti “Inizio ora”, “Modifica” e “Più tardi”. Verificare con pochi utenti se il passo suggerito aiuta a iniziare.
- **Ruolo del LLM:** proporre una scomposizione breve usando il contesto scritto dall’utente. L’interfaccia, la scelta finale e la registrazione dell’avvio restano deterministiche e sotto il controllo dell’utente.
- **Rischi da verificare:** passi vaghi, troppo grandi o inadatti; attività sensibili inviate al provider; suggerimenti che aggiungono lavoro invece di facilitarne l’avvio.

## 2. Un invito nel momento opportuno

**Ipotesi:** Kairos può offrire un invito leggero a riprendere un’attività scelta dall’utente, in una finestra o a un orario selezionato da lui. L’invito propone un’azione breve e una via semplice per rimandare o disattivare i promemoria.

- **Valore per chi procrastina:** porta l’attenzione su un’intenzione nel momento scelto, senza trasformare il promemoria in un obbligo.
- **Primo esperimento/MVP:** promemoria Android configurabile per una sola attività e una sola fascia oraria, con “Avvia”, “Rimanda” e “Disattiva”. Osservare se gli utenti lo trovano utile e rispettoso.
- **Ruolo del LLM:** facoltativamente riscrivere l’attività come invito breve e coerente con il tono scelto. Orari, frequenza, silenziamento e azioni dei pulsanti seguono regole deterministiche.
- **Rischi da verificare:** notifiche intempestive o insistenti, permessi e limiti del sistema operativo, tono percepito come giudicante. Nessuna promessa di miglioramento clinico.

## 3. Ripartire senza colpa

**Ipotesi:** se un’attività non parte o viene rimandata, offrire una breve scelta pratica: ridurre il passo, scegliere un altro momento o lasciare l’attività. Il mancato avvio non viene presentato come fallimento.

- **Valore per chi procrastina:** rende facile correggere il piano quando la prima proposta non funziona e mantiene l’utente in controllo.
- **Primo esperimento/MVP:** dopo un rinvio, mostrare tre opzioni predefinite (“Riduci il passo”, “Scegli un orario”, “Lascia stare”) e verificare con sessioni osservate quale opzione è comprensibile e utile.
- **Ruolo del LLM:** se richiesto, aiutare a formulare un passo più piccolo o una motivazione pratica, senza interpretare stati mentali. Le opzioni, i rinvii e la modifica dell’attività sono gestiti dall’app.
- **Rischi da verificare:** far sentire l’utente monitorato o in colpa; formulazioni che sembrano diagnosi; raccogliere più dati del necessario.

## Flussi e implicazioni per la POC

Il focus attuale è il flusso di eventi, attività e promemoria come base per facilitare un’azione concreta. Un’agenda, da sola, non dimostra né garantisce che la procrastinazione venga superata. Le indicazioni seguenti descrivono un possibile flusso da discutere, non una specifica approvata.

### Eventi, attività e promemoria

Da voce o testo, Kairos potrebbe mostrare un riepilogo modificabile con evento, luogo e durata se forniti, attività da svolgere prima o dopo e promemoria richiesti. Voce trascritta e testo dovrebbero entrare nello stesso flusso di interpretazione e revisione. L’assistente chiede gli orari dei promemoria quando mancano e chiarisce solo ambiguità o dati necessari, come anno o fuso orario quando incidono sull’orario, oppure a quale evento si riferisce un’attività “prima” o “dopo”. Non inventa valori mancanti; l’utente rivede il riepilogo prima della creazione.

Attività collegate, evento e promemoria sono oggetti distinti: un’attività prima/dopo descrive qualcosa da fare, un promemoria indica quando avvisare. Un evento può avere N promemoria configurabili. Pianificazione, validazione di date e orari e registrazione delle scelte sono deterministiche; il LLM interpreta la richiesta e propone una struttura, che l’utente può correggere.

## Decisione esplicita: lista della spesa fuori dalla prima POC

La lista della spesa non rientra nella prima POC. L’idea resta futura e potrà essere rivalutata solo se avrà un’integrazione sensata con il problema della procrastinazione, evitando di accumulare funzioni scollegate. Se ripresa, potrebbe generare da una ricetta una lista modificabile con articoli ricorrenti e acquisti una tantum; la ricorrenza di un articolo non autorizzerebbe ordini, acquisti o rifornimenti automatici.

## Filtro proposto per nuove funzionalità

Questi criteri sono una proposta operativa derivata dall’intento del prodotto, non nuovi vincoli approvati. Prima di aggiungere una funzione, chiedersi:

- Quale rinvio o ostacolo concreto aiuta a superare?
- Quale azione concreta rende più facile iniziare o completare?
- La complessità aggiunta è proporzionata al beneficio per quel caso d’uso?

Se non emerge un legame chiaro tra ostacolo e azione facilitata, la funzione può restare fuori dalla POC e venire rivalutata in seguito.

### Interazione, profilo e guardrail

Pulsanti e componenti interattivi dentro l’app possono offrire azioni rapide e avvio vocale. I widget della schermata Home Android sono esclusi per ora. Un onboarding con tag o selezioni è un’opzione da valutare, mantenendo facoltativo il testo.

### Lingua, streaming e messaggi di progresso — decisione del 25 ottobre 2026

Per backend e CLI, le stringhe statiche restano complete in italiano e inglese e seguono la lingua dell’interfaccia. Chiarimenti e testo LLM usano una sola lingua conversazionale per turno, senza agente o chiamata aggiuntiva. La preferenza iniziale deriva dal contesto; saluti chiaramente riconosciuti possono indicare una lingua, mentre input brevi, ambigui o neutri come “ok”, date e numeri mantengono la lingua precedente. Un cambio esplicito in italiano o inglese prevale; anche un messaggio successivo sostanziale in una di queste lingue può cambiare la lingua del turno. Se la lingua della chat non è supportata, l’inglese diventa il default della chat nella chiamata LLM già prevista, senza rilevamento separato. La regola è nel prompt e i test simulati, incluso mock HTTP, passano.

Una prova reale limitata su Ollama `qwen3:8b` Q4_K_M (`think=False`, temperatura 0, seed 42; 6 scenari e 9 turni per variante) ha mostrato che la baseline non seleziona o mantiene sempre la lingua attesa in quella configurazione, per esempio restando in italiano con contesto iniziale inglese. Il candidato compatto ha superato più check linguistici della baseline (3/6 contro 2/6), ma è stato scartato perché ha introdotto regressioni semantiche in prove con injection. Il prompt runtime baseline da 354 parole resta in uso; la prova circoscritta non dimostra un’incapacità generale del modello. Un’eventuale correzione e nuova valutazione restano un punto aperto, senza nuova modifica autorizzata.

Lo streaming del testo è opzionale e separato dalle tool call. Gli argomenti vengono raccolti e validati prima dell’esecuzione; la CLI presenta la bozza validata e non espone JSON parziali o reasoning. I messaggi di progresso sono prodotti dal codice, statici nella lingua UI e descrivono soltanto fasi reali osservabili, senza timer, pensieri del modello o chiamate LLM aggiuntive. Streaming e progressi sono verificati con provider simulato; le evidenze reali limitate sulla lingua sono riportate sopra. API, app mobile, persistenza e notifiche non fanno parte di questa decisione.

La lingua non deve alterare l’interpretazione di date, numeri o fusi orari: questi valori vanno analizzati e validati secondo regole esplicite, anche quando la richiesta mescola lingua e formati.

Come proposta per v1, le informazioni di profilo salvate dovrebbero essere essenziali, esplicite, modificabili e cancellabili. Vanno mostrate e gestite separatamente dalla cronologia delle conversazioni e dalle inferenze del modello; un’inferenza non confermata non diventa un fatto di profilo. Servono limiti chiari su quali strumenti l’assistente può invocare, validazione deterministica dei parametri, protezione dei dati in memoria e gestione degli input che tentano di sovrascrivere le istruzioni. La conferma dell’utente dovrebbe essere proporzionata all’effetto: revisione prima di creare o cambiare impegni, conferma esplicita per azioni esterne o difficili da annullare.

La gestione dei feedback resta futura: un agente può raccogliere e ordinare segnalazioni per revisione, ma non dovrebbe modificare codice né eliminare feedback autonomamente. Ogni segnalazione e ogni esito di revisione dovrebbero restare tracciabili.

Prima di definire l’MVP vanno decisi il trattamento dei dati in locale o nel cloud e l’affidabilità attesa delle notifiche nei diversi contesti d’uso. Queste proposte non scelgono tecnologie.

## Questioni da discutere

- Quale situazione quotidiana dovrebbe guidare il primo prototipo?
- I promemoria sono coerenti con l’idea di “momento opportuno” se è l’utente a scegliere quando riceverli?
- Quale tono dovrebbe usare Kairos quando l’utente rimanda o non avvia un’attività?
- Quali dati possono restare sul dispositivo e quali, se necessari, verrebbero inviati al servizio LLM?
- Quali conferme servono per creare o modificare eventi e attività, e quali per eventuali azioni esterne?
- Come si gestiscono fuso orario, orari ambigui e permessi di notifica nel flusso scelto?
- Quali dati di profilo l’utente può salvare esplicitamente, e come vedere, modificare o cancellare tali dati?
- Quali componenti interattivi nell’app e azioni rapide hanno valore sufficiente per la prima versione?
- Come migliorare la selezione e il mantenimento della lingua senza introdurre regressioni semantiche? I risultati disponibili sono limitati alla configurazione Ollama descritta.
