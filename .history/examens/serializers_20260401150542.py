from rest_framework import serializers
from .models import Examen
from users.models import Enseignant


class ExamenSerializer(serializers.ModelSerializer):
    enseignant_nom = serializers.CharField(
        source='enseignant_responsable.user.get_full_name',
        read_only=True
    )
    nb_surveillants_requis = serializers.IntegerField(read_only=True)

    class Meta:
        model = Examen
        fields = [
            'id', 'matiere', 'classe', 'date_exam',
            'heure_debut', 'heure_fin', 'salle',
            'nb_etudiants', 'nb_surveillants_requis',
            'enseignant_responsable', 'enseignant_nom'
        ]


class ImportExcelSerializer(serializers.Serializer):
    fichier = serializers.FileField()

    def validate_fichier(self, value):
        if not value.name.endswith(('.xlsx', '.xls')):
            raise serializers.ValidationError("Le fichier doit être au format Excel (.xlsx ou .xls)")
        return value