# Diagramma — Modello ER relazionale del dataset sorgente

Come si modellerebbe il dataset `.parquet` in forma relazionale, prima della
mappatura a grafo. Nessuna entità `Person`: solo indirizzi email e display
name testuali (vedi "Derivazione di `Person`" in `graph_schema.md`).

Le tabelle ponte (`MAIL_RECIPIENT`, `MAIL_CLUSTER`) esistono solo dove la
relazione è realmente N:M (una mail ha più destinatari, un destinatario
riceve più mail; una mail può appartenere a più cluster con probabilità
diverse). Il legame `Mail`-`Thread` è invece N:1 (ogni mail ha un solo
`doc_id` e un solo `message_index`, vedi `src/etl/build_csv.py`): niente
tabella ponte, `thread_doc_id` (FK) e `position` sono colonne dirette di
`MAIL`, come già `sender_address`.

```mermaid
erDiagram
    EMAIL_ADDRESS ||--o{ MAIL : "sender (FK)"
    EMAIL_ADDRESS ||--o{ MAIL_RECIPIENT : "recipient (FK)"
    MAIL ||--o{ MAIL_RECIPIENT : has
    MAIL ||--o{ MAIL_CLUSTER : has
    CLUSTER ||--o{ MAIL_CLUSTER : has
    THREAD ||--o{ MAIL : "thread (FK)"

    EMAIL_ADDRESS {
        string address PK
        string domain
        bool is_redacted
    }
    MAIL {
        string id PK
        string subject
        string body
        datetime sent_at
        int redaction_count
        float redaction_ratio
        int attachment_count
        bool is_promotional
        string sender_address FK
        string thread_doc_id FK
        int position
    }
    MAIL_RECIPIENT {
        string mail_id FK
        string address FK
        string recipient_type "TO | CC | BCC"
    }
    CLUSTER {
        int cluster_id PK
        string label
    }
    MAIL_CLUSTER {
        string mail_id FK
        int cluster_id FK
        float probability
    }
    THREAD {
        string doc_id PK
    }
```
