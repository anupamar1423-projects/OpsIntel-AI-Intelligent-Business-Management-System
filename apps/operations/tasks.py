from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.utils.module_loading import import_string
from apps.core.models import AuditEvent
from apps.core.notifications import notify_roles, notify_user
from .models import Incident, PipelineRun, RecoveryAttempt

@shared_task(bind=True, autoretry_for=(ConnectionError,), retry_backoff=True, max_retries=3)
def process_recovery(self, attempt_id):
    with transaction.atomic():
        attempt=RecoveryAttempt.objects.select_for_update().select_related("incident__pipeline","reviewed_by").get(pk=attempt_id)
        if attempt.status!="queued":return attempt.status
        incident=attempt.incident;pipeline=incident.pipeline
        if not pipeline or not pipeline.recovery_enabled or pipeline.recovery_adapter not in settings.RECOVERY_ADAPTERS:
            attempt.status="failed";attempt.note=(attempt.note+"\nNo safe recovery adapter is configured.").strip();attempt.completed_at=timezone.now();attempt.save()
            incident.status="investigating";incident.save(update_fields=["status","updated_at"])
            return "failed"
        if incident.recovery_attempts.exclude(status="rejected").count()>pipeline.retry_limit:
            attempt.status="failed";attempt.note=(attempt.note+"\nRetry limit reached.").strip();attempt.completed_at=timezone.now();attempt.save()
            incident.status="investigating";incident.save(update_fields=["status","updated_at"])
            return "failed"
        attempt.status="running";attempt.save(update_fields=["status"])
    try:
        adapter=import_string(settings.RECOVERY_ADAPTERS[pipeline.recovery_adapter])
        result=adapter(pipeline,incident,attempt)
        if not isinstance(result,dict) or "success" not in result:raise ValueError("Recovery adapters must return a success boolean")
        now=timezone.now()
        succeeded=bool(result["success"])
        PipelineRun.objects.create(pipeline=pipeline,started_at=now,finished_at=now,duration_minutes=0,status="success" if succeeded else "failed",rows_processed=max(0,int(result.get("rows_processed",0))),detail=str(result.get("detail",""))[:4000],attempt=attempt.incident.recovery_attempts.count()+1)
        attempt.status="succeeded" if succeeded else "failed";attempt.completed_at=now;attempt.save(update_fields=["status","completed_at"])
        incident.status="resolved" if succeeded else "investigating";incident.resolved_at=now if succeeded else None;incident.recovery_note=str(result.get("detail",""))[:4000];incident.save(update_fields=["status","resolved_at","recovery_note","updated_at"])
        if attempt.reviewed_by:AuditEvent.objects.create(organization=incident.organization,actor=attempt.reviewed_by,action="recovery_succeeded" if succeeded else "recovery_failed",entity_type="Incident",entity_id=str(incident.pk),detail={"attempt_id":attempt.pk})
        try:notify_user(incident.organization,attempt.requested_by,"Recovery completed" if succeeded else "Recovery failed",incident.title,"/operations/")
        except Exception:pass
        return "succeeded" if succeeded else "failed"
    except Exception as exc:
        RecoveryAttempt.objects.filter(pk=attempt_id).update(status="failed",completed_at=timezone.now(),note=f"{attempt.note}\nAdapter error: {type(exc).__name__}")
        Incident.objects.filter(pk=incident.pk).update(status="investigating")
        raise

@shared_task
def scan_all_organizations():
    from apps.core.models import Organization
    from apps.insights.services import detect_anomalies
    created=0
    for org in Organization.objects.all().iterator():
        for run,score,reason in detect_anomalies(org):
            title=f"Anomaly detected: {run.pipeline.name} run {run.pk}"
            incident,was_created=Incident.objects.get_or_create(organization=org,pipeline=run.pipeline,title=title,defaults={"severity":"high" if run.status=="failed" else "medium","detail":f"{reason}. Anomaly score {score:.3f}; review before recovery."})
            if was_created:notify_roles(org,{"org_admin","operator"},"Pipeline anomaly detected",incident.title,"/operations/")
            created+=int(was_created)
    return created
