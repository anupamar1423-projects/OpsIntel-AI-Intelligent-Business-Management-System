from django import forms
from django.conf import settings
from apps.operations.models import Pipeline, Incident
from apps.procurement.models import Vendor

class TransactionForm(forms.Form):
    kind = forms.ChoiceField(choices=[("income", "Income"), ("expense", "Expense")])
    category = forms.CharField(max_length=80)
    amount = forms.DecimalField(max_digits=13, decimal_places=2, min_value=0)
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    description = forms.CharField(max_length=240, required=False)

class PipelineForm(forms.Form):
    name = forms.CharField(max_length=120)
    expected_minutes = forms.IntegerField(min_value=1, initial=10)
    recovery_enabled = forms.BooleanField(required=False)
    recovery_adapter = forms.ChoiceField(choices=[("none","Not configured")]+[(key,key.replace("_"," ").title()) for key in settings.RECOVERY_ADAPTERS], required=False)

class VendorForm(forms.Form):
    name = forms.CharField(max_length=140)
    category = forms.CharField(max_length=100, required=False)
    unit_price = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    reliability = forms.IntegerField(min_value=0, max_value=100, initial=80)
    on_time_rate = forms.IntegerField(min_value=0, max_value=100, initial=80)
    product_image = forms.ImageField(required=False)

    def clean_product_image(self):
        image=self.cleaned_data.get("product_image")
        if image and image.size>10*1024*1024:
            raise forms.ValidationError("Vendor images must be 10 MB or smaller.")
        return image

class PurchaseForm(forms.Form):
    title = forms.CharField(max_length=160)
    quantity = forms.IntegerField(min_value=1, initial=1)
    estimated_cost = forms.DecimalField(max_digits=13, decimal_places=2, min_value=0)
    preferred_vendor = forms.ModelChoiceField(queryset=Vendor.objects.none(), required=False)

    def __init__(self, *args, organization, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["preferred_vendor"].queryset = Vendor.objects.filter(organization=organization, approved=True)

class BudgetForm(forms.Form):
    month = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    department = forms.CharField(max_length=80, required=False)
    amount = forms.DecimalField(max_digits=13, decimal_places=2, min_value=0)

class IncidentForm(forms.Form):
    pipeline = forms.ModelChoiceField(queryset=Pipeline.objects.none(), required=False)
    title = forms.CharField(max_length=160)
    severity = forms.ChoiceField(choices=[("low","Low"),("medium","Medium"),("high","High"),("critical","Critical")])
    detail = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, *args, organization, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pipeline"].queryset = Pipeline.objects.filter(organization=organization)

class EvidenceForm(forms.Form):
    file = forms.FileField()
    caption = forms.CharField(max_length=240, required=False)

    def clean_file(self):
        value = self.cleaned_data["file"]
        if value.size > 50 * 1024 * 1024:
            raise forms.ValidationError("Evidence files must be 50 MB or smaller.")
        ext=value.name.rsplit(".",1)[-1].lower() if "." in value.name else ""
        if ext not in {"jpg","jpeg","png","webp","mp4","webm"}:
            raise forms.ValidationError("Use a JPG, PNG, WebP, MP4 or WebM file.")
        return value

class DocumentForm(forms.Form):
    file = forms.FileField()
    category = forms.ChoiceField(choices=[("invoice","Invoice"),("vendor","Vendor document"),("purchase","Purchase record"),("other","Other")])

    def clean_file(self):
        value=self.cleaned_data["file"]
        if value.size > 50 * 1024 * 1024:
            raise forms.ValidationError("Documents must be 50 MB or smaller.")
        ext=value.name.rsplit(".",1)[-1].lower() if "." in value.name else ""
        if ext not in {"pdf","csv","xlsx","docx","jpg","jpeg","png","webp","mp4","webm"}:
            raise forms.ValidationError("File type is not supported.")
        return value
