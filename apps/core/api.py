from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum
from .org import current_org
from apps.finance.models import Transaction
from apps.operations.models import Incident
from apps.operations.models import Pipeline,PipelineRun
from apps.procurement.models import Vendor,PurchaseRequest
@login_required
def summary(request):
 org=current_org(request)
 if not org:return JsonResponse({"detail":"No organization membership"},status=403)
 q=Transaction.objects.filter(organization=org)
 runs=PipelineRun.objects.filter(pipeline__organization=org)
 return JsonResponse({"organization":org.name,"income":float(q.filter(kind="income").aggregate(x=Sum("amount"))["x"] or 0),"expenses":float(q.filter(kind="expense").aggregate(x=Sum("amount"))["x"] or 0),"open_incidents":Incident.objects.filter(organization=org,status__in=["open","investigating","recovery_pending"]).count(),"pipeline_count":Pipeline.objects.filter(organization=org).count(),"failed":runs.filter(status="failed").count(),"vendors":Vendor.objects.filter(organization=org).count(),"pending":PurchaseRequest.objects.filter(organization=org,status="pending").count()})
