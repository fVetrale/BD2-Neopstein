# Diagramma — Modello ER relazionale del dataset sorgente

Come si modellerebbe il dataset `.parquet` in forma relazionale, prima della
mappatura a grafo. Nessuna entità `Person`: solo indirizzi email e display
name testuali (vedi "Derivazione di `Person`" in `graph_schema.md`).

```mermaid
erDiagram
    EMAIL_ADDRESS ||--o{ MAIL : "sender (FK)"
    EMAIL_ADDRESS ||--o{ MAIL_RECIPIENT : "recipient (FK)"
    MAIL ||--o{ MAIL_RECIPIENT : has
    MAIL ||--o{ MAIL_CLUSTER : has
    CLUSTER ||--o{ MAIL_CLUSTER : has
    MAIL ||--o{ MAIL_THREAD : has
    THREAD ||--o{ MAIL_THREAD : has

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
    MAIL_THREAD {
        string mail_id FK
        string doc_id FK
        int position
    }
```
