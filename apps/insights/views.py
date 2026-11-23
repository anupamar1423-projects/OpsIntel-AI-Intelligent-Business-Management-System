from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Sum
from apps.core.org import current_org
from apps.finance.models import Transaction
from apps.operations.models import Incident,PipelineRun
from apps.core.models import AssistantMessage
from apps.procurement.models import Vendor,PurchaseRequest,PurchaseOrder
from apps.finance.models import Budget
from django.contrib import messages
from django.conf import settings
from .services import detect_anomalies,forecast
from .assistant import answer
from .retrieval import relevant_documents
@login_required
def home(request):
 o=current_org(request);tx=list(Transaction.objects.filter(organization=o)) if o else [];return render(request,"insights.html",{"org":o,"anomalies":detect_anomalies(o) if o else [],"forecast":forecast(tx),"runs":PipelineRun.objects.filter(pipeline__organization=o).count() if o else 0})
@login_required
def assistant(request):
 o=current_org(request);facts={"organization":o.name if o else "","finance":{},"operations":{},"procurement":{}};response=None;provider=None
 if o:
  q=Transaction.objects.filter(organization=o);runs=PipelineRun.objects.filter(pipeline__organization=o); incidents=Incident.objects.filter(organization=o);reqs=PurchaseRequest.objects.filter(organization=o)
  facts["finance"]={"income_total":float(q.filter(kind="income").aggregate(x=Sum("amount"))["x"] or 0),"expense_total":float(q.filter(kind="expense").aggregate(x=Sum("amount"))["x"] or 0),"transaction_count":q.count(),"budgets":[{"month":str(b.month),"department":b.department,"amount":float(b.amount)} for b in Budget.objects.filter(organization=o).order_by("-month")[:12]]}
  facts["operations"]={"pipeline_count":runs.values("pipeline_id").distinct().count(),"run_count":runs.count(),"failed_runs":runs.filter(status="failed").count(),"open_incidents":incidents.filter(status__in=["open","investigating","recovery_pending"]).count(),"recent_incidents":list(incidents.filter(status__in=["open","investigating","recovery_pending"]).values("title","severity","status")[:10])}
  facts["procurement"]={"vendors":[{"name":v.name,"category":v.category,"unit_price":float(v.unit_price),"reliability":v.reliability,"on_time_rate":v.on_time_rate,"score":v.score} for v in Vendor.objects.filter(organization=o,approved=True).order_by("-reliability")[:10]],"requests":{"pending":reqs.filter(status="pending").count(),"approved":reqs.filter(status="approved").count(),"rejected":reqs.filter(status="rejected").count()},"purchase_orders":{"in_transit":PurchaseOrder.objects.filter(request__organization=o,status="in_transit").count(),"delivered":PurchaseOrder.objects.filter(request__organization=o,status="delivered").count()}}
 if request.method=="POST" and o:
  question=request.POST.get("question","").strip()
  if not question:messages.error(request,"Type a question first.")
  elif len(question)>4000:messages.error(request,"Please keep a question under 4,000 characters.")
  else:
   previous=list(AssistantMessage.objects.filter(organization=o,user=request.user).order_by("-created_at")[:6]);history=[]
   for item in reversed(previous):history.extend([{"role":"user","content":item.question},{"role":"assistant","content":item.answer}])
   try:
    facts["relevant_files"]=relevant_documents(o,question)
    response,provider=answer(question,o.name,facts,history)
    AssistantMessage.objects.create(organization=o,user=request.user,question=question,answer=response,provider=provider)
   except Exception:messages.error(request,"The AI provider did not return an answer. Check AI_PROVIDER, its required key or local service, network access, and the model name in .env.")
 return render(request,"assistant.html",{"org":o,"response":response,"provider":provider,"ai_provider":settings.AI_PROVIDER,"question":request.POST.get("question","") if request.method=="POST" else "","history":AssistantMessage.objects.filter(organization=o,user=request.user).order_by("-created_at")[:10] if o else []})
