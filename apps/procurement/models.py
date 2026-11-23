from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.validators import FileExtensionValidator, MaxValueValidator
from django.db import models

from apps.core.models import Organization


def vendor_image_path(instance, filename):
    return f"organizations/{instance.organization_id}/vendors/{uuid4().hex}{Path(filename).suffix.lower()}"


class Vendor(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="vendors")
    name = models.CharField(max_length=140)
    category = models.CharField(max_length=100, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reliability = models.PositiveSmallIntegerField(default=80, validators=[MaxValueValidator(100)])
    on_time_rate = models.PositiveSmallIntegerField(default=80, validators=[MaxValueValidator(100)])
    approved = models.BooleanField(default=True)
    product_image = models.ImageField(upload_to=vendor_image_path, blank=True, validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])])
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def score(self):
        return round(self.reliability * .55 + self.on_time_rate * .45, 1)

    def __str__(self):
        return self.name


class PurchaseRequest(models.Model):
    STATUS = [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("returned", "Returned")]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="purchase_requests")
    title = models.CharField(max_length=160)
    quantity = models.PositiveIntegerField(default=1)
    estimated_cost = models.DecimalField(max_digits=13, decimal_places=2)
    preferred_vendor = models.ForeignKey(Vendor, null=True, blank=True, on_delete=models.SET_NULL, related_name="requests")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="purchase_requests")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_purchase_requests")
    status = models.CharField(max_length=12, choices=STATUS, default="pending", db_index=True)
    approval_note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title


class PurchaseOrder(models.Model):
    STATUS = [("issued", "Issued"), ("in_transit", "In transit"), ("delivered", "Delivered"), ("cancelled", "Cancelled")]
    request = models.OneToOneField(PurchaseRequest, on_delete=models.CASCADE, related_name="purchase_order")
    order_number = models.CharField(max_length=40, unique=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="purchase_orders")
    status = models.CharField(max_length=12, choices=STATUS, default="issued")
    issued_at = models.DateTimeField(auto_now_add=True)
    expected_delivery = models.DateField(null=True, blank=True)
    actual_delivery = models.DateField(null=True, blank=True)
    tracking_reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.order_number
