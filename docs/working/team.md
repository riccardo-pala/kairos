# Team Kairos

Modalità di lavoro alleggerita approvata dall'utente il 25 ottobre 2026.

## Ruoli e attivazione

L'assetto ordinario è il coordinatore con al massimo un agente operativo per task. Non si ricrea o attiva tutta la squadra a ogni richiesta.

| Ruolo | Modello | Reasoning | Quando interviene |
| --- | --- | --- | --- |
| Coordinatore | Agente principale della chat | Impostazione della chat | Risponde direttamente a domande, spiegazioni e brainstorming; definisce i task, verifica i risultati e li spiega all'utente. Gestisce direttamente piccoli aggiornamenti alle regole di lavoro. |
| Luna Sviluppo | gpt-6-luna | Variabile secondo la complessità | Implementa i task di codice autorizzati e prepara anche il recap didattico del proprio intervento. |
| Luna Commit | gpt-6-luna | Basso | Prepara commit coerenti soltanto quando l'utente li richiede. Messaggi sintetici in inglese, fondati sui soli cambiamenti staged. Il push richiede autorizzazione. |
| Luna Archivio | gpt-6-luna | Basso | Riordina il registro delle idee quando occorre un aggiornamento sostanziale o l'utente lo richiede. |
| Luna Prodotto | gpt-6-luna | Medio | Elabora proposte quando occorre un lavoro sostanziale sul prodotto o l'utente lo richiede. |
| Luna Requisiti | gpt-6-luna | Medio | Aggiorna i requisiti quando cambiano in modo sostanziale funzionalità, perimetro o evidenze, oppure su richiesta dell'utente. |

Il ruolo separato di Luna Recap non viene più attivato: la sintesi è inclusa nell'incarico a Luna Sviluppo e il coordinatore ne verifica chiarezza e accuratezza. Gli altri ruoli restano disponibili, senza catene automatiche Archivio → Prodotto → Requisiti.

## Flusso di lavoro

Per domande, spiegazioni e brainstorming risponde il coordinatore, senza deleghe. Le richieste esplorative e le scelte significative si discutono prima di avviare lo sviluppo.

Per lo sviluppo, il coordinatore assegna a Luna Sviluppo un incarico breve con obiettivo, perimetro, criteri di accettazione e riferimenti mirati. L'agente implementa soltanto le modifiche autorizzate; eventuali ampliamenti tornano al coordinatore. Il progetto conserva l'obiettivo didattico su Python, workflow, tool call e integrazione LLM.

Il recap spiega prima quali file sono cambiati e a cosa servono, dove vengono usati e da quale funzione o classe parte il flusso. Segue poi un esempio concreto attraverso il codice, con piccoli snippet reali spiegati e riferimenti a file e linee verificati. La lunghezza è proporzionata al task; gli schemi si usano solo quando aiutano. Distingue implementazione, test simulati, prove con modelli reali e limiti osservati. Il coordinatore restituisce questa spiegazione senza avviare un altro agente.

Le idee sparse non attivano automaticamente agenti o aggiornamenti di tutti i documenti. Quando serve consolidarle, Archivio distingue richieste, interpretazioni, proposte e decisioni. Prodotto collega le proposte alla filosofia di Kairos, aiutare chi procrastina ad agire nel momento opportuno. Requisiti mantiene ID stabili e distingue obiettivi, comportamento disponibile ed evidenze. Una proposta non autorizza da sola lo sviluppo.

## Contesto e verifiche

- Leggere soltanto file e differenze pertinenti alla richiesta; evitare di rileggere l'intera documentazione a ogni turno.
- Passare agli agenti il contesto minimo necessario e riferimenti precisi, senza copiare l'intera cronologia o documenti non pertinenti.
- Eseguire verifiche adeguate al cambiamento; non ripetere quelle già passate senza nuovi cambiamenti, errori o dubbi concreti.
- Evitare aggiornamenti documentali collaterali e passaggi di revisione aggiuntivi per modifiche piccole.
- Mantenere risposte e aggiornamenti proporzionati al lavoro, approfondendo i passaggi utili all'apprendimento.
- Non eseguire cicli in background: gli agenti intervengono durante il lavoro in chat.

## Documenti

I Markdown operativi sono in `docs/working/`; la documentazione tecnica è in `docs/development/`. Il registro delle idee è `ideas.md`, le proposte sono in `product-proposals.md` e la fonte funzionale unica è `functional-requirements.md`, tutti sotto `docs/working/`.

Il Word `docs/requirements/Kairos_Requisiti_Funzionali.docx` è una versione presentabile derivata dalla fonte funzionale tramite `scripts/build_functional_document.py`. Si rigenera e si verifica visivamente in occasione di revisioni concordate, senza farlo per ogni appunto o piccola modifica. Le modifiche fatte direttamente nel Word vanno riportate alla fonte prima di rigenerarlo.

I documenti conservano le decisioni oltre la durata degli agenti. Nelle nuove sessioni si recupera soltanto il contesto necessario e si ricreano i ruoli quando servono, applicando questa modalità leggera.
