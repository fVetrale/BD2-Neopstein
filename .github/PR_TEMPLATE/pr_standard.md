---
name: PR standard progetto
about: Template per creare una Pull Request conforme alla struttura richiesta dal docente
title: "[FASE-N] Titolo breve (verbo + oggetto)"
labels: ""
assignees: ""
reviewers: ""
---

## Issue collegata

<!--
OBBLIGATORIO: ogni PR deve chiudere almeno una issue.
Usa il costrutto Closes, non solo un riferimento (Related to si usa solo
in casi particolari, ma durante il corso ogni PR chiude almeno una issue).
-->

Closes #<ID>

## Descrizione

**Cosa cambia:**
<!-- Almeno 3 bullet, anche brevi -->
-
-
-

**Come testare:**
<!-- Comandi o passi concreti per riprodurre/verificare la modifica -->
-

## Checklist di verifica

<!--
Prima di chiedere il merge va verificato che la modifica funzioni e non
rompa nulla. Compila SOLO le sezioni pertinenti al tipo di modifica;
per le altre scrivi "N/A" (ammesso solo per PR di sola documentazione/
formattazione/typo, o se il progetto non ha ancora test/benchmark —
in quel caso specifica comunque cosa hai verificato manualmente, con
comandi e risultati).
-->

- [ ] **Query/aggregazioni**: eseguita la query su seed data, conservato output/log o screenshot, indicato il comando usato
- [ ] **Schema/constraint/migrazioni**: eseguito lo script di setup, verificato che il DB si avvii, che schema/constraint siano applicati, che inserimento e lettura base funzionino
- [ ] **Indici/ottimizzazione**: eseguito un mini-benchmark (anche semplice: tempo medio su N run), riportati i risultati
- [ ] **ETL/ingestion**: eseguita la pipeline su dati sintetici, verificato conteggio record e validazioni
- [ ] **API/backend**: lanciati test unit/integration oppure eseguite almeno alcune chiamate base (curl/Postman), riportati esempi

## README aggiornato?

<!--
Aggiornare se la PR cambia come si usa il progetto: nuovo script
(setup/seed/benchmark/query), comandi di avvio o docker compose,
nuove dipendenze o prerequisiti, struttura dati o endpoint principali,
nuove modalità di test/benchmark.
NON serve per refactor interni che non cambiano l'uso esterno o
correzioni minime che non incidono su comandi/procedura.
-->

- [ ] Sì — sezione aggiornata: `<nome sezione>`, comando/esempio: `<comando>`
- [ ] No — non necessario perché: `<motivo>`

## Controllo sicurezza

<!--
Nel repository non devono comparere dati sensibili o credenziali:
password, token, API key, credenziali DB, cookie, ecc.
Controllare file e pattern tipici (es. se si usa Python, controllare il .env).
-->

- [ ] Verificato che nessun file della PR contiene credenziali o segreti (es. `.env` escluso/ignorato)

## Review

<!--
Il reviewer deve essere una persona diversa dall'autore. Se lavorate da
soli, il reviewer è il docente. Il merge va fatto dopo almeno
un'approvazione, oppure dopo aver gestito in modo condiviso gli eventuali
commenti emersi.
-->

**Reviewer richiesto:** <nome, oppure "docente" se si lavora da soli>

## Label

<!-- almeno 1, meglio 1-2. Esempi: setup, design, etl, db, query, testing, documentation, API -->
