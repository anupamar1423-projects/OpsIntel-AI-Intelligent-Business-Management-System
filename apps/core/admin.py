from django.contrib import admin
from .models import Organization,Membership,Department,AuditEvent,BusinessDocument,AssistantMessage,Notification,OrganizationAPIKey
admin.site.register([Organization,Membership,Department,AuditEvent,BusinessDocument,AssistantMessage,Notification,OrganizationAPIKey])
