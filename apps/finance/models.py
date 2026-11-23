from django.db import models
from apps.core.models import Organization
class Transaction(models.Model):
 organization=models.ForeignKey(Organization,on_delete=models.CASCADE);kind=models.CharField(max_length=8,choices=[("income","Income"),("expense","Expense")]);category=models.CharField(max_length=80);amount=models.DecimalField(max_digits=13,decimal_places=2);date=models.DateField();description=models.CharField(max_length=240,blank=True)
class Budget(models.Model):
 organization=models.ForeignKey(Organization,on_delete=models.CASCADE);month=models.DateField();department=models.CharField(max_length=80,blank=True);amount=models.DecimalField(max_digits=13,decimal_places=2)
