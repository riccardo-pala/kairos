# Requisiti funzionali — Kairos

**Stato del documento:** baseline funzionale ricavata dalle idee esplicite, dalle proposte di prodotto e dallo stato descritto nel README al 24 ottobre 2026. Non equivale a una specifica approvata in ogni dettaglio.

## Sintesi per stakeholder

Chi procrastina può faticare a passare da un impegno o da un’intenzione alle azioni necessarie per affrontarli. Kairos nasce per supportare questo passaggio con un assistente personale ispirato al “momento opportuno”, mantenendo le funzioni legate a questo obiettivo.

La proposta funzionale è raccogliere la descrizione di un impegno, chiarire i dati mancanti e organizzarla in un evento con le attività da svolgere prima o dopo e i promemoria scelti dall’utente. L’interazione prevista comprende voce o testo e componenti dentro l’app; Android è la prima piattaforma e italiano e inglese sono richiesti fin dall’inizio.

La POC desiderata verifica questo percorso dall’impegno alla creazione dell’evento e alla ricezione dei promemoria. Oggi è disponibile soltanto la preparazione di una bozza in memoria nel backend; app mobile, voce, persistenza e notifiche sono ancora da realizzare. La lista della spesa è esclusa dalla POC.

## Problema, utenti e valore atteso

- **Problema di riferimento:** chi procrastina può avere difficoltà a passare da un’intenzione o da un impegno concreto all’azione necessaria.
- **Utenti previsti:** persone che procrastinano e desiderano supporto pratico nell’organizzare impegni e attività connesse. Non è definito un segmento più specifico.
- **Valore atteso:** rendere più semplice esprimere un impegno, chiarire le informazioni mancanti e organizzare attività e promemoria che l’utente ritiene utili.
- **Principio di prodotto:** favorire il “momento opportuno” e mantenere il focus sul supporto a chi procrastina; valutare nuove funzioni in base alla loro coerenza con questo scopo.
- **Limite delle evidenze:** il valore è un’intenzione di prodotto da verificare con utenti. Non sono disponibili risultati di ricerca o prove di efficacia clinica.

## Percorso utente desiderato

1. L’utente avvia una richiesta in italiano o inglese, usando testo o voce.
2. Descrive un evento o un impegno; può indicare luogo, durata e attività da svolgere prima o dopo, se pertinenti.
3. Kairos organizza i dati forniti e chiede le informazioni necessarie che mancano o sono ambigue. In particolare, se l’utente non ha indicato quando vuole un promemoria, gli chiede di sceglierlo.
4. L’utente può correggere la bozza e configurare N promemoria; il comportamento in caso di nessun promemoria resta da definire.
5. La revisione della bozza da parte dell’utente è un comportamento proposto da validare; le correzioni conversazionali della bozza sono già supportate nel workflow backend.
6. Come obiettivo della POC, Kairos crea l’evento con le attività e i promemoria configurati. La destinazione dell’evento (calendario interno o esterno) e il meccanismo con cui recapitare i promemoria restano da decidere; creazione persistente e notifiche non risultano implementate.
7. In una futura esperienza completa, l’utente può ritrovare il contesto essenziale che ha scelto di condividere. Persistenza e gestione del profilo non risultano implementate.

## Requisiti funzionali

Gli ID sono stabili per consentire riferimenti e revisioni. “Richiesto” indica un’intenzione esplicita dell’utente; i criteri descrivono risultati osservabili, lasciando aperti i dettagli non decisi.

