from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model

from .models import Departement, Enseignant
from .serializers import (
    UserSerializer, RegisterSerializer, ChangePasswordSerializer,
    DepartementSerializer, EnseignantSerializer, EnseignantCreateSerializer
)
from .permissions import IsAdmin, IsAdminOrChef

User = get_user_model()


# --- JWT personnalisé : ajouter role + nom dans le token ---
class CustomTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role']       = user.role
        token['full_name']  = user.get_full_name()
        token['email']      = user.email
        return token


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenSerializer
    permission_classes = [AllowAny]


# --- Profil de l'utilisateur connecté ---
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Mot de passe modifié avec succès."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# --- Gestion des utilisateurs (Admin seulement) ---
class UserListView(generics.ListAPIView):
    queryset = User.objects.all().order_by('last_name')
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]


# --- Départements ---
class DepartementListCreateView(generics.ListCreateAPIView):
    queryset = Departement.objects.all()
    serializer_class = DepartementSerializer
    permission_classes = [IsAdminOrChef]


class DepartementDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Departement.objects.all()
    serializer_class = DepartementSerializer
    permission_classes = [IsAdmin]


# --- Enseignants ---
class EnseignantListView(generics.ListAPIView):
    serializer_class = EnseignantSerializer
    permission_classes = [IsAdminOrChef]

    def get_queryset(self):
        qs = Enseignant.objects.select_related('user', 'departement').all()
        # Filtrer par département si paramètre fourni
        dept = self.request.query_params.get('departement')
        if dept:
            qs = qs.filter(departement_id=dept)
        return qs


class EnseignantCreateView(generics.CreateAPIView):
    """L'admin crée un compte enseignant (User + Enseignant d'un coup)."""
    serializer_class = EnseignantCreateSerializer
    permission_classes = [IsAdmin]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enseignant = serializer.save()
        return Response(
            EnseignantSerializer(enseignant).data,
            status=status.HTTP_201_CREATED
        )


class EnseignantDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Enseignant.objects.select_related('user', 'departement').all()
    serializer_class = EnseignantSerializer
    permission_classes = [IsAdminOrChef]


class MonProfilEnseignantView(APIView):
    """Un enseignant consulte son propre profil."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            enseignant = request.user.profil_enseignant
            serializer = EnseignantSerializer(enseignant)
            return Response(serializer.data)
        except Enseignant.DoesNotExist:
            return Response(
                {"detail": "Profil enseignant introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )