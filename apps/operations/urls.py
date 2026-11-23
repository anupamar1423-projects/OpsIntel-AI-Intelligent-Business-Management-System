from django.urls import path
from .views import listing,create_incident,add_evidence,download_evidence,incident_action,review_recovery
urlpatterns=[path("",listing,name="operations"),path("incidents/create/",create_incident,name="create-incident"),path("incidents/<int:incident_id>/evidence/",add_evidence,name="add-incident-evidence"),path("evidence/<int:evidence_id>/download/",download_evidence,name="download-evidence"),path("incidents/<int:incident_id>/action/",incident_action,name="incident-action"),path("recovery/<int:attempt_id>/review/",review_recovery,name="review-recovery")]