| ID | Requisito e criterio osservabile | Stato e provenienza |
| --- | --- | --- |
| **FR-01** | L’utente può descrivere un evento o impegno in linguaggio naturale. Kairos restituisce una struttura di bozza coerente con i dati forniti. | Richiesto per la prima versione; workflow di bozza disponibile nel backend. |
| **FR-02** | L’utente può fornire la richiesta tramite testo oppure voce. Il contenuto vocale entra nello stesso percorso funzionale della richiesta testuale. | Testo e voce richiesti; interfacce e input vocale non implementati. |
| **FR-03** | La bozza può includere data e ora dell’evento, luogo e durata quando l’utente li conosce e li comunica. Il sistema non inventa valori mancanti. | Richiesto per il caso d’uso; alcuni campi e chiarimenti sono nel workflow backend. |
| **FR-04** | L’utente può associare all’evento una o più attività da svolgere prima e/o dopo. Le attività restano distinguibili dai promemoria. | Richiesto per la prima versione; la bozza backend supporta attività prima/dopo. |
| **FR-05** | L’utente può scegliere N promemoria per un evento. Se non specifica quando desidera un promemoria, Kairos lo chiede prima di completare la bozza. | Richiesto; chiarimenti e pluralità dei promemoria sono presenti nella bozza backend. Notifiche non implementate. |
| **FR-06** | Kairos chiede chiarimenti quando non dispone di informazioni necessarie o rileva ambiguità che impediscono di rappresentare la richiesta. Le risposte aggiornano la stessa bozza. | Richiesto nel flusso; aggiornamenti su più turni sono disponibili nel workflow. I dettagli dei campi obbligatori restano aperti. |
| **FR-07** | L’utente può correggere o completare le informazioni proposte prima di considerare la bozza pronta. | Comportamento derivato/proposta da validare; le correzioni della bozza sono supportate dal workflow backend, ma revisione UI e conferma esplicita prima della creazione non sono disponibili/decise. |
| **FR-08** | L’esperienza offre testo, voce e pulsanti o componenti interattivi dentro l’app, così il testo non è l’unico modo di interagire. | Richiesto; app e componenti interattivi non implementati. |
| **FR-09** | I widget della schermata Home Android non fanno parte del perimetro attuale. | Esclusione esplicita dell’utente. |
| **FR-10** | L’app supporta italiano e inglese fin dall’inizio. I flussi funzionali principali sono disponibili in entrambe le lingue. | Richiesto; supporto effettivo nell’app non implementato. La relazione tra lingua UI e lingua della conversazione è aperta. |
| **FR-11** | Kairos accumula nel tempo informazioni essenziali sull’utente che aiutano a personalizzare l’assistenza. | Richiesto; profilo persistente non implementato. Quali informazioni conservare e come gestirle è aperto. |
| **FR-12** | L’onboarding può offrire scelte guidate, pulsanti e tag mantenendo facoltativo l’inserimento manuale. | Possibilità da valutare, non requisito approvato; non implementato. |
| **FR-13** | Kairos crea l’evento descritto dall’utente con le attività e i promemoria configurati. | Obiettivo funzionale richiesto per la prima versione; il workflow attuale prepara soltanto una bozza in memoria. Creazione persistente non implementata. Destinazione interna/esterna da decidere. |
| **FR-14** | L’utente riceve i promemoria configurati per l’evento. | Obiettivo funzionale richiesto; notifiche non implementate. Meccanismo, tempi/orari effettivi e gestione dei permessi restano da definire. |

## Caratteristiche trasversali

- **Accesso semplice — richiesta esplicita:** il testo non deve essere l’unico modo di interagire; sono richiesti voce, pulsanti e componenti interattivi dentro l’app.
- **Focus — intenzione esplicita:** le funzionalità devono mantenere un legame sensato con il problema della procrastinazione; evitare l’accumulo di funzioni scollegate.
- **Informazioni mancanti — comportamento richiesto:** non trasformare esempi incompleti in fatti. Anno, luogo, durata o altre informazioni non fornite non vanno inventati; il chiarimento preciso è da definire per campo e caso.
- **Controllo dei dati e delle azioni — proposta da definire:** l’utente richiede un profilo essenziale accumulato, ma controlli su consenso, conservazione, modifica, cancellazione e azioni dell’assistente non sono ancora requisiti decisi.
- **Guardrail dei modelli — priorità riconosciuta, tempi aperti:** l’utente li considera importanti e li ha collocati “pro futuro”. Anticiparli alla prima versione è una proposta del coordinatore, non approvata. Comportamenti e criteri restano da definire.
- **Qualità e risultati — da verificare:** non sono definiti indicatori, soglie o promesse di miglioramento. Nessuna funzione implica diagnosi o trattamento clinico.

