from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.validators import FileExtensionValidator, MaxValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import Organization


def evidence_path(instance, filename):
    return f"organizations/{instance.incident.organization_id}/incidents/{instance.incident_id}/{uuid4().hex}{Path(filename).suffix.lower()}"


class Pipeline(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="pipelines")
    name = models.CharField(max_length=120)
    expected_minutes = models.PositiveIntegerField(default=10)
    active = models.BooleanField(default=True)
    retry_limit = models.PositiveSmallIntegerField(default=2, validators=[MaxValueValidator(5)])
    recovery_enabled = models.BooleanField(default=False)
    recovery_adapter = models.CharField(max_length=24, choices=[("none","Not configured"),("demo","Safe demo retry")], default="none")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class PipelineRun(models.Model):
    STATUS = [("success", "Success"), ("failed", "Failed"), ("running", "Running")]
    pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE, related_name="runs")
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.FloatField(default=0)
    status = models.CharField(max_length=12, choices=STATUS, default="success")
    rows_processed = models.PositiveIntegerField(default=0)
    detail = models.TextField(blank=True)
    attempt = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return f"{self.pipeline} · {self.get_status_display()} · {self.started_at:%Y-%m-%d %H:%M}"


class Incident(models.Model):
    SEVERITY = [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")]
    STATUS = [("open", "Open"), ("investigating", "Investigating"), ("recovery_pending", "Recovery pending"), ("resolved", "Resolved")]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="incidents")
    pipeline = models.ForeignKey(Pipeline, null=True, blank=True, on_delete=models.SET_NULL, related_name="incidents")
    title = models.CharField(max_length=160)
    severity = models.CharField(max_length=10, choices=SEVERITY, default="medium")
    status = models.CharField(max_length=20, choices=STATUS, default="open", db_index=True)
    detail = models.TextField(blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_incidents")
    recovery_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints=[models.UniqueConstraint(fields=["organization","pipeline","title"],name="uniq_incident_org_pipeline_title")]

    def __str__(self):
        return self.title


class IncidentEvidence(models.Model):
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="evidence")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    file = models.FileField(upload_to=evidence_path, validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp", "mp4", "webm"])])
    original_name = models.CharField(max_length=255)
    caption = models.CharField(max_length=240, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class RecoveryAttempt(models.Model):
    STATUS = [("pending", "Pending approval"), ("queued", "Queued"), ("running", "Running"), ("succeeded", "Succeeded"), ("failed", "Failed"), ("rejected", "Rejected")]
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="recovery_attempts")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="recovery_requests")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="recovery_reviews")
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
