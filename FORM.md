# Compilazione Form: Linee Guida per Agente AI

Questo documento funge da contesto e linea guida per automatizzare la compilazione dei moduli (form) richiesti dal professore per il monitoraggio del progetto. **Ogni volta che viene chiusa una Issue / completata una PR, l'agente deve consultare questo file prima di attivare il browser_subagent per la compilazione.**

---

## ⚙️ Variabili Globali (Da modificare con i valori reali)
- **TEAM_ID**: `<Neopstein>`
- **USER_FILIPPO_ID**: `<fVetrale>`
- **USER_JOSE_ID**: `<jose-sgariglia>`

*Nota: Modifica queste variabili una volta che i vostri codici identificativi definitivi sono noti.*

---

## 📝 FORM 3 – Issue/Feature Survey

**Link al Form**: [Clicca qui per il Form 3](https://cryptpad.fr/form/#/2/form/view/sul+mlxF-8YrToTYcRIhxHFMm7I--Sbittf7vircH68/)

Questo form è il cuore del tracciamento e misura i fattori che aumentano la complessità, l'effort e la "verification tax".

### ⏱️ Quando compilarlo (Trigger)
- **Solo ed esclusivamente** dopo che la Issue è stata realmente chiusa (Done/Closed).
- La relativa PR deve essere stata mergiata.
- Entro e non oltre le **24 ore** dalla chiusura.

### 👤 Chi lo compila
- Deve essere compilato a nome del **responsabile della Issue** (l'assignee).
- **Importante**: Se più persone hanno lavorato alla stessa Issue, ognuno inserirà solo le **sue ore personali** quando compilerà a proprio nome (mai inserire le ore totali del team).

### 📋 Regole e Consigli Pratici (Istruzioni per l'Agente)
1. **Identificativi**: Usa esattamente il `TEAM_ID` e il Codice Partecipante in base all'autore della PR/Issue (`USER_FILIPPO_ID` o `USER_JOSE_ID`).
2. **Issue ID e Titolo**: Estrai e usa esattamente il Titolo e l'ID della issue così come appaiono sul repository. Non inventarli.
3. **Driver di Complessità (NEI/NDEP/NDE ecc.)**:
   - Analizza la PR e seleziona la fascia più realistica (0, 1, 2–3, 4–6, >6). Non scegliere per forza sempre le stesse medie.
4. **Query Complexity**:
   - Seleziona la categoria della query più rilevante su cui si è lavorato (es. se c'è un CRUD ma anche una pipeline complessa, prediligi "aggregazioni/pipeline").
5. **Utilizzo AI / Strumenti Generativi**:
   - Se io (Agente AI) ti ho aiutato nella Issue, alla voce "Uso strumenti generativi" segna "Sì" e spiega sinteticamente dove e in che proporzione ti ho assistito.
6. **Rework/Loop**:
   - Conta i giri "grossi" di revisione o riscrittura (es. rifacimento dello schema o della pipeline), e non i micro-fix o i typo.
7. **Ore Personali**:
   - Chiedi sempre le ore personali da inserire, o deduci una stima ragionevole. **Devono essere solo le ore di chi ha fatto la Issue**.

### 🚫 Errori Tipici da Evitare (Strict Rules)
- **NON** inserire ore del team, ma solo personali.
- **NON** inserire Issue ID inventati.
- **NON** mettere fasce "medie" solo per sbrigarti. Le risposte devono riflettere la reale entità del codice.
- **NON** dichiarare "CI/test failures" se non vi è una CI implementata o usata per quella issue (in quel caso metti "Non applicabile").

---

## 📝 FORM 4 – PR Survey

**Link al Form**: [Clicca qui per il Form 4](https://cryptpad.fr/form/#/2/form/view/7zaW+oNuLYamvCnV4ck5M9almBHbeGRbu5gB1NPsn60/)

Questo form serve a quantificare il "costo di verifica e consegna" di una singola PR (review, test, correzioni, rework).

### ⏱️ Quando compilarlo (Trigger)
- **Solo ed esclusivamente** per PR effettivamente mergiate (non "open").
- Entro e non oltre **24 ore** dal merge.

### 👤 Chi lo compila
- L'**autore principale della PR**, ossia chi l'ha aperta, gestita fino in fondo e fixata. Inserirà solo le sue **ore personali**.
- Se lavorato in coppia, l'autore "titolare" della PR compila il form.

### 📋 Regole e Consigli Pratici (Istruzioni per l'Agente)
1. **Identificativi e Titoli**: Usa il `TEAM_ID`, l'ID utente corretto (`USER_FILIPPO_ID` o `USER_JOSE_ID`) e ricopia PR ID e Titolo esattamente da GitHub.
2. **Issue Collegate**: Specifica gli ID delle Issue risolte separati da virgola (es. `#12, #15`). Verifica che ci sia un `Closes #...` nella PR.
3. **Indicatori Change-Level**: Analizza quanto è ampia la modifica (interfacce, dipendenze, schema toccati).
4. **Utilizzo Strumenti Generativi (AI)**: Specifica come e dove io (o un'altra AI) sono intervenuto nella specifica PR.
5. **Review Rounds**: Conta i cicli completi "invio PR → feedback → aggiornamento → nuova review" (Non confonderli con il numero di reviewer).
6. **Severità delle Richieste**: Segna "maggiore" SOLO se ci sono stati cambi netti di design o approccio (non per piccoli fix o typo).
7. **CI/test failures**: Conta i fallimenti della pipeline prima del merge. Se non c'è CI, seleziona "Non applicabile".
8. **Ore Personali**: Stima accurata delle ore (implementazione + test + review fixes).

### 🚫 Errori Tipici da Evitare (Strict Rules)
- **NON** compilare prima che la PR sia mergiata sul branch principale.
- **NON** inserire "NONE" nelle issue collegate (le PR devono sempre chiudere una Issue).
- **NON** confondere il numero di persone (reviewers) con i cicli di revisione (review rounds).
- **NON** dichiarare fail di CI se la CI non esiste o non è stata eseguita.
- **NON** inserire ore del team, inserisci quelle personali dell'autore.

---

## 📝 FORM 5 – Log Settimanale

**Link al Form**: [Clicca qui per il Form 5](https://cryptpad.fr/form/#/2/form/view/rwaT81QeTchvIqPXMMPi7cBKPtVaajQf35h4YzxBS4k/)

Questo form serve a tenere un "registro" settimanale del tempo dedicato al progetto, per evitare imprecisioni dovute alla memoria. **Non sostituisce i form 3 e 4**, ma li affianca come "rete di sicurezza".

### ⏱️ Quando compilarlo (Trigger)
- **Una volta a settimana**, da compilare per la settimana appena trascorsa.
- Entro e non oltre **domenica alle 23:59**.
- **Nota**: Va compilato **anche se non hai lavorato** (in tal caso si indicano 0 ore).

### 👤 Chi lo compila
- Deve essere compilato singolarmente da **ogni membro del team** (sia Filippo che Josè compileranno il proprio ogni fine settimana).

### 📋 Regole e Consigli Pratici (Istruzioni per l'Agente)
1. **Identificativi e Date**: Usa `TEAM_ID` e ID utente. Come "settimana di riferimento" inserisci la data del **lunedì** della settimana appena passata.
2. **Ore Personali**: Somma TUTTE le ore personali spese sul progetto quella settimana (mai le ore dell'intero team).
3. **Giorni di Lavoro**: Inserisci il numero di giorni in cui c'è stato effettivo lavoro sul progetto.
4. **Conteggio Github**: Ricava dai log di Github quante Issue ha chiuso l'utente, quante PR ha mergiato come autore, e quante Code Review ha fatto per gli altri. Il conteggio deve essere reale e coerente.
5. **Ripartizione Percentuale del Tempo**: Fai una stima (il cui totale si avvicini al 100%) divisa per queste categorie:
   - *Schema/constraints* (progettazione, migrazioni)
   - *Query/analytics* (aggregazioni, ottimizzazioni)
   - *Backend/API* (script Python, ETL)
   - *Test/benchmark* (unit test, raccolta performance)
   - *Debug/rework* (correzioni, riscritture, fix post review)
   - *Docs/report* (README, report, diagrammi)
6. **Ostacolo Principale**: Descrivi brevemente (se presente) il blocco principale avuto durante la settimana.

### 🚫 Errori Tipici da Evitare (Strict Rules)
- **NON** compilare più settimane insieme in ritardo. Va fatto settimanalmente.
- **NON** mettere ore casuali che non combaciano con il lavoro svolto effettivamente in quella settimana.
- **NON** mettere percentuali finte o sempre uguali (es. "100% schema" per mesi).
- **NON** inserire le ore dell'intero team nel form personale.
