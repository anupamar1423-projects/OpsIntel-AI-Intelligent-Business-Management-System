from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import Membership
from apps.finance.models import Budget, Transaction
from apps.operations.models import Incident, Pipeline, PipelineRun
from apps.procurement.models import PurchaseRequest, Vendor


class Command(BaseCommand):
    help="Add fictional demonstration records to the first registered user's organization."

    def handle(self,*args,**kwargs):
        user=get_user_model().objects.order_by("pk").first()
        if not user:
            self.stderr.write("Create an account in the browser first, then run this command.")
            return
        membership=Membership.objects.filter(user=user).select_related("organization").first()
        if not membership:
            self.stderr.write("The first account has no organization membership.")
            return
        org=membership.organization
        names=["Daily Revenue Sync","Supplier Data Import","Inventory Reconciliation"]
        for name in names:
            pipeline,_=Pipeline.objects.get_or_create(organization=org,name=name)
            if name=="Supplier Data Import" and not pipeline.recovery_enabled:
                pipeline.recovery_enabled=True;pipeline.recovery_adapter="demo";pipeline.save(update_fields=["recovery_enabled","recovery_adapter"])
            if not pipeline.runs.exists():
                for index in range(12):
                    failed=index==9 and name=="Supplier Data Import"
                    long_run=index==11 and name=="Daily Revenue Sync"
                    PipelineRun.objects.create(pipeline=pipeline,started_at=timezone.now()-timedelta(days=12-index),duration_minutes=39 if long_run else 7+(index%4)*2,status="failed" if failed else "success",rows_processed=1200+index*53,detail="Fictional demo data")
        supplier=Pipeline.objects.filter(organization=org,name="Supplier Data Import").first()
        Incident.objects.get_or_create(organization=org,pipeline=supplier,title="Delayed supplier import",defaults={"severity":"high","detail":"Fictional sample incident for response workflow practice."})
        vendors=[]
        for name,price,reliability,on_time in [("Aster Supply",48000,94,92),("BluePeak Traders",42500,78,72),("CedarWorks",51000,98,97)]:
            vendor,_=Vendor.objects.get_or_create(organization=org,name=name,defaults={"category":"Equipment","unit_price":price,"reliability":reliability,"on_time_rate":on_time})
            vendors.append(vendor)
        if not Transaction.objects.filter(organization=org).exists():
            for index in range(8):
                Transaction.objects.create(organization=org,kind="income" if index%3==0 else "expense",category=["Sales","Cloud","Payroll","Travel"][index%4],amount=Decimal(180000+index*12500 if index%3==0 else 22000+index*6100),date=timezone.localdate()-timedelta(days=index*30),description="Fictional sample data")
        Budget.objects.get_or_create(organization=org,month=timezone.localdate().replace(day=1),defaults={"amount":Decimal("250000"),"department":"Operations"})
        PurchaseRequest.objects.get_or_create(organization=org,title="Quarterly workstations",defaults={"quantity":5,"estimated_cost":Decimal("212500"),"preferred_vendor":vendors[1],"requested_by":user})
        self.stdout.write(self.style.SUCCESS(f"Fictional demo records created in {org.name}."))
