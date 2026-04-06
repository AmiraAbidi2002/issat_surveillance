from django.urls import path
from . import views

urlpatterns = [
    path('',                        views.SurveillanceListView.as_view(),  name='surv_list'),
    path('planifier/',              views.LancerPlanificationView.as_view(),name='planifier'),
    path('mes-surveillances/',      views.MesSurveillancesView.as_view(),  name='mes_surv'),
    path('<int:pk>/presence/',      views.MarquerPresenceView.as_view(),   name='presence'),
    path('reset/', views.ResetPlanningView.as_view(), name='reset'),
]