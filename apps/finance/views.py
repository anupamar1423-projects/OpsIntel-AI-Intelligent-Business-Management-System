from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from apps.core.org import current_org
from .models import Transaction,Budget
@login_required
def listing(request):
 o=current_org(request);return render(request,"listing.html",{"title":"Finance","org":o,"items":Transaction.objects.filter(organization=o).order_by("-date")[:50] if o else [],"budgets":Budget.objects.filter(organization=o) if o else []})
