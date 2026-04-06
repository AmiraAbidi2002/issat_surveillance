from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Auth JWT
    path('login/',           views.LoginView.as_view(),         name='login'),
    path('refresh/',         TokenRefreshView.as_view(),        name='token_refresh'),
    path('me/',              views.MeView.as_view(),            name='me'),
    path('change-password/', views.ChangePasswordView.as_view(),name='change_password'),

    # Utilisateurs (admin)
    path('users/',           views.UserListView.as_view(),      name='user_list'),
    path('users/<int:pk>/',  views.UserDetailView.as_view(),    name='user_detail'),

    # Départements
    path('departements/',          views.DepartementListCreateView.as_view(), name='dept_list'),
    path('departements/<int:pk>/', views.DepartementDetailView.as_view(),     name='dept_detail'),

    # Enseignants
    path('enseignants/',           views.EnseignantListView.as_view(),   name='ens_list'),
    path('enseignants/creer/',     views.EnseignantCreateView.as_view(), name='ens_create'),
    path('enseignants/<int:pk>/',  views.EnseignantDetailView.as_view(), name='ens_detail'),
    path('enseignants/moi/',       views.MonProfilEnseignantView.as_view(), name='ens_moi'),
]