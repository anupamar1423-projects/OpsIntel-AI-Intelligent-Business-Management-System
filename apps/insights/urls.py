from django.urls import path
from .views import home,assistant
urlpatterns=[path("",home,name="insights"),path("assistant/",assistant,name="assistant")]
