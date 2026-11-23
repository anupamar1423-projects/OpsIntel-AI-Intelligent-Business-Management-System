from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import login, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.http import FileResponse, Http404, HttpResponseForbidden, JsonResponse
from django.db import connection
from django.core.files.storage import default_storage
from django.utils import timezone
from uuid import UUID
from hashlib import sha256
from secrets import token_urlsafe
from .org import current_org
from .models import Organization, Membership, BusinessDocument, Notification, OrganizationAPIKey
from apps.finance.models import Transaction
from apps.operations.models import Pipeline,PipelineRun,Incident
from apps.procurement.models import Vendor,PurchaseRequest
from .forms import TransactionForm, PipelineForm, VendorForm, PurchaseForm, BudgetForm, DocumentForm
from apps.finance.models import Budget
from .access import member_for, audit
from .notifications import notify_roles
@login_required
def dashboard(request):
 org=current_org(request)
 if not org: return render(request,"no_org.html")
 tx=Transaction.objects.filter(organization=org); income=tx.filter(kind="income").aggregate(x=Sum("amount"))["x"] or 0; expense=tx.filter(kind="expense").aggregate(x=Sum("amount"))["x"] or 0; runs=PipelineRun.objects.filter(pipeline__organization=org)
 return render(request,"dashboard.html",{"org":org,"income":income,"expense":expense,"net":income-expense,"pipeline_count":Pipeline.objects.filter(organization=org).count(),"failed":runs.filter(status="failed").count(),"incidents":Incident.objects.filter(organization=org,status__in=["open","investigating","recovery_pending"]).count(),"vendors":Vendor.objects.filter(organization=org).count(),"pending":PurchaseRequest.objects.filter(organization=org,status="pending").count(),"runs":runs.select_related("pipeline").order_by("-started_at")[:7]})

def signup(request):
 if request.user.is_authenticated:return redirect("dashboard")
 if request.method=="POST":
  username=request.POST.get("username","").strip();email=request.POST.get("email","").strip();org_name=request.POST.get("organization","").strip();invite_code=request.POST.get("invite_code","").strip();password=request.POST.get("password","");confirm=request.POST.get("confirm_password","")
  User=get_user_model()
  try:parsed_invite=UUID(invite_code) if invite_code else None
  except ValueError:parsed_invite=None
  invited_org=Organization.objects.filter(invite_code=parsed_invite).first() if parsed_invite else None
  if not all([username,email,password]) or (not org_name and not invited_org):messages.error(request,"Enter your account details and either an organization name or a valid invite code.")
  elif password!=confirm:messages.error(request,"The passwords do not match.")
  elif User.objects.filter(username__iexact=username).exists():messages.error(request,"That username is already in use.")
  elif not invite_code and Organization.objects.filter(name__iexact=org_name).exists():messages.error(request,"That organization name is already registered. Ask an administrator for its invite code.")
  elif invite_code and not invited_org:messages.error(request,"That organization invite code is invalid.")
  else:
   try:
    validate_password(password)
    with db_transaction.atomic():
     user=User.objects.create_user(username=username,email=email,password=password)
     org=invited_org or Organization.objects.create(name=org_name)
     Membership.objects.create(user=user,organization=org,role="executive" if invited_org else "org_admin")
    login(request,user);return redirect("dashboard")
   except ValidationError as exc:messages.error(request," ".join(exc.messages))
   except Exception:messages.error(request,"We could not create the account. Check your details and try again.")
 return render(request,"signup.html")

@login_required
def create_record(request, record_type):
 org=current_org(request)
 if not org:return render(request,"no_org.html")
 forms={"transaction":TransactionForm,"budget":BudgetForm,"pipeline":PipelineForm,"vendor":VendorForm,"purchase":lambda *a,**kw:PurchaseForm(*a,organization=org,**kw)}
 titles={"transaction":"Add transaction","budget":"Set a monthly budget","pipeline":"Add pipeline","vendor":"Add vendor","purchase":"New purchase request"}
 form_class=forms.get(record_type)
 if form_class is None:return redirect("dashboard")
 member=member_for(request.user,org)
 allowed={"transaction":{"org_admin","finance"},"budget":{"org_admin","finance"},"pipeline":{"org_admin","operator"},"vendor":{"org_admin","procurement"},"purchase":{"org_admin","procurement"}}
 if not member or member.role not in allowed[record_type]:return HttpResponseForbidden("Your organization role cannot create this record.")
 form=form_class(request.POST or None,request.FILES or None)
 if request.method=="POST" and form.is_valid():
  d=form.cleaned_data
  if record_type=="transaction":obj=Transaction.objects.create(organization=org,**d)
  elif record_type=="budget":obj=Budget.objects.create(organization=org,**d)
  elif record_type=="pipeline":obj=Pipeline.objects.create(organization=org,**d)
  elif record_type=="vendor":obj=Vendor.objects.create(organization=org,**d)
  else:obj=PurchaseRequest.objects.create(organization=org,requested_by=request.user,**d)
  audit(request,org,"created",obj.__class__.__name__,obj)
  if record_type=="purchase":notify_roles(org,{"org_admin","approver"},"Purchase request needs review",obj.title,"/procurement/")
  messages.success(request,"Record saved to your organization.")
  return redirect("dashboard")
 return render(request,"record_form.html",{"org":org,"form":form,"title":titles[record_type]})

@login_required
def documents(request):
 org=current_org(request)
 if not org:return render(request,"no_org.html")
 docs=BusinessDocument.objects.filter(organization=org).select_related("uploaded_by")
 return render(request,"documents.html",{"org":org,"documents":docs})

@login_required
def upload_document(request):
 org=current_org(request)
 if not org:return render(request,"no_org.html")
 member=member_for(request.user,org)
 if not member or member.role=="executive":return HttpResponseForbidden("Your organization role is view-only.")
 form=DocumentForm(request.POST or None,request.FILES or None)
 if request.method=="POST" and form.is_valid():
  f=form.cleaned_data["file"]
  document=BusinessDocument.objects.create(organization=org,uploaded_by=request.user,file=f,original_name=f.name,category=form.cleaned_data["category"],content_type=f.content_type or "application/octet-stream",size_bytes=f.size)
  audit(request,org,"uploaded", "BusinessDocument", document, {"category":document.category,"size_bytes":document.size_bytes})
  messages.success(request,"Private organization document uploaded.")
  return redirect("documents")
 return render(request,"record_form.html",{"org":org,"form":form,"title":"Upload a private document"})

@login_required
def download_document(request, document_id):
 org=current_org(request)
 document=BusinessDocument.objects.filter(pk=document_id,organization=org).first() if org else None
 if not document or not default_storage.exists(document.file.name):raise Http404
 audit(request,org,"downloaded","BusinessDocument",document)
 try:
  stream=default_storage.open(document.file.name,"rb")
 except Exception as exc:
  raise Http404 from exc
 return FileResponse(stream,as_attachment=True,filename=document.original_name,content_type=document.content_type or "application/octet-stream")

@login_required
def switch_organization(request, organization_id):
 if request.method!="POST":return HttpResponseForbidden("POST required")
 membership=Membership.objects.filter(user=request.user,organization_id=organization_id).first()
 if not membership:return HttpResponseForbidden("You are not a member of this organization.")
 request.session["active_org_id"]=membership.organization_id
 return redirect("dashboard")

@login_required
def team(request):
 org=current_org(request);member=member_for(request.user,org) if org else None
 if not member or member.role!="org_admin":return HttpResponseForbidden("Organization admin role required.")
 if request.method=="POST":
  membership=Membership.objects.filter(pk=request.POST.get("membership_id"),organization=org).select_related("user").first()
  action=request.POST.get("action")
  if not membership:return HttpResponseForbidden("Membership not found in this organization.")
  if membership.user_id==request.user.id and action in {"remove","role"}:messages.error(request,"You cannot remove or change your own admin membership.")
  elif action=="remove":
   audit(request,org,"member_removed","Membership",membership,{"user":membership.user.username});membership.delete();messages.success(request,"Member removed from this organization.")
  elif action=="role":
   role=request.POST.get("role")
   if role not in dict(Membership.ROLES):return HttpResponseForbidden("Invalid organization role.")
   old=membership.role;membership.role=role;membership.save(update_fields=["role"]);audit(request,org,"role_changed","Membership",membership,{"from":old,"to":role});messages.success(request,"Organization role updated.")
  return redirect("team")
 return render(request,"team.html",{"org":org,"members":Membership.objects.filter(organization=org).select_related("user"),"roles":Membership.ROLES})

@login_required
def notifications(request):
 org=current_org(request)
 if not org:return render(request,"no_org.html")
 qs=Notification.objects.filter(organization=org,recipient=request.user)
 if request.method=="POST":
  qs.filter(read_at__isnull=True).update(read_at=timezone.now())
  return redirect("notifications")
 return render(request,"notifications.html",{"org":org,"items":qs[:80]})

@login_required
def audit_log(request):
 org=current_org(request)
 if not org:return render(request,"no_org.html")
 return render(request,"audit.html",{"org":org,"events":org.audit_events.select_related("actor")[:200]})

def health_check(request):
 try:connection.ensure_connection()
 except Exception:return JsonResponse({"status":"unavailable"},status=503)
 return JsonResponse({"status":"ok"})

@login_required
def api_keys(request):
 org=current_org(request);member=member_for(request.user,org) if org else None
 if not member or member.role!="org_admin":return HttpResponseForbidden("Organization admin role required.")
 new_key=None
 if request.method=="POST" and request.POST.get("revoke_id"):
  key=OrganizationAPIKey.objects.filter(pk=request.POST["revoke_id"],organization=org,revoked_at__isnull=True).first()
  if key:key.revoked_at=timezone.now();key.save(update_fields=["revoked_at"]);audit(request,org,"api_key_revoked","OrganizationAPIKey",key);messages.success(request,"API key revoked.")
  return redirect("api-keys")
 if request.method=="POST":
  label=request.POST.get("label","Pipeline integration").strip()[:80] or "Pipeline integration"
  token="ops_"+token_urlsafe(36)
  key=OrganizationAPIKey.objects.create(organization=org,label=label,prefix=token[:12],token_hash=sha256(token.encode()).hexdigest(),created_by=request.user)
  audit(request,org,"api_key_created","OrganizationAPIKey",key,{"label":label,"prefix":key.prefix})
  new_key=token
 return render(request,"api_keys.html",{"org":org,"keys":org.api_keys.all(),"new_key":new_key})
