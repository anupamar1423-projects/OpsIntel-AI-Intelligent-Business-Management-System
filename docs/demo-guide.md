# Demo walkthrough

1. Run the project and sign up to create a new organization.
2. Optionally use `python manage.py seed_demo` for fictional records.
3. Add an expense, a budget, a pipeline, a supplier image, and a purchase request from the app.
4. Sign up a second account with the organization's invite code, then set that user's role from Team.
5. Sign in as an approver and approve or return a purchase request with a note; inspect the generated PO and its delivery tracker.
6. Report an incident, attach a photo/video, request a retry, and approve it. The built-in demo retry is explicitly simulated.
7. Ask the configured AI assistant a general question and organization-specific questions. Upload a text PDF or spreadsheet and ask a question that matches its contents.
8. Create a scoped API key, submit a pipeline run, and inspect the generated incident/notification if the run fails.
9. Review organization audit history, CSV/PDF reports, and private document download behavior.

For the AI demo, configure an OpenAI API key or start Ollama. For scheduled anomaly scanning and background tasks, run Redis, a Celery worker, and Celery Beat.
