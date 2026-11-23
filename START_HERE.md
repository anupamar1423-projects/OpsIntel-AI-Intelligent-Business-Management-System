# OpsIntel AI — complete project quick start

This ZIP contains two coordinated parts because the supplied project is Django while the requested analytics interface is Streamlit:

- **Django business app** (`manage.py` in this folder): accounts, organization-scoped operations, finance, procurement, document flows, reports, and the API. This is the version intended for PythonAnywhere.
- **Streamlit AI analytics app** (`streamlit_dashboard/`): interactive dashboards, pipeline anomaly detection, expense forecasting, supplier ranking, CSV analysis, and model training. This is the version intended for Streamlit Community Cloud or a Hugging Face Docker Space.

They are separate apps and databases. The Streamlit demo does not silently read private Django data. Both start with fictional records; the Streamlit pages also accept small CSV files for analysis.

## Run on Windows with VS Code or Command Prompt

### 1. Install and prepare

Install Python 3.12 and select **Add Python to PATH**. Unzip the project, open the `opsintel_ai` folder in VS Code, then run this once from its terminal:

```bat
setup_windows.bat
```

The setup installs the Django and Streamlit requirements in `.venv`, applies Django migrations, creates the generated datasets, trains both demo models, and saves evaluation metrics.

### 2. Start both apps

Open two VS Code terminals in the `opsintel_ai` folder:

```bat
run_django.bat
```

```bat
run_streamlit.bat
```

Open the Django site at <http://127.0.0.1:8000/accounts/signup/> and the Streamlit analytics site at <http://localhost:8501>. Create the first Django account to create an organization. Use Ctrl+C in each terminal to stop its server.

To add fictional records to the Django organization, create the account first, then run in another terminal:

```bat
.venv\Scripts\activate.bat
python manage.py seed_demo
```

### 3. Train the bundled datasets again

```bat
train_models.bat
```

Or run the individual commands from `streamlit_dashboard`:

```bat
python generate_dataset.py
python train_models.py
```

The generated files are:

- `streamlit_dashboard/data/operations_synthetic.csv` — 6,000 fictional pipeline runs with duration, volume, status, and an anomaly label for evaluation.
- `streamlit_dashboard/data/finance_synthetic.csv` — 60 months across five fictional departments, with expenses and budgets.
- `streamlit_dashboard/data/vendors_synthetic.csv` — fictional supplier prices and performance scores.
- `streamlit_dashboard/artifacts/` — saved model pipelines and `training_report.json` with data hashes and chronological holdout metrics.

Operations uses a scaled Isolation Forest. Its score threshold is calibrated on a separate time window; the final 20% is held out for evaluation. Finance uses a Random Forest regressor with previous-month features and a chronological holdout. Vendor ranking is a documented weighted formula because the project has no verified historical vendor outcome labels. Retrain from the Streamlit **Training center** page or the terminal script. Review false positives before using alerts; synthetic-data scores do not prove real-world accuracy.

If you later use real company CSVs, first remove names, account numbers, email addresses, and other identifying information. Do not upload confidential company data to a public demo. For operations, keep the column names shown on the **Operations AI** upload help. For finance, use `month, department, expense_amount, budget_amount`; provide continuous monthly history for each department. The app rejects missing months, negative values, invalid statuses, oversized files, and invalid numbers.

## Run checks

From the `opsintel_ai` folder:

```bat
.venv\Scripts\python.exe manage.py check
```

From `streamlit_dashboard`:

```bat
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

These check Django configuration, generated model artifacts, CSV validation, forecasts, anomaly scoring, and malformed input handling.

## Free deployment choices

| Target | App to deploy | Free status and limit |
| --- | --- | --- |
| Streamlit Community Cloud | Contents of `streamlit_dashboard/` as the repository root; entry point `app.py` | Free Streamlit hosting. Deploy from a GitHub repository; a public app/repository is visible to everyone. |
| Hugging Face Spaces + Streamlit | Contents of `streamlit_dashboard/` as the Space repository root; choose Docker | Streamlit works in a Docker Space, but current Hugging Face docs require a PRO subscription for Docker CPU compute. This is not a free path on a standard free account. |
| Hugging Face free Space | A Gradio interface using these same Python models | Could avoid Docker compute, but it would be a different UI and is not included as the Streamlit app. |
| PythonAnywhere | Django project in this folder | Free tier is suitable for a lightweight portfolio demo, within its CPU/disk limits and one-month expiry. It has one web app/worker; outbound networking is allowlisted. |

### Streamlit Community Cloud (free Streamlit deployment)

1. Create a GitHub repository for the Streamlit app. Put the **contents** of `streamlit_dashboard/` at the repository root; do not push `.venv`, secrets, or private business CSVs.
2. Sign in at [Streamlit Community Cloud](https://share.streamlit.io/) with GitHub and choose **Create app**.
3. Select the repository, branch, and `app.py` entry point, then deploy. The `requirements.txt` and Docker-independent `app_pages/` folder are already included.
4. The app contains only fictional demo records by default. On each hosted rebuild the Docker/Cloud setup regenerates training data from the deterministic script; uploaded CSVs are held only for the running session and are not a durable database.
5. If you also deploy Django, add `DJANGO_APP_URL=https://<username>.pythonanywhere.com` in the Streamlit app's settings/environment to show a link to the business app. This adds navigation only; it does not connect the two databases.

### Hugging Face Space (Streamlit Docker deployment)

1. Create a Hugging Face **Docker Space** and choose a public or private visibility deliberately. A public Space exposes its source and demo. Never publish `.env`, API tokens, the SQLite database, or private customer data.
2. Upload/push the **contents** of `streamlit_dashboard/` into the Space repository root. Its `README.md` has the Docker Space metadata and port `8501`.
   After creating the Space, the optional Windows helper can upload this folder: in Command Prompt, run `set HF_SPACE_ID=<username>/<space-name>`, authenticate once with `hf auth login`, then run `deploy_huggingface.bat` from `streamlit_dashboard/`.
3. The Docker build generates the datasets and trains the models before it starts Streamlit.
4. This path needs HF Docker CPU compute, which currently requires a PRO subscription. If you need zero-cost HF hosting, use a Gradio ZeroGPU app instead; that requires a separate UI adapter.

### PythonAnywhere (Django deployment)

The app is configured for a small SQLite demo, no paid AI key, no external database, and a slim dependency set:

1. Create a PythonAnywhere account and upload/clone this project folder to `/home/<username>/opsintel_ai`.
2. In a Bash console run:

   ```bash
   cd ~/opsintel_ai
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements-pythonanywhere.txt
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```

3. In **Web → Add a new web app**, select manual configuration and the same Python version. Set the source/working directory to `/home/<username>/opsintel_ai` and the virtualenv to `/home/<username>/opsintel_ai/.venv`.
4. Replace the WSGI file shown on the Web tab with this, substituting the account name:

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

5. Add a private `.env` beside `manage.py`:

   ```text
   SECRET_KEY=<long-random-private-value>
   DEBUG=False
   ALLOWED_HOSTS=<username>.pythonanywhere.com
   CSRF_TRUSTED_ORIGINS=https://<username>.pythonanywhere.com
   AI_PROVIDER=demo
   CELERY_TASK_ALWAYS_EAGER=True
   ```

6. In **Web → Static files**, map `/static/` to `/home/<username>/opsintel_ai/staticfiles/`. Click **Reload**, then visit `/accounts/signup/` on the assigned site URL.

The free PythonAnywhere plan has tight compute and disk limits, one web worker, and a one-month expiry. Its outbound network access is allowlisted, so the included free configuration does not depend on OpenAI, S3, or an external database. Recheck the account limits before relying on it for a live service.

## AI cost and safety notes

- The ML models are local scikit-learn models and need no API key. The assistant defaults to `AI_PROVIDER=demo` so startup does not require a paid provider. For a real LLM without API billing, you can use local Ollama on a computer that can run the model; a PythonAnywhere free web app cannot reach your laptop's local Ollama server.
- Anomaly alerts and forecasts are decision aids. They may be wrong; humans must review them. The vendor score is not a learned model.
- The Streamlit dashboard is a demo frontend, not Django authentication or a tenant-isolated API. Do not place confidential data in a public hosted app.
- “No mistakes” cannot be guaranteed for any software. This package includes migration/configuration checks, data validation, model holdout metrics, and focused unit tests to catch common failures.
