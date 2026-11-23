import csv
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum
from reportlab.pdfgen import canvas
from .org import current_org
from apps.finance.models import Transaction
@login_required
def csv_report(request):
 org=current_org(request); r=HttpResponse(content_type="text/csv"); r["Content-Disposition"]='attachment; filename="transactions.csv"'; w=csv.writer(r);w.writerow(["Date","Type","Category","Amount"]);
 if org:
  for t in Transaction.objects.filter(organization=org):w.writerow([t.date,t.kind,t.category,t.amount])
 return r
@login_required
def pdf_report(request):
 org=current_org(request);r=HttpResponse(content_type="application/pdf");r["Content-Disposition"]='attachment; filename="summary.pdf"';c=canvas.Canvas(r);c.drawString(70,770,"OpsIntel AI Business Summary");c.drawString(70,740,"Organization: "+(org.name if org else "Not assigned"));c.save();return r
