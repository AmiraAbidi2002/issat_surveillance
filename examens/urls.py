from django.urls import path
from . import views

urlpatterns = [
    path('',                    views.ExamenListView.as_view(),           name='examen_list'),
    path('<int:pk>/',           views.ExamenDetailView.as_view(),         name='examen_detail'),
    path('importer/',           views.ImporterExamensView.as_view(),      name='import_examens'),
    path('importer-dispos/',    views.ImporterDisponibilitesView.as_view(),name='import_dispos'),
    path('importer-absences/',  views.ImporterAbsenteismeView.as_view(),  name='import_absences'),
    path('importer-complet/',    views.ImporterFichierCompletView.as_view(),name='import_complet'),
]