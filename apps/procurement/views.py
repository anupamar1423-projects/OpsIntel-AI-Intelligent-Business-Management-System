import uuid
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from django.utils import timezone
from pathlib import Path
from django.db import transaction

from apps.core.access import audit, member_for
from apps.core.org import current_org
from apps.core.notifications import notify_user
from .models import Vendor, PurchaseRequest, PurchaseOrder


@login_required
def listing(request):
    org=current_org(request)
    if not org:return render(request,"no_org.html")
    return render(request,"procurement.html",{
        "title":"Procurement","org":org,
        "vendors":Vendor.objects.filter(organization=org).order_by("-reliability"),
        "requests":PurchaseRequest.objects.filter(organization=org).select_related("preferred_vendor","requested_by","reviewed_by").order_by("-created_at"),
        "orders":PurchaseOrder.objects.filter(request__organization=org).select_related("request","vendor").order_by("-issued_at"),
        "can_approve":member_for(request.user,org).role in {"org_admin","approver"},
        "can_procure":member_for(request.user,org).role in {"org_admin","procurement"},
        "order_status_choices":PurchaseOrder.STATUS,
    })

@login_required
def product_image(request,vendor_id):
    org=current_org(request)
    vendor=get_object_or_404(Vendor,pk=vendor_id,organization=org)
    if not vendor.product_image or not default_storage.exists(vendor.product_image.name):raise Http404
    try:stream=default_storage.open(vendor.product_image.name,"rb")
    except Exception as exc:raise Http404 from exc
    mime={".jpg":"image/jpeg",".jpeg":"image/jpeg",".png":"image/png",".webp":"image/webp"}.get(Path(vendor.product_image.name).suffix.lower(),"application/octet-stream")
    response=FileResponse(stream,content_type=mime);response["X-Content-Type-Options"]="nosniff";response["Content-Disposition"]="inline"
    return response


@login_required
@transaction.atomic
def review_request(request, request_id):
    org=current_org(request)
    member=member_for(request.user,org) if org else None
    if not member or member.role not in {"org_admin","approver"}:return HttpResponseForbidden("Approver role required.")
    purchase=get_object_or_404(PurchaseRequest,pk=request_id,organization=org,status="pending")
    if request.method!="POST":return HttpResponseForbidden("POST required.")
    decision=request.POST.get("decision")
    note=request.POST.get("note","").strip()
    if decision not in {"approve","reject","return"} or not note:
        messages.error(request,"Choose a valid decision and enter an audit note.")
        return redirect("procurement")
    if decision=="approve":
        if not purchase.preferred_vendor or purchase.preferred_vendor.organization_id!=org.id:
            messages.error(request,"Select an approved vendor from this organization before approval.")
            return redirect("procurement")
        purchase.status="approved"
        po=PurchaseOrder.objects.create(request=purchase,vendor=purchase.preferred_vendor,order_number=f"OP-{org.pk}-{uuid.uuid4().hex[:8].upper()}")
        audit(request,org,"approved","PurchaseRequest",purchase,{"note":note,"purchase_order":po.order_number})
        messages.success(request,f"Request approved. Purchase order {po.order_number} created.")
    else:
        purchase.status="rejected" if decision=="reject" else "returned"
        audit(request,org,purchase.status,"PurchaseRequest",purchase,{"note":note})
        messages.success(request,f"Request {purchase.status} with the recorded reason.")
    purchase.reviewed_by=request.user;purchase.reviewed_at=timezone.now();purchase.approval_note=note
    purchase.save(update_fields=["status","reviewed_by","reviewed_at","approval_note"])
    notify_user(org,purchase.requested_by,f"Purchase request {purchase.status}",note,"/procurement/")
    return redirect("procurement")


@login_required
def update_order(request, order_id):
    org=current_org(request);member=member_for(request.user,org) if org else None
    if not member or member.role not in {"org_admin","procurement"}:return HttpResponseForbidden("Procurement role required.")
    order=get_object_or_404(PurchaseOrder,pk=order_id,request__organization=org)
    if request.method!="POST":return HttpResponseForbidden("POST required.")
    status=request.POST.get("status")
    if status not in dict(PurchaseOrder.STATUS):return HttpResponseForbidden("Invalid order status.")
    order.status=status
    order.tracking_reference=request.POST.get("tracking_reference","").strip()[:120]
    raw_date=request.POST.get("expected_delivery","").strip()
    if raw_date:
        try:order.expected_delivery=date.fromisoformat(raw_date)
        except ValueError:messages.error(request,"Expected delivery date is invalid.");return redirect("procurement")
    if status=="delivered":order.actual_delivery=date.today()
    order.save(update_fields=["status","tracking_reference","expected_delivery","actual_delivery"])
    audit(request,org,"updated_delivery","PurchaseOrder",order,{"status":status,"tracking_reference":order.tracking_reference})
    notify_user(org,order.request.requested_by,f"Order {order.order_number} updated",f"Delivery status: {order.get_status_display()}","/procurement/")
    messages.success(request,"Purchase order delivery status updated.")
    return redirect("procurement")
