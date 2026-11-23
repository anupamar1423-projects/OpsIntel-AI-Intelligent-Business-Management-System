from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from pathlib import Path
from uuid import uuid4

def document_upload_path(instance, filename):
 suffix=Path(filename).suffix.lower()
 return f"organizations/{instance.organization_id}/documents/{timezone.now():%Y/%m}/{uuid4().hex}{suffix}"
class Organization(models.Model):
 name=models.CharField(max_length=140,unique=True); industry=models.CharField(max_length=100,blank=True); invite_code=models.UUIDField(default=uuid4,unique=True,editable=False)
 def __str__(self): return self.name
class Membership(models.Model):
 ROLES=[(x,x.replace("_"," ").title()) for x in ["org_admin","operator","finance","procurement","approver","executive"]]
 organization=models.ForeignKey(Organization,on_delete=models.CASCADE); user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE); role=models.CharField(max_length=24,choices=ROLES,default="executive")
 class Meta: unique_together=[("organization","user")]
class Department(models.Model):
 organization=models.ForeignKey(Organization,on_delete=models.CASCADE,related_name="departments")
 name=models.CharField(max_length=100)
 class Meta: constraints=[models.UniqueConstraint(fields=["organization","name"],name="uniq_department_per_org")]
 def __str__(self):return self.name
class AuditEvent(models.Model):
 organization=models.ForeignKey(Organization,on_delete=models.CASCADE,related_name="audit_events")
 actor=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL)
 action=models.CharField(max_length=80)
 entity_type=models.CharField(max_length=100)
 entity_id=models.CharField(max_length=80,blank=True)
 detail=models.JSONField(default=dict,blank=True)
 ip_address=models.GenericIPAddressField(null=True,blank=True)
 created_at=models.DateTimeField(auto_now_add=True,db_index=True)
 class Meta:ordering=["-created_at"]
 def __str__(self):return f"{self.action}: {self.entity_type} {self.entity_id}"
class BusinessDocument(models.Model):
 CATEGORIES=[("invoice","Invoice"),("vendor","Vendor document"),("purchase","Purchase record"),("other","Other")]
 organization=models.ForeignKey(Organization,on_delete=models.CASCADE,related_name="documents")
 uploaded_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL)
 file=models.FileField(upload_to=document_upload_path,validators=[FileExtensionValidator(["pdf","csv","xlsx","docx","jpg","jpeg","png","webp","mp4","webm"])])
 original_name=models.CharField(max_length=255)
 category=models.CharField(max_length=20,choices=CATEGORIES,default="other")
 content_type=models.CharField(max_length=120,blank=True)
 size_bytes=models.PositiveBigIntegerField(default=0)
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta:ordering=["-created_at"]
 def __str__(self):return self.original_name

class AssistantMessage(models.Model):
 organization=models.ForeignKey(Organization,on_delete=models.CASCADE,related_name="assistant_messages")
 user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
 question=models.TextField()
 answer=models.TextField()
 provider=models.CharField(max_length=32,default="demo")
 created_at=models.DateTimeField(auto_now_add=True,db_index=True)
 class Meta:ordering=["created_at"]

class Notification(models.Model):
 organization=models.ForeignKey(Organization,on_delete=models.CASCADE,related_name="notifications")
 recipient=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="opsintel_notifications")
 title=models.CharField(max_length=180)
 body=models.CharField(max_length=500,blank=True)
 url=models.CharField(max_length=240,blank=True)
 read_at=models.DateTimeField(null=True,blank=True)
 created_at=models.DateTimeField(auto_now_add=True,db_index=True)
 class Meta:ordering=["-created_at"]

class OrganizationAPIKey(models.Model):
 organization=models.ForeignKey(Organization,on_delete=models.CASCADE,related_name="api_keys")
 label=models.CharField(max_length=80)
 prefix=models.CharField(max_length=12,db_index=True)
 token_hash=models.CharField(max_length=64,unique=True)
 created_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL)
 created_at=models.DateTimeField(auto_now_add=True)
 last_used_at=models.DateTimeField(null=True,blank=True)
 revoked_at=models.DateTimeField(null=True,blank=True)
 class Meta:ordering=["-created_at"]
