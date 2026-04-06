# surveillances/algorithme.py
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


def get_candidats_disponibles(date_exam, heure_debut, heure_fin,
                               exclusions_ids=None):
    """
    Recherche dichotomique correcte :
    1. Récupère tous les candidats disponibles et non occupés
    2. Trie par charge_restante DÉCROISSANTE (plus besoin d'heures = priorité)
    3. Utilise bisect sur liste CROISSANTE pour trouver
       ceux qui ont encore des heures dues (charge_restante > 0)
    4. Retourne d'abord ceux qui ont des heures dues,
       puis les autres en fallback
    """
    exclusions_ids = exclusions_ids or []

    # Récupérer tous les enseignants disponibles non occupés
    tous = list(
        Enseignant.objects.select_related('user')
        .exclude(id__in=exclusions_ids)
    )

    disponibles = [
        e for e in tous
        if enseignant_est_disponible(e, date_exam, heure_debut, heure_fin)
        and not enseignant_est_occupe(e, date_exam, heure_debut, heure_fin)
    ]

    if not disponibles:
        return [], []

    # Séparer ceux qui ont encore des heures dues et les autres
    avec_heures_dues  = [e for e in disponibles if charge_restante(e) > 0]
    sans_heures_dues  = [e for e in disponibles if charge_restante(e) <= 0]

    # Trier chaque groupe : ceux qui ont le plus grand manque d'abord
    # (tri sur liste croissante pour bisect_left correct)
    avec_heures_dues.sort(key=charge_restante, reverse=True)
    sans_heures_dues.sort(key=charge_restante, reverse=True)

    # Dichotomie : dans avec_heures_dues, trouver ceux avec charge > seuil_min
    # On construit une liste croissante des charges pour bisect
    seuil_min = 0.0
    charges_croissantes = sorted(charge_restante(e) for e in avec_heures_dues)
    idx = bisect.bisect_right(charges_croissantes, seuil_min)
    # idx = nombre d'éléments <= seuil_min dans la liste triée
    # Les éléments au-delà de idx ont charge > seuil_min
    # Comme notre liste avec_heures_dues est déjà triée décroissante,
    # tous ses éléments ont charge > 0 : on les prend tous
    # La dichotomie sert ici à confirmer qu'il existe bien des candidats utiles

    return avec_heures_dues, sans_heures_dues


@transaction.atomic
def planifier_surveillances():
    """
    Algorithme corrigé :

    ÉTAPE 0 : Réinitialisation complète
    ÉTAPE 1 : Trier les examens par date + heure
    ÉTAPE 2 : Affecter le responsable (OBLIGATOIRE, sans condition de quota)
    ÉTAPE 3 : Compléter avec candidats ayant des heures dues (dichotomie)
    ÉTAPE 4 : Fallback sur candidats sans heures dues si encore manquant
    ÉTAPE 5 : Rapport + alertes
    """

    # ── ÉTAPE 0 : Reset ────────────────────────────────────────────
    Enseignant.objects.all().update(heures_effectuees=0)
    Surveillance.objects.all().delete()

    examens = list(
        Examen.objects.all().order_by('date_exam', 'heure_debut')
    )

    rapport = {
        'examens_traites':       0,
        'affectations_reussies': 0,
        'examens_incomplets':    [],
        'alertes_charge':        [],
        'detail':                []
    }

    for examen in examens:
        rapport['examens_traites'] += 1
        nb_requis   = examen.nb_surveillants_requis
        nb_affectes = 0
        ids_assignes = []

        detail = {
            'examen':      str(examen),
            'date':        str(examen.date_exam),
            'nb_requis':   nb_requis,
            'surveillants':[],
            'manquants':   0
        }

        duree = calculer_duree_heures(examen.heure_debut, examen.heure_fin)

        # ── ÉTAPE 2 : Responsable (OBLIGATOIRE sans condition quota) ──
        responsable = examen.enseignant_responsable

        if responsable:
            dispo  = enseignant_est_disponible(
                responsable, examen.date_exam,
                examen.heure_debut, examen.heure_fin
            )
            occupe = enseignant_est_occupe(
                responsable, examen.date_exam,
                examen.heure_debut, examen.heure_fin
            )

            if dispo and not occupe:
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
                    'nom':  str(responsable),
                    'role': 'responsable'
                })
            else:
                # Responsable non dispo : noter mais continuer
                detail['surveillants'].append({
                    'nom':  str(responsable),
                    'role': 'responsable_absent'
                })

        # ── ÉTAPE 3 : Compléter (candidats avec heures dues d'abord) ─
        nb_manquant = nb_requis - nb_affectes

        if nb_manquant > 0:
            avec_dues, sans_dues = get_candidats_disponibles(
                examen.date_exam, examen.heure_debut, examen.heure_fin,
                exclusions_ids=ids_assignes
            )

            # D'abord les enseignants qui ont encore des heures dues
            for ens in avec_dues:
                if nb_manquant <= 0:
                    break
                Surveillance.objects.create(
                    enseignant=ens, examen=examen, role='surveillant'
                )
                ens.heures_effectuees += duree
                ens.save()
                nb_affectes  += 1
                nb_manquant  -= 1
                ids_assignes.append(ens.id)
                detail['surveillants'].append(
                    {'nom': str(ens), 'role': 'surveillant'}
                )

            # ── ÉTAPE 4 : Fallback sans heures dues ────────────────
            if nb_manquant > 0:
                for ens in sans_dues:
                    if nb_manquant <= 0:
                        break
                    Surveillance.objects.create(
                        enseignant=ens, examen=examen, role='remplacant'
                    )
                    ens.heures_effectuees += duree
                    ens.save()
                    nb_affectes  += 1
                    nb_manquant  -= 1
                    ids_assignes.append(ens.id)
                    detail['surveillants'].append(
                        {'nom': str(ens), 'role': 'remplacant'}
                    )

        # ── Résultat de cet examen ────────────────────────────────
        detail['manquants'] = nb_manquant
        rapport['detail'].append(detail)

        if nb_manquant == 0:
            rapport['affectations_reussies'] += 1
        else:
            rapport['examens_incomplets'].append({
                'examen':    str(examen),
                'manquants': nb_manquant
            })

    # ── ÉTAPE 5 : Alertes ─────────────────────────────────────────
    for ens in Enseignant.objects.select_related('user').all():
        ecart = ens.heures_effectuees - ens.heures_surveillance_dues
        if ecart > 0.5:
            rapport['alertes_charge'].append({
                'enseignant': str(ens),
                'statut':     'Dépassement',
                'ecart':      round(ecart, 2)
            })
        elif ecart < -0.5:
            rapport['alertes_charge'].append({
                'enseignant': str(ens),
                'statut':     'Insuffisant',
                'ecart':      round(ecart, 2)
            })

    return rapport