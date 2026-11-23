from django.urls import path
from .api import summary
from .external_api import PipelineRunIngest
urlpatterns=[path("summary/",summary),path("v1/pipeline-runs/",PipelineRunIngest.as_view(),name="api-pipeline-runs")]
