# OpsIntel AI

OpsIntel AI is a Django business-operations application based on the supplied synopsis. It includes tenant-scoped operations and finance records, pipeline anomaly detection, incident workflows, vendor scoring, purchase approvals and order tracking, private file storage, audit events, alerts, an LLM business assistant, a JSON ingestion API, and scheduled Celery tasks.

## Run on Windows with Command Prompt

Install Python 3.12 from [python.org](https://www.python.org/downloads/windows/) and select **Add Python to PATH**. Extract the ZIP, open Command Prompt or the VS Code terminal, and change directory to the extracted `opsintel_ai` folder (the folder containing `manage.py`).

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000/accounts/signup/ and create an account. The first registrant can create an organization and becomes its organization admin. Normal sign-up does **not** need `createsuperuser`. Keep the Command Prompt window open while using the app; press Ctrl+C to stop the server.

The ZIP contains initial database migrations, so the first setup only needs `migrate`. Run `python manage.py makemigrations` when you change Django models later.

### Optional demo records

Create your browser account first. In another Command Prompt, activate the virtual environment, then run:

```bat
.venv\Scripts\activate.bat
python manage.py seed_demo
```

This adds fictional pipeline, finance, supplier and incident records to the first registered account's organization.

## Live AI assistant

The assistant uses a model provider at question time. It can answer general questions and can use the active organization's finance, operations, vendor, purchase-order and document context. Organization queries are filtered to that organization. It does not approve requests or run recovery actions. Provider output can be wrong; verify business decisions.

### OpenAI provider

The default `demo` provider keeps the site usable without a paid API. To use a live model locally at no API cost, install [Ollama](https://ollama.com/download/windows/) and use the local setup below. OpenAI is optional and can incur API usage charges. Add values to `.env` only if you choose it:

```text
AI_PROVIDER=openai
OPENAI_API_KEY=your-private-key
OPENAI_MODEL=gpt-5-mini
OPENAI_WEB_SEARCH=False
```

Restart the Django server after editing `.env`. The app uses the OpenAI Responses API; it sends the question, a small set of organization-scoped summaries, and up to three relevant text-document excerpts. The request uses `store=False`. Enable `OPENAI_WEB_SEARCH=True` if you want the provider to use current web search. See the [Responses API reference](https://developers.openai.com/api/reference/resources/responses/methods/create) and [text generation guide](https://developers.openai.com/api/docs/guides/text).

### Local Ollama provider

Install Ollama from [ollama.com](https://ollama.com/download/windows/), then in Command Prompt run:

```bat
ollama pull llama3.2
```

Set `AI_PROVIDER=ollama` in `.env`, leave Ollama running, and restart Django. Ollama runs locally; answer quality and latency depend on the selected local model and your computer.

`AI_PROVIDER=demo` returns a setup note rather than model-generated answers; it is the no-key default. The separate Streamlit analytics app includes trained local ML models that work offline.

## Images, video and business files

Media is part of the workflows rather than a stock-photo gallery:

- Add a vendor product image in Procurement. Image files are served through an organization-checked view.
- Attach incident evidence in Operations. Operators can upload JPG, PNG, WebP, MP4 or WebM files; access is organization-scoped.
- Upload invoices, spreadsheets, PDFs and vendor or purchase documents in Documents. Files download through an authenticated organization check.
- Local development stores uploads under `media/`. Set `USE_S3=True` and S3 credentials to use private S3-compatible object storage instead.

Uploads are limited to 50 MB in the app. A production web server should also set its request-body limit, scan uploads if appropriate, and back up object storage. Django warns that uploaded files are untrusted; see its [file upload security guidance](https://docs.djangoproject.com/en/5.2/topics/security/#user-uploaded-content).

## Main features

- Organization sign-up, invite-code joining, membership roles, organization switching, and tenant-scoped queries.
- Pipeline records, external run ingestion, Isolation Forest alerts, operator incident investigation, and evidence attachments.
- Human-approved recovery requests. The built-in `demo` adapter is explicitly a simulation; production integrations must register an organization-owned Celery adapter in `RECOVERY_ADAPTERS_JSON`. The app never executes arbitrary shell commands.
- Income/expense transactions, budgets, financial summaries and basic monthly expense projection.
- Vendor reliability and delivery score, purchase request approvals with notes, purchase-order creation, tracking reference and delivery status.
- Organization-private document vault using local storage or Boto3-backed S3 storage.
- OpenAI or Ollama assistant, conversation history, text retrieval from PDF, DOCX, CSV and XLSX uploads, and optional OpenAI web search.
- Audit history, role-aware notifications, authenticated CSV/PDF reports and a tenant-scoped external pipeline API.
- A dashboard that refreshes KPI data every 10 seconds. This is polling, not a WebSocket push connection.
- Celery tasks for recovery and a scheduled anomaly scan every five minutes when Celery Beat and Redis are running.

## S3 / Boto3 configuration

Boto3 and `django-storages` are installed by `requirements.txt`; no separate Boto3 installer is needed. Create a private bucket and credentials with AWS or another S3-compatible provider. Add to `.env`:

```text
USE_S3=True
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=your-private-bucket
AWS_S3_REGION_NAME=your-region
AWS_S3_ENDPOINT_URL=
```

For MinIO, set `AWS_S3_ENDPOINT_URL` to its endpoint. Do not commit `.env` or expose credentials in screenshots. The app keeps S3 objects private and returns organization-checked downloads.

## PostgreSQL, Redis and background workers

`requirements.txt` includes the PostgreSQL driver and Celery packages. For a local Windows SQLite setup, PostgreSQL and Redis are optional. For asynchronous recovery and scheduled anomaly scans, run Redis plus a Celery worker and Beat process:

```bat
celery -A config worker -l info
```

In a second Command Prompt:

```bat
celery -A config beat -l info
```

Set `REDIS_URL` in `.env`. For production set `CELERY_TASK_ALWAYS_EAGER=False`; configure a worker and Beat service against the same database and Redis broker. The default local `.env.example` runs Celery tasks eagerly for a simple demo.

## External pipeline API

An organization admin creates/revokes a key under **Team → Manage integration API keys**. The raw key is shown once. Send `POST /api/v1/pipeline-runs/` with `Authorization: Bearer <key>` and JSON containing `pipeline_id`, `status` (`success`, `failed`, or `running`), `duration_minutes`, and `rows_processed`. Failed runs create an incident and notify operators. The key is hashed at rest and scoped to one organization. Example CMD request is shown on the API key page.

## Docker deployment

Install Docker Desktop, copy `.env.example` to `.env`, and configure `SECRET_KEY` and any AI settings. For local PostgreSQL, Redis, web, Celery worker and Beat:

```bat
docker compose up --build -d
docker compose logs -f web
```

Then sign up at http://127.0.0.1:8000/accounts/signup/. Stop the stack with `docker compose down`; persistent local database and uploads remain in named volumes. `docker compose down -v` removes those volumes and their data.

## Deploy to Render

1. Push the project to a private GitHub repository; never commit `.env`.
2. Create a managed PostgreSQL database and a web service. Build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`.
3. Start command: `gunicorn config.wsgi:application`.
4. Set `SECRET_KEY` to a generated private value, `DEBUG=False`, `ALLOWED_HOSTS=your-service.onrender.com`, `CSRF_TRUSTED_ORIGINS=https://your-service.onrender.com`, and `DATABASE_URL` to the Render PostgreSQL URL.
5. Configure private S3 storage for durable uploaded files. Add managed Redis, a Celery worker and a Celery Beat service for asynchronous recovery and scheduled anomaly scans. Add `OPENAI_API_KEY` as a secret only if using OpenAI.
6. Set up database backups, object-store lifecycle/backup, error monitoring and a process for key rotation. Run Django's deployment check and review its [deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/) before exposing the service.

Do not deploy with `DEBUG=True`, the development secret, a public upload bucket, or the built-in demo recovery adapter for real pipeline work.

## Streamlit and Hugging Face deployment

The Streamlit app lives in `streamlit_dashboard/`; deploy that folder as its own app. The Space is configured as a Docker Streamlit app on port 8501. Current Hugging Face documentation says Docker/CPU Spaces require a PRO subscription, so this route is **not free** on a standard free account. The free Hugging Face ZeroGPU route is Gradio-based and would require a different UI. For free Streamlit hosting, use Streamlit Community Cloud; see `START_HERE.md` for both routes and the exact steps.

The Django business application is separate and can be deployed to PythonAnywhere. The Streamlit demo uses generated sample data and uploaded CSVs within its own runtime; it does not share the Django database automatically.

## Deploy Django to PythonAnywhere

PythonAnywhere hosts the Django app through its **Web** tab and WSGI configuration. For a small demo, SQLite and local media can work; back up the database and uploaded files. For persistent production use, configure a managed PostgreSQL service and private S3-compatible storage.

1. Upload or clone this folder to `/home/<username>/opsintel_ai` on PythonAnywhere. In a Bash console, create a virtual environment using the same Python version selected for the web app, then install the free-tier dependency set:

   ```bash
   cd ~/opsintel_ai
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements-pythonanywhere.txt
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```

2. In **Web → Add a new web app**, choose **Manual configuration** and the matching Python version. Set the source and working directories to `/home/<username>/opsintel_ai`, and virtualenv to `/home/<username>/opsintel_ai/.venv`.
3. Edit the WSGI configuration file shown on the Web tab. Replace its contents with:

   ```python
   import os
   import sys
   project = "/home/<username>/opsintel_ai"
   if project not in sys.path:
       sys.path.insert(0, project)
   os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```

   Replace `<username>` with the actual account name. Put `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS=<username>.pythonanywhere.com`, `CSRF_TRUSTED_ORIGINS=https://<username>.pythonanywhere.com`, `AI_PROVIDER=demo`, and `CELERY_TASK_ALWAYS_EAGER=True` in a private `.env` file beside `manage.py`; `.env` is ignored by Git. The eager task setting avoids needing Redis on the free tier.
4. In **Web → Static files**, map `/static/` to `/home/<username>/opsintel_ai/staticfiles/`. Do not map `/private-media/` directly to the filesystem; downloads go through organization-checked views.
5. Click **Reload** on the Web tab. Open `/accounts/signup/` on the site and create the first organization.

The free PythonAnywhere account has strict storage/CPU limits and a one-month expiry. Free-account outbound networking is allowlisted, so do not rely on OpenAI/Ollama/S3 API calls there. The supplied minimal requirements intentionally use SQLite and the no-key assistant mode; optional ML falls back to simple statistics. See `START_HERE.md` for the current plan note and alternatives.

## Routes

Sign-up `/accounts/signup/`; dashboard `/`; Operations `/operations/`; Finance `/finance/`; Procurement `/procurement/`; AI insights `/insights/`; assistant `/insights/assistant/`; documents `/documents/`; team `/organizations/team/`; audit `/audit/`; alerts `/notifications/`; API keys `/organizations/api-keys/`; summary API `/api/summary/`; pipeline ingest API `/api/v1/pipeline-runs/`; CSV `/reports/transactions.csv`; PDF `/reports/summary.pdf`.

## Scope and limitations

This is a substantial educational/portfolio implementation, not a certified accounting system or audited enterprise SaaS service. Forecasts and anomaly alerts are decision aids. Real recovery requires an adapter that invokes your organization's authorized pipeline code. Review file scanning, retention, email delivery, backup, role design, rate limiting and production infrastructure before using confidential or financial data.
