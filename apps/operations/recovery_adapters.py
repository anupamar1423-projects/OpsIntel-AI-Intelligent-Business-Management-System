def demo_retry(pipeline, incident, attempt):
    """Safe illustration only. Replace with an idempotent organization-owned retry handler."""
    previous=pipeline.runs.order_by("-started_at").first()
    return {"success":True,"rows_processed":previous.rows_processed if previous else 0,"detail":"Safe demo adapter completed; no external pipeline was executed."}
