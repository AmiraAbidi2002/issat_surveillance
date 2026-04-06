from django.http import FileResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from users.permissions import IsAdminOrChef
from .generateur_pdf import generer_pdf_depuis_bdd
from datetime import date


class ExporterPlanningPDFView(APIView):
    """
    GET /api/rapports/planning-pdf/
    Génère et retourne le planning complet en PDF.
    Accessible : Admin + Chef de département.
    """
    permission_classes = [IsAdminOrChef]

    def get(self, request):
        buffer = generer_pdf_depuis_bdd()
        nom_fichier = f"planning_surveillance_{date.today().strftime('%Y%m%d')}.pdf"
        return FileResponse(
            buffer,
            as_attachment=True,
            filename=nom_fichier,
            content_type='application/pdf'
        )


class ExporterMonPlanningPDFView(APIView):
    """
    GET /api/rapports/mon-planning-pdf/
    Un enseignant télécharge uniquement son propre planning.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from surveillances.models import Surveillance
        from users.models import Enseignant
        from .generateur_pdf import generer_pdf_planning

        try:
            ens = request.user.profil_enseignant
        except Enseignant.DoesNotExist:
            from rest_framework.response import Response
            from rest_framework import status
            return Response({'detail': 'Profil enseignant introuvable.'},
                            status=status.HTTP_404_NOT_FOUND)

        # Seulement ses surveillances
        surv_qs = Surveillance.objects.filter(
            enseignant=ens
        ).select_related('examen').order_by('examen__date_exam')

        surveillances_data = [{
            'enseignant': ens.user.get_full_name(),
            'date':       s.examen.date_exam.strftime('%d/%m/%Y'),
            'horaire':    f"{s.examen.heure_debut.strftime('%H:%M')}-{s.examen.heure_fin.strftime('%H:%M')}",
            'salle':      s.examen.salle,
            'matiere':    s.examen.matiere,
            'classe':     s.examen.classe,
            'role':       s.role,
        } for s in surv_qs]

        heures_abs = max(0, ens.heures_surveillance_dues - ens.heures_enseignement)
        enseignants_data = [{
            'nom':        ens.user.get_full_name(),
            'dept':       ens.departement.nom if ens.departement else '',
            'heures_ens': ens.heures_enseignement,
            'heures_abs': round(heures_abs, 2),
            'dues':       ens.heures_surveillance_dues,
            'effectuees': round(ens.heures_effectuees, 2),
        }]

        # Examens uniquement de cet enseignant
        from examens.models import Examen
        examens_ids = surv_qs.values_list('examen_id', flat=True)
        examens_data = []
        for exam in Examen.objects.filter(id__in=examens_ids):
            surv_list = Surveillance.objects.filter(examen=exam).select_related('enseignant__user')
            examens_data.append({
                'matiere':      exam.matiere,
                'classe':       exam.classe,
                'date':         exam.date_exam.strftime('%d/%m/%Y'),
                'horaire':      f"{exam.heure_debut.strftime('%H:%M')}-{exam.heure_fin.strftime('%H:%M')}",
                'salle':        exam.salle,
                'nb_etudiants': exam.nb_etudiants,
                'nb_requis':    exam.nb_surveillants_requis,
                'surveillants': ', '.join(
                    s.enseignant.user.get_full_name() for s in surv_list
                ),
                'complet':      surv_list.count() >= exam.nb_surveillants_requis,
            })

        titre = f"Mon Planning — {ens.user.get_full_name()}"
        buffer = generer_pdf_planning(surveillances_data, enseignants_data,
                                       examens_data, [], titre_doc=titre)
        nom = f"mon_planning_{ens.user.username}_{date.today().strftime('%Y%m%d')}.pdf"
        return FileResponse(buffer, as_attachment=True,
                            filename=nom, content_type='application/pdf')