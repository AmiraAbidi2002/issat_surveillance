from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from users.permissions import IsAdmin, IsAdminOrChef
from users.models import Enseignant
from .models import Surveillance, Absenteisme
from .algorithme import planifier_surveillances
from rest_framework import serializers


class SurveillanceSerializer(serializers.ModelSerializer):
    enseignant_nom = serializers.CharField(
        source='enseignant.user.get_full_name', read_only=True
    )
    examen_info = serializers.SerializerMethodField()

    def get_examen_info(self, obj):
        return {
            'matiere':     obj.examen.matiere,
            'classe':      obj.examen.classe,
            'date':        str(obj.examen.date_exam),
            'heure_debut': str(obj.examen.heure_debut),
            'heure_fin':   str(obj.examen.heure_fin),
            'salle':       obj.examen.salle,
        }

    class Meta:
        model = Surveillance
        fields = [
            'id', 'enseignant', 'enseignant_nom',
            'examen', 'examen_info', 'role',
            'present', 'motif_absence', 'date_affectation'
        ]


class LancerPlanificationView(APIView):
    """Lance l'algorithme de planification automatique."""
    permission_classes = [IsAdmin]

    def post(self, request):
        rapport = planifier_surveillances()
        return Response(rapport, status=status.HTTP_200_OK)


class SurveillanceListView(generics.ListAPIView):
    serializer_class = SurveillanceSerializer
    permission_classes = [IsAdminOrChef]

    def get_queryset(self):
        qs = Surveillance.objects.select_related(
            'enseignant__user', 'examen'
        ).all()
        examen_id    = self.request.query_params.get('examen')
        enseignant_id = self.request.query_params.get('enseignant')
        if examen_id:
            qs = qs.filter(examen_id=examen_id)
        if enseignant_id:
            qs = qs.filter(enseignant_id=enseignant_id)
        return qs


class MesSurveillancesView(APIView):
    """Un enseignant consulte ses propres surveillances."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            enseignant = request.user.profil_enseignant
        except Enseignant.DoesNotExist:
            return Response(
                {'detail': 'Profil enseignant introuvable.'},
                status=status.HTTP_404_NOT_FOUND
            )

        surveillances = Surveillance.objects.filter(
            enseignant=enseignant
        ).select_related('examen').order_by('examen__date_exam')

        serializer = SurveillanceSerializer(surveillances, many=True)
        return Response({
            'heures_dues':      enseignant.heures_surveillance_dues,
            'heures_effectuees': enseignant.heures_effectuees,
            'heures_restantes': enseignant.heures_restantes,
            'surveillances':    serializer.data
        })


class MarquerPresenceView(APIView):
    """L'admin marque la présence/absence après l'examen."""
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            surveillance = Surveillance.objects.get(pk=pk)
        except Surveillance.DoesNotExist:
            return Response(
                {'detail': 'Surveillance introuvable.'},
                status=status.HTTP_404_NOT_FOUND
            )

        present       = request.data.get('present', True)
        motif_absence = request.data.get('motif_absence', '')

        surveillance.present       = present
        surveillance.motif_absence = motif_absence
        surveillance.save()

        # Si absent → créer un enregistrement d'absentéisme
        if not present:
            from .algorithme import calculer_duree_heures
            duree = calculer_duree_heures(
                surveillance.examen.heure_debut,
                surveillance.examen.heure_fin
            )
            Absenteisme.objects.update_or_create(
                surveillance=surveillance,
                defaults={
                    'enseignant':     surveillance.enseignant,
                    'semestre':       request.data.get('semestre', 1),
                    'annee':          request.data.get('annee', 2025),
                    'heures_reportees': duree
                }
            )
            # Mettre à jour les heures effectuées
            ens = surveillance.enseignant
            ens.heures_effectuees = max(0, ens.heures_effectuees - duree)
            ens.save()

        return Response({'message': 'Présence mise à jour.'})