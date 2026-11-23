# OpsIntel AI architecture

```text
Browser ──Django session──> Org-aware Django pages
                                  │
       ┌──────────────────────────┼──────────────────────────┐
       Operations              Finance                  Procurement
       runs/incidents          transactions/budgets      vendors/approvals/orders
       evidence/media          forecast                  delivery/media
                                  │
                  scoped database query layer + audit events
                    SQLite local / PostgreSQL deployment
                                  │
         ┌────────────────────────┼────────────────────────┐
     LLM assistant          Private file storage         Celery + Redis
   OpenAI or Ollama       local or S3/Boto3           scheduled scans/retry
```

Every business record is related to an organization. HTML views, downloads, assistant context and the pipeline API resolve the active organization from the signed-in membership or organization-scoped API key, then filter reads/writes against it. Organization invite codes add members as Executive Viewer; an organization admin may assign a narrower operational role. API keys are random bearer secrets stored as SHA-256 digests and can be revoked.

Uploaded documents and incident evidence are private by default. Download endpoints require authentication and a matching organization. S3 object access uses the application's server-side storage client; the browser is not given a public bucket URL.

## AI assistant context

The assistant is a real provider call when OpenAI or Ollama is configured. It receives only the active tenant's aggregate records and up to three matching text-file excerpts from that tenant. General questions can be answered from the model; current web lookup is an optional OpenAI tool. Uploaded text is treated as untrusted data and must not become model instructions. Conversation records are kept per user and tenant.

## Recovery and automation

Anomaly scans are scheduled by Celery Beat. Alerts become incidents for operator investigation. Recovery requires an operator request and an approver decision. The selected adapter is an allowlisted Python callable configured by the application owner; the app never runs a command string. The built-in demo adapter records a simulated result and is not a live integration with a company's pipeline.

## Deployment

`docker-compose.yml` provides PostgreSQL, Redis, web, worker and Beat services for a single-host setup. Production should use private environment secrets, HTTPS, managed database and object storage, backups, logging, and Django's deployment checklist. `runserver` and the demo adapter are for local learning only.
