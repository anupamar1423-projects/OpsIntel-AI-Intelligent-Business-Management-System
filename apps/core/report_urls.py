from django.urls import path
from .reports import csv_report,pdf_report
urlpatterns=[path("transactions.csv",csv_report),path("summary.pdf",pdf_report)]
