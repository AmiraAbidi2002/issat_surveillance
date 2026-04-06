from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, status
from users.permissions import IsAdmin, IsAdminOrChef
from .models import Examen
from .serializers import ExamenSerializer, ImportExcelSerializer
from .utils import importer_examens, importer_disponibilites, importer_absenteisme


class ExamenListView(generics.ListAPIView):
    serializer_class = ExamenSerializer
    permission_classes = [IsAdminOrChef]

    def get_queryset(self):
        qs = Examen.objects.all()
        # Filtres optionnels
        classe = self.request.query_params.get('classe')
        date   = self.request.query_params.get('date')
        if classe:
            qs = qs.filter(classe__icontains=classe)
        if date:
            qs = qs.filter(date_exam=date)
        return qs


class ExamenDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Examen.objects.all()
    serializer_class = ExamenSerializer
    permission_classes = [IsAdmin]


class ImporterExamensView(APIView):
    """Import du fichier Excel des examens."""
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = ImportExcelSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        resultat = importer_examens(request.FILES['fichier'])

        if not resultat['success']:
            return Response(
                {'erreur': resultat['erreur']},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(resultat, status=status.HTTP_200_OK)


class ImporterDisponibilitesView(APIView):
    """Import du fichier Excel des disponibilités."""
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = ImportExcelSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        resultat = importer_disponibilites(request.FILES['fichier'])

        if not resultat['success']:
            return Response(
                {'erreur': resultat['erreur']},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(resultat, status=status.HTTP_200_OK)


class ImporterAbsenteismeView(APIView):
    """Import du fichier Excel de l'absentéisme."""
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = ImportExcelSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        resultat = importer_absenteisme(request.FILES['fichier'])

        if not resultat['success']:
            return Response(
                {'erreur': resultat['erreur']},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(resultat, status=status.HTTP_200_OK)