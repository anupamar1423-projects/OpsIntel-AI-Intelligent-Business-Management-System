from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial=True
    dependencies=[("core","0001_initial")]
    operations=[
        migrations.CreateModel(name="Transaction",fields=[("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),("kind",models.CharField(choices=[("income","Income"),("expense","Expense")],max_length=8)),("category",models.CharField(max_length=80)),("amount",models.DecimalField(decimal_places=2,max_digits=13)),("date",models.DateField()),("description",models.CharField(blank=True,max_length=240)),("organization",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,to="core.organization"))]),
        migrations.CreateModel(name="Budget",fields=[("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),("month",models.DateField()),("department",models.CharField(blank=True,max_length=80)),("amount",models.DecimalField(decimal_places=2,max_digits=13)),("organization",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,to="core.organization"))]),
    ]
