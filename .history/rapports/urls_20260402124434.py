from django.urls import path
from . import views

urlpatterns = [
    path('planning-pdf/',    views.ExporterPlanningPDFView.as_view(),    name='planning_pdf'),
    path('mon-planning-pdf/',views.ExporterMonPlanningPDFView.as_view(), name='mon_planning_pdf'),
]