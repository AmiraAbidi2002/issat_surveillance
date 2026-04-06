import bisect
from datetime import datetime
from django.db import transaction
from users.models import Enseignant
from examens.models import Examen
from disponibilites.models import Disponibilite
from .models import Surveillance


def calculer_duree_heures(heure_debut, heure_fin):
    d = datetime.combine(datetime.today(), heure_debut)
    f = datetime.combine(datetime.today(), heure_fin)
    return max(0.0, (f - d).seconds / 3600)


def charge_restante(ens):
    return ens.heures_surveillance_dues - ens.heures_effectuees


def enseignant_est_disponible(enseignant, date_exam, heure_debut, heure_fin):
    return Disponibilite.objects.filter(
        enseignant=enseignant,
        date_dispo=date_exam,
        heure_debut__lte=heure_debut,
        heure_fin__gte=heure_fin
    ).exists()


def enseignant_est_occupe(enseignant, date_exam, heure_debut, heure_fin):
    return Surveillance.objects.filter(
        enseignant=enseignant,
        examen__date_exam=date_exam,
        examen__heure_debut__lt=heure_fin,
        examen__heure_fin__gt=heure_debut
    ).exists()


def recherche_dichotomique_disponibles(
    date_exam, heure_debut, heure_fin, exclusions_ids=None
):
    """
    Recherche dichotomique sur charge restante.
    Les enseignants avec plus de charge restante passent avant.
    """
    exclusions_ids = exclusions_ids or []

    candidats = list(
        Enseignant.objects.select_related('user')
        .exclude(id__in=exclusions_ids)
    )

    # garder uniquement les disponibles
    candidats = [
        e for e in candidats
        if enseignant_est_disponible(e, date_exam, heure_debut, heure_fin)
        and not enseignant_est_occupe(e, date_exam, heure_debut, heure_fin)
    ]

    # tri greedy : plus grand manque d'abord
    candidats.sort(key=charge_restante, reverse=True)

    # liste triée pour dichotomie
    charges = [-charge_restante(e) for e in candidats]

    # premier avec charge_restante > 0
    idx = bisect.bisect_left(charges, -1)

    return candidats[idx:]


@transaction.atomic
def planifier_surveillances():
    """
    Algorithme final :
    1) reset
    2) responsable
    3) greedy + dichotomie
    4) remplaçants
    5) alertes
    """

    Enseignant.objects.all().update(heures_effectuees=0)
    Surveillance.objects.all().delete()

    examens = list(
        Examen.objects.all().order_by('date_exam', 'heure_debut')
    )

    rapport = {
        'examens_traites': 0,
        'affectations_reussies': 0,
        'examens_incomplets': [],
        'alertes_charge': [],
        'detail': []
    }

    for examen in examens:
        rapport['examens_traites'] += 1
        nb_requis = examen.nb_surveillants_requis
        nb_affectes = 0
        ids_assignes = []

        detail = {
            'examen': str(examen),
            'date': str(examen.date_exam),
            'nb_requis': nb_requis,
            'surveillants': [],
            'manquants': 0
        }

        duree = calculer_duree_heures(
            examen.heure_debut,
            examen.heure_fin
        )

        # =====================================================
        # RESPONSABLE
        # =====================================================
        responsable = getattr(examen, 'enseignant_responsable', None)

        if (
            responsable
            and charge_restante(responsable) > 0
            and enseignant_est_disponible(
                responsable,
                examen.date_exam,
                examen.heure_debut,
                examen.heure_fin
            )
            and not enseignant_est_occupe(
                responsable,
                examen.date_exam,
                examen.heure_debut,
                examen.heure_fin
            )
        ):
            Surveillance.objects.create(
                enseignant=responsable,
                examen=examen,
                role='responsable'
            )

            responsable.heures_effectuees += duree
            responsable.save()

            nb_affectes += 1
            ids_assignes.append(responsable.id)

            detail['surveillants'].append({
                'nom': str(responsable),
                'role': 'responsable'
            })

        # =====================================================
        # GREEDY + DICHOTOMIE
        # =====================================================
        nb_manquant = nb_requis - nb_affectes

        candidats = recherche_dichotomique_disponibles(
            examen.date_exam,
            examen.heure_debut,
            examen.heure_fin,
            ids_assignes
        )

        for ens in candidats:
            if nb_manquant <= 0:
                break

            Surveillance.objects.create(
                enseignant=ens,
                examen=examen,
                role='surveillant'
            )

            ens.heures_effectuees += duree
            ens.save()

            nb_affectes += 1
            nb_manquant -= 1
            ids_assignes.append(ens.id)

            detail['surveillants'].append({
                'nom': str(ens),
                'role': 'surveillant'
            })

        # =====================================================
        # REMPLAÇANTS
        # =====================================================
        if nb_manquant > 0:
            remplaçants = [
                e for e in Enseignant.objects.exclude(id__in=ids_assignes)
                if enseignant_est_disponible(
                    e,
                    examen.date_exam,
                    examen.heure_debut,
                    examen.heure_fin
                )
            ]

            for ens in remplaçants:
                if nb_manquant <= 0:
                    break

                Surveillance.objects.create(
                    enseignant=ens,
                    examen=examen,
                    role='remplacant'
                )

                ens.heures_effectuees += duree
                ens.save()

                nb_affectes += 1
                nb_manquant -= 1

                detail['surveillants'].append({
                    'nom': str(ens),
                    'role': 'remplacant'
                })

        detail['manquants'] = nb_manquant
        rapport['detail'].append(detail)

        if nb_manquant == 0:
            rapport['affectations_reussies'] += 1
        else:
            rapport['examens_incomplets'].append(detail)

    # =========================================================
    # ALERTES
    # =========================================================
    for ens in Enseignant.objects.select_related('user'):
        ecart = ens.heures_effectuees - ens.heures_surveillance_dues
        if abs(ecart) > 0.5:
            rapport['alertes_charge'].append({
                'enseignant': str(ens),
                'statut': 'Dépassement' if ecart > 0 else 'Insuffisant',
                'ecart': round(ecart, 2)
            })

    return rapport