from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.validators import validate_image_file_extension
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.core.access import audit, member_for
from apps.core.notifications import notify_roles, notify_user
from apps.core.forms import EvidenceForm, IncidentForm
from apps.core.org import current_org
from .models import Pipeline, PipelineRun, Incident, IncidentEvidence, RecoveryAttempt


@login_required
def listing(request):
    org=current_org(request)
    if not org:return render(request,"no_org.html")
    return render(request,"operations.html",{
        "org":org,
        "pipelines":Pipeline.objects.filter(organization=org).order_by("name"),
        "runs":PipelineRun.objects.filter(pipeline__organization=org).select_related("pipeline").order_by("-started_at")[:40],
        "incidents":Incident.objects.filter(organization=org).select_related("pipeline","assigned_to").prefetch_related("evidence","recovery_attempts")[:40],
        "can_operate":member_for(request.user,org).role in {"org_admin","operator"},
        "can_approve":member_for(request.user,org).role in {"org_admin","approver"},
    })


@login_required
def create_incident(request):
    org=current_org(request);member=member_for(request.user,org) if org else None
    if not member or member.role not in {"org_admin","operator"}:return HttpResponseForbidden("Operator role required.")
    form=IncidentForm(request.POST or None,organization=org)
    if request.method=="POST" and form.is_valid():
        incident=Incident.objects.create(organization=org,**form.cleaned_data)
        audit(request,org,"created","Incident",incident,{"severity":incident.severity})
        notify_roles(org,{"org_admin","operator"},"New operations incident",incident.title,"/operations/")
        messages.success(request,"Incident created for your organization.")
        return redirect("operations")
    return render(request,"record_form.html",{"org":org,"form":form,"title":"Create incident"})


@login_required
def add_evidence(request, incident_id):
    org=current_org(request);member=member_for(request.user,org) if org else None
    if not member or member.role not in {"org_admin","operator"}:return HttpResponseForbidden("Operator role required.")
    incident=get_object_or_404(Incident,pk=incident_id,organization=org)
    form=EvidenceForm(request.POST or None,request.FILES or None)
    if request.method=="POST" and form.is_valid():
        f=form.cleaned_data["file"]
        try:validate_image_file_extension(f)
        except Exception:
            ext=f.name.rsplit(".",1)[-1].lower() if "." in f.name else ""
            if ext not in {"mp4","webm"}:form.add_error("file","Choose an image or an MP4/WebM video.");return render(request,"record_form.html",{"org":org,"form":form,"title":"Attach incident evidence"})
        evidence=IncidentEvidence.objects.create(incident=incident,uploaded_by=request.user,file=f,original_name=f.name,caption=form.cleaned_data["caption"],content_type=f.content_type or "application/octet-stream",size_bytes=f.size)
        audit(request,org,"evidence_attached","IncidentEvidence",evidence,{"incident_id":incident.pk,"file_name":evidence.original_name})
        messages.success(request,"Evidence attached to the incident.")
        return redirect("operations")
    return render(request,"record_form.html",{"org":org,"form":form,"title":"Attach incident image or video"})

@login_required
def download_evidence(request,evidence_id):
    org=current_org(request)
    evidence=IncidentEvidence.objects.filter(pk=evidence_id,incident__organization=org).first() if org else None
    if not evidence or not default_storage.exists(evidence.file.name):raise Http404
    try:stream=default_storage.open(evidence.file.name,"rb")
    except Exception as exc:raise Http404 from exc
    return FileResponse(stream,as_attachment=True,filename=evidence.original_name,content_type=evidence.content_type or "application/octet-stream")


@login_required
def incident_action(request, incident_id):
    org=current_org(request);member=member_for(request.user,org) if org else None
    if not member or member.role not in {"org_admin","operator"}:return HttpResponseForbidden("Operator role required.")
    if request.method!="POST":return HttpResponseForbidden("POST required.")
    incident=get_object_or_404(Incident,pk=incident_id,organization=org)
    action=request.POST.get("action")
    note=request.POST.get("note","").strip()
    if action=="investigate":incident.status="investigating"
    elif action=="resolve":
        if not note:messages.error(request,"Enter a resolution note.");return redirect("operations")
        incident.status="resolved";incident.resolved_at=timezone.now();incident.recovery_note=note
    elif action=="request_recovery":
        if not incident.pipeline or not incident.pipeline.recovery_enabled:
            messages.error(request,"Configure and enable a safe adapter on this pipeline before requesting recovery.");return redirect("operations")
        RecoveryAttempt.objects.create(incident=incident,requested_by=request.user,note=note,status="pending")
        incident.status="recovery_pending"
        audit(request,org,"recovery_requested","Incident",incident,{"note":note})
        notify_roles(org,{"org_admin","approver"},"Incident recovery requires approval",incident.title,"/operations/")
        messages.success(request,"Recovery request submitted to an approver.")
    else:return HttpResponseForbidden("Unknown incident action.")
    incident.save()
    audit(request,org,action,"Incident",incident,{"note":note})
    return redirect("operations")


@login_required
def review_recovery(request, attempt_id):
    org=current_org(request);member=member_for(request.user,org) if org else None
    if not member or member.role not in {"org_admin","approver"}:return HttpResponseForbidden("Approver role required.")
    if request.method!="POST":return HttpResponseForbidden("POST required.")
    attempt=get_object_or_404(RecoveryAttempt,pk=attempt_id,incident__organization=org,status="pending")
    decision=request.POST.get("decision");note=request.POST.get("note","").strip()
    if decision not in {"approve","reject"} or not note:
        messages.error(request,"Choose a decision and record the review reason.");return redirect("operations")
    attempt.reviewed_by=request.user;attempt.reviewed_at=timezone.now();attempt.note=(attempt.note+"\nReviewer: "+note).strip()
    incident=attempt.incident
    if decision=="reject":
        attempt.status="rejected";attempt.save();incident.status="investigating";incident.save(update_fields=["status","updated_at"])
        audit(request,org,"recovery_rejected","RecoveryAttempt",attempt,{"note":note});messages.success(request,"Recovery rejected; incident returned to investigation.")
        return redirect("operations")
    pipeline=incident.pipeline
    from django.conf import settings
    if not pipeline or not pipeline.recovery_enabled or pipeline.recovery_adapter not in settings.RECOVERY_ADAPTERS:
        messages.error(request,"This pipeline has no enabled safe recovery adapter.");return redirect("operations")
    attempt.status="queued";attempt.save();incident.status="recovery_pending";incident.save(update_fields=["status","updated_at"])
    audit(request,org,"recovery_approved","RecoveryAttempt",attempt,{"note":note})
    try:
        from .tasks import process_recovery
        process_recovery.delay(attempt.pk)
        notify_user(org,attempt.requested_by,"Recovery request reviewed","Your authorized recovery request is being processed.","/operations/")
        messages.success(request,"Approved recovery was queued for the configured adapter.")
    except Exception:
        attempt.status="failed";attempt.completed_at=timezone.now();attempt.save(update_fields=["status","completed_at"])
        incident.status="investigating";incident.save(update_fields=["status","updated_at"])
        messages.error(request,"Recovery could not be queued. Check Redis and the Celery worker.")
    return redirect("operations")