## Perimetro: POC e sviluppi futuri

| Area | Prima POC desiderata | Stato disponibile descritto nelle fonti | Futuro / esclusioni |
| --- | --- | --- | --- |
| Flusso evento | Bozza di impegno, attività prima/dopo, chiarimenti, creazione dell’evento e più promemoria da ricevere; Android come prima piattaforma prevista. | Workflow backend per preparare una bozza in memoria, con aggiornamenti su più turni e provider simulato; adattatore Ollama opzionale e CLI. | Creazione persistente, API HTTP, notifiche e app mobile non implementate; calendario e recapito dei promemoria da definire. |
| Interazione | Voce o testo, con pulsanti e componenti interattivi in app; italiano e inglese. | La CLI e il workflow documentati non costituiscono l’esperienza mobile richiesta. | Voice UI e UI Android da realizzare; widget Home Android esclusi per ora. |
| Profilo | Conservare informazioni essenziali utili alla personalizzazione. | Non risulta disponibile memoria persistente del profilo; il workflow conserva bozza e ultima domanda. | Contenuti e gestione del profilo da definire. |
| Lista della spesa | Esclusa dalla prima POC per mantenere il focus. | Non indicata come implementata. | Idea futura: rivalutare solo con un’integrazione coerente con il supporto alla procrastinazione. |
| Feedback | Fuori dal perimetro della prima POC. | Non indicato come implementato. | Idea futura: raccolta e organizzazione dei feedback; l’eventuale revisione umana è una proposta, non una decisione. |
| Guardrail | L’inclusione nella prima POC non è ancora approvata. | README descrive validazione degli argomenti e un primo confine del tool, non una protezione completa. | L’utente considera il tema importante per il futuro; anticipo in v1 proposto dal coordinatore. |
| Primo passo, inviti e ripartenza | Non inclusi come requisiti approvati della POC in base alle fonti attuali. | Non indicati come implementati. | Idee di prodotto da discutere: suggerire un piccolo primo passo, inviti in un momento scelto e ripartenza senza colpa. |

La descrizione dello stato disponibile è limitata a quanto riportato nel README e nel registro delle idee; non costituisce una verifica indipendente del codice.

## Scelte aperte

1. Quali campi, oltre a data e ora, servono per completare un evento? Quali sono obbligatori e quali richiedono chiarimento?
2. Come si definiscono aggiunta, modifica o rimozione di N promemoria e il comportamento per “nessun promemoria”?
3. La bozza deve richiedere sempre una conferma esplicita prima della creazione? Qual è il confine tra preparare una bozza e creare un impegno?
4. Italiano e inglese si applicano sia all’interfaccia sia alla conversazione? Come si sceglie la lingua quando differiscono?
5. Quali informazioni essenziali possono entrare nel profilo e quali controlli avrà l’utente su di esse?
6. L’onboarding guidato entra nella POC? Quali scelte aiutano senza aggiungere attrito?
7. I guardrail restano futuri o vengono anticipati alla prima versione? Quali regole osservabili ne definiscono il perimetro?
8. Quali scenari e utenti serviranno per valutare se il flusso è comprensibile e utile?

## Registro revisioni

| Data | Revisione |
| --- | --- |
| 24 ottobre 2026 | Prima baseline funzionale: requisiti espliciti separati da proposte e stato implementativo; lista della spesa esclusa dalla prima POC. |

## Gestione del documento

Questo Markdown è la fonte funzionale unica. Il Word è una versione presentabile derivata da rigenerare in occasione di revisioni significative; le modifiche funzionali fatte sul Word vanno riportate qui per evitare versioni divergenti.
