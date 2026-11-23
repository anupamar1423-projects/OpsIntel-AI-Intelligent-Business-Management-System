from django.contrib import admin
from .models import Pipeline,PipelineRun,Incident,IncidentEvidence,RecoveryAttempt
admin.site.register([Pipeline,PipelineRun,Incident,IncidentEvidence,RecoveryAttempt])
