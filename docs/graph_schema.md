# Graph Schema — Mappatura ER → Neo4j

Traduzione formale del modello ER relazionale (email del dataset Epstein) nel
modello a grafo Neo4j. Documento di design, nessun codice.

## Nodi

| Label | Chiave | Altre proprietà |
|---|---|---|
| `Person` | `person_id` | `display_name`, `is_unknown`, `is_epstein` |
| `EmailAddress` | `address` | `domain`, `is_redacted` |
| `Mail` | `id` | `subject`, `body`, `sent_at`, `redaction_count`, `redaction_ratio`, `attachment_count`, `is_promotional` |
| `Cluster` | `cluster_id` | `label` |
| `Thread` | `doc_id` | — |

## Relazioni

| Relazione | Proprietà | Note |
|---|---|---|
| `(Person)-[:OWNS]->(EmailAddress)` | — | una persona può possedere più indirizzi |
| `(EmailAddress)-[:SENT]->(Mail)` | — | mittente della mail |
| `(Mail)-[:TO\|:CC\|:BCC]->(EmailAddress)` | — | un tipo di relazione per ruolo destinatario, non un'unica `RECEIVED` con attributo |
| `(Mail)-[:BELONGS_TO]->(Cluster)` | `probability` | soft-clustering: una mail può appartenere a più cluster con probabilità diverse |
| `(Mail)-[:PART_OF]->(Thread)` | `position` | `position = message_index`, ordina i messaggi dentro il thread |

Convenzioni: label nodi in PascalCase, tipi di relazione in MAIUSCOLO con underscore.

## Differenze principali rispetto al modello ER relazionale

- **Proprietà sugli archi, non su entità dedicate.** `cluster_probability` e
  `message_index` nel modello relazionale richiederebbero una tabella
  associativa (`Mail_Cluster`, `Mail_Thread`) con FK + attributo. In Neo4j
  sono proprietà native della relazione (`BELONGS_TO.probability`,
  `PART_OF.position`): nessuna tabella ponte, nessun JOIN per leggerle.
- **Ruolo del destinatario come tipo di relazione, non come colonna.**
  Invece di una FK con discriminatore (`recipient_type IN ('TO','CC','BCC')`),
  usiamo tre tipi di relazione (`TO`, `CC`, `BCC`). Il ruolo è nello schema,
  non nel dato, e permette pattern Cypher mirati (es. solo `CC`) senza filtri.
- **Denormalizzazione controllata sui nodi.** `EmailAddress.domain` è
  derivabile da `address`, ma viene materializzato come proprietà per evitare
  parsing ripetuto nelle query; scelta di comodo, non necessità del modello a
  grafo.
- **Nessuna FK esplicita.** L'attraversamento `Person → EmailAddress → Mail`
  sostituisce i JOIN relazionali con pattern match sul grafo; le "relazioni"
  ER diventano archi di primo livello, interrogabili in entrambe le direzioni
  senza indici su colonne FK dedicate.
- **Cardinalità non imposte dal DB.** Il modello relazionale può vincolare
  cardinalità con FK + UNIQUE; Neo4j non impone cardinalità sugli archi. Le
  cardinalità attese (es. un `EmailAddress` appartiene a al più un `Person`,
  una `Mail` ha esattamente un `SENT`) sono documentate qui e verificate dai
  test post-import (issue #10), non dal DB stesso.
- **Entità senza mapping esplicito nel dataset sorgente:** vedi sezione
  dedicata sotto (`Person`, `Thread`).

## Derivazione di `Person`

Il dataset non contiene un mapping esplicito nome → persona: solo indirizzi
email e display name testuali nei campi `sender`/`to_recipients`/
`cc_recipients`/`bcc_recipients` (stringhe `"Nome <indirizzo>"` o
`"<indirizzo>"`).

Decisione: `Person` è il risultato di **entity resolution sui display name**,
eseguita in fase ETL, non un'entità presente 1:1 nel dataset grezzo.

- **Niente split `Firstname`/`Lastname`.** I display name sono troppo
  irregolari (ordine variabile, iniziali, titoli, redazioni parziali) per uno
  split affidabile. `Person` espone solo `display_name` (la variante scelta
  come canonica), più `is_unknown` e `is_epstein`.
- **Pipeline di risoluzione, in ordine:**
  1. Regole deterministiche: normalizzazione stringa (case, spazi, punteggiatura),
     confronto cognome + iniziale, indirizzi email condivisi tra varianti di
     nome diverse.
  2. Fallback LLM locale (llama3.1) solo per i casi ambigui non risolti dalle
     regole; output cachato su file (`data/ml_output/`) per rendere i run
     ripetibili senza reinterrogare il modello.
- **Nodo comunque creato in assenza di nome.** Se un `EmailAddress` non ha un
  display name associato ricavabile, l'indirizzo esiste comunque come nodo
  `EmailAddress`; il nodo `Person` collegato via `OWNS` si crea solo quando è
  disponibile almeno un nome, altrimenti `Person.is_unknown = true` con
  `display_name` assente o placeholder.
- **Cardinalità attesa:** un `EmailAddress` è posseduto da al più un
  `Person` (`OWNS` 1:N in uscita da `Person`); un `Person` può possedere più
  indirizzi. Verificata nei test post-import, non imposta da Neo4j.

## `Thread`

Entità non presente come tale nel modello ER originale: introdotta per
ricostruire l'ordine delle conversazioni. Chiave `doc_id`; la posizione del
messaggio nel thread (`message_index` nel dataset) diventa la proprietà
`position` della relazione `PART_OF`, non un attributo di `Mail`, perché è
significativa solo nel contesto di un thread specifico.


