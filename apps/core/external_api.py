from datetime import timedelta
from hashlib import sha256
import math

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .models import OrganizationAPIKey, AuditEvent
from .notifications import notify_roles
from apps.operations.models import Pipeline, PipelineRun, Incident


class PipelineRunIngest(APIView):
    authentication_classes=[]
    permission_classes=[AllowAny]

    def post(self,request):
        raw=request.headers.get("Authorization","")
        if not raw.startswith("Bearer "):
            return Response({"detail":"Use Authorization: Bearer <organization-api-key>."},status=status.HTTP_401_UNAUTHORIZED)
        token=raw[7:].strip()
        key=OrganizationAPIKey.objects.filter(prefix=token[:12],token_hash=sha256(token.encode()).hexdigest(),revoked_at__isnull=True).select_related("organization").first()
        if not key:
            return Response({"detail":"API key is invalid or revoked."},status=status.HTTP_401_UNAUTHORIZED)
        try:pipeline_id=int(request.data.get("pipeline_id"))
        except (TypeError,ValueError):return Response({"pipeline_id":"A valid pipeline id is required."},status=status.HTTP_400_BAD_REQUEST)
        pipeline=Pipeline.objects.filter(pk=pipeline_id,organization=key.organization,active=True).first()
        if not pipeline:return Response({"pipeline_id":"Pipeline is not active in this organization."},status=status.HTTP_404_NOT_FOUND)
        run_status=request.data.get("status","success")
        if run_status not in {"success","failed","running"}:return Response({"status":"Choose success, failed, or running."},status=status.HTTP_400_BAD_REQUEST)
        try:duration=float(request.data.get("duration_minutes",0));rows=int(request.data.get("rows_processed",0))
        except (TypeError,ValueError):return Response({"metrics":"Duration and row count must be numbers."},status=status.HTTP_400_BAD_REQUEST)
        if not math.isfinite(duration) or duration<0 or rows<0:return Response({"metrics":"Duration and row count must be non-negative finite values."},status=status.HTTP_400_BAD_REQUEST)
        started=parse_datetime(str(request.data.get("started_at",""))) if request.data.get("started_at") else timezone.now()
        if started is None:return Response({"started_at":"Use an ISO-8601 datetime."},status=status.HTTP_400_BAD_REQUEST)
        if timezone.is_naive(started):started=timezone.make_aware(started)
        detail=str(request.data.get("detail",""))[:4000]
        now=timezone.now()
        run=PipelineRun.objects.create(pipeline=pipeline,started_at=started,finished_at=None if run_status=="running" else started+timedelta(minutes=duration),duration_minutes=duration,status=run_status,rows_processed=rows,detail=detail)
        key.last_used_at=now;key.save(update_fields=["last_used_at"])
        AuditEvent.objects.create(organization=key.organization,action="pipeline_run_ingested",entity_type="PipelineRun",entity_id=str(run.pk),detail={"status":run_status,"pipeline":pipeline.name},ip_address=request.META.get("REMOTE_ADDR"))
        incident_id=None
        if run_status=="failed":
            title=f"External pipeline failure: {pipeline.name} run {run.pk}"
            incident,created=Incident.objects.get_or_create(organization=key.organization,pipeline=pipeline,title=title,defaults={"severity":"high","detail":detail or "External integration reported a failed pipeline run."})
            incident_id=incident.pk
            if created:notify_roles(key.organization,{"org_admin","operator"},"Pipeline run failed",title,"/operations/")
        return Response({"run_id":run.pk,"pipeline":pipeline.name,"status":run_status,"incident_id":incident_id},status=status.HTTP_201_CREATED)
