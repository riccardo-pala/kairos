# Team Kairos

Organizzazione richiesta dall'utente il 24 ottobre 2026.

| Ruolo | Modello | Reasoning | Responsabilità |
| --- | --- | --- | --- |
| Coordinatore | Agente principale della chat | Impostazione della chat | Dialogo con l'utente, riconoscimento degli spunti, deleghe e sintesi |
| Luna Archivio | gpt-6-luna | Basso | Raccogliere e riordinare le idee in `docs/working/ideas.md` |
| Luna Prodotto | gpt-6-luna | Medio | Elaborare proposte a partire dal registro in `docs/working/product-proposals.md` |
| Luna Requisiti | gpt-6-luna | Medio | Mantenere `docs/working/functional-requirements.md`: funzionalità, caratteristiche, perimetro e criteri osservabili con taglio funzionale e sintesi per stakeholder |

## Flusso di lavoro

L'utente comunica con il coordinatore e può inserire idee o nozioni sparse anche fuori contesto. Il coordinatore riconosce gli spunti pertinenti a Kairos e li delega automaticamente a Luna Archivio, senza richiedere ogni volta una formula esplicita o una conferma.

Dopo l'aggiornamento del registro, il coordinatore coinvolge Luna Prodotto per elaborare o aggiornare le proposte quando lo spunto ha conseguenze sul prodotto. Le proposte rimangono da valutare fino a una decisione dell'utente; una nuova idea non autorizza da sola l'implementazione.

Luna Archivio conserva la distinzione fra parole dell'utente, interpretazioni, proposte e decisioni. Luna Prodotto collega le proposte alle idee di origine e alla filosofia di Kairos: aiutare chi procrastina a cogliere il momento opportuno per agire.

Luna Requisiti è proprietaria del documento funzionale e si coordina direttamente con Luna Archivio, Luna Prodotto e il coordinatore, come autorizzato dall'utente. Il coordinatore la coinvolge quando emergono modifiche funzionali, caratteristiche trasversali, decisioni di perimetro o chiarimenti. Archivio fornisce le fonti e le decisioni; Prodotto fornisce le proposte con il loro stato. Requisiti aggiorna il documento distinguendo richieste esplicite, ipotesi da valutare e comportamento disponibile, senza trasformare proposte in decisioni.

Per contenere i token, gli agenti si scambiano soprattutto i cambiamenti rilevanti e i riferimenti ai documenti. Requisiti mantiene ID stabili, criteri osservabili sintetici e una breve traccia delle revisioni; non occorre riscrivere l'intero documento a ogni aggiornamento. La sintesi per stakeholder descrive problema, valore atteso e percorso utente, evitando dettagli di implementazione e promesse non verificate. Non sono previsti cicli di esecuzione in background: il coordinatore attiva gli agenti durante il lavoro in chat.

## Organizzazione dei documenti

I Markdown operativi sono in `docs/working/`; la documentazione tecnica è in `docs/development/`. Il documento presentabile dei requisiti è `docs/requirements/Kairos_Requisiti_Funzionali.docx`. Luna Requisiti mantiene la fonte unica `docs/working/functional-requirements.md`; lo script `scripts/build_functional_document.py` produce il Word derivato. Il coordinatore ne verifica l'impaginazione dopo le revisioni significative, senza generare una nuova versione per ogni appunto. Le modifiche fatte direttamente nel Word vanno riportate alla fonte per evitare divergenze.

I documenti nel repository conservano il lavoro oltre la durata dei singoli sottoagenti. Se una sessione non conserva gli agenti attivi, il coordinatore può ricreare questi ruoli leggendo questo documento e il registro.
