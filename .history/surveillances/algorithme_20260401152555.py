import bisect
from datetime import datetime
from users.models import Enseignant
from examens.models import Examen
from disponibilites.models import Disponibilite
from .models import Surveillance


def calculer_duree_heures(heure_debut, heure_fin):
    d = datetime.combine(datetime.today(), heure_debut)
    f = datetime.combine(datetime.today(), heure_fin)
    return max(0.0, (f - d).seconds / 3600)


def enseignant_est_disponible(enseignant, date_exam, heure_debut, heure_fin):
    """Vérifie créneau de disponibilité couvrant toute la durée."""
    return Disponibilite.objects.filter(
        enseignant=enseignant,
        date_dispo=date_exam,
        heure_debut__lte=heure_debut,
        heure_fin__gte=heure_fin
    ).exists()


def enseignant_est_occupe(enseignant, date_exam, heure_debut, heure_fin):
    """Vérifie conflit avec une autre surveillance déjà assignée."""
    return Surveillance.objects.filter(
        enseignant=enseignant,
        examen__date_exam=date_exam,
        examen__heure_debut__lt=heure_fin,
        examen__heure_fin__gt=heure_debut
    ).exists()


# ─────────────────────────────────────────────────────────────────
# RECHERCHE DICHOTOMIQUE  ← manquait dans la version précédente
# ─────────────────────────────────────────────────────────────────
def recherche_dichotomique_disponibles(date_exam, heure_debut, heure_fin,
                                        exclusions_ids=None):
    """
    Étape 4 de l'algorithme :
    1. Récupère les noms triés des enseignants disponibles ce jour-là
    2. Utilise bisect (recherche dichotomique) pour trouver rapidement
       les enseignants dans la liste triée
    3. Vérifie disponibilité complète + absence de conflit
    Retourne la liste triée par heures_effectuées (moins chargés d'abord).
    """
    exclusions_ids = exclusions_ids or []

    # Noms des enseignants ayant une dispo ce jour-là
    noms_dispos = list(
        Disponibilite.objects.filter(date_dispo=date_exam)
        .values_list('enseignant__user__last_name', flat=True)
        .distinct()
        .order_by('enseignant__user__last_name')   # ← liste TRIÉE (précondition)
    )

    # Tous les enseignants triés par nom de famille
    tous = list(
        Enseignant.objects.select_related('user')
        .exclude(id__in=exclusions_ids)
        .order_by('user__last_name')
    )
    noms_tous = [e.user.last_name for e in tous]

    candidats = []
    for nom in noms_dispos:
        # Recherche dichotomique dans la liste triée
        idx = bisect.bisect_left(noms_tous, nom)
        if idx < len(noms_tous) and noms_tous[idx] == nom:
            ens = tous[idx]
            if (ens.id not in exclusions_ids
                    and enseignant_est_disponible(ens, date_exam, heure_debut, heure_fin)
                    and not enseignant_est_occupe(ens, date_exam, heure_debut, heure_fin)):
                candidats.append(ens)

    # Trier par heures effectuées (moins chargés d'abord)
    candidats.sort(key=lambda e: e.heures_effectuees)
    return candidats


# ─────────────────────────────────────────────────────────────────
# ALGORITHME PRINCIPAL
# ─────────────────────────────────────────────────────────────────
def planifier_surveillances():
    """
    ÉTAPE 1 : Réinitialiser les heures effectuées
    ÉTAPE 2 : Trier examens par date + heure
    ÉTAPE 3 : Affecter responsable de matière (s'il est disponible)
    ÉTAPE 4 : Compléter via recherche dichotomique (moins chargés d'abord)
    ÉTAPE 5 : Remplaçants si encore insuffisant
    ÉTAPE 6 : Rapport final + alertes absentéisme
    """

    # ÉTAPE 1 — Réinitialiser les heures effectuées
    Enseignant.objects.all().update(heures_effectuees=0)
    Surveillance.objects.all().delete()

    # ÉTAPE 2 — Examens triés
    examens = list(Examen.objects.all().order_by('date_exam', 'heure_debut'))

    rapport = {
        'examens_traites':       0,
        'affectations_reussies': 0,
        'examens_incomplets':    [],
        'alertes_charge':        [],   # ← absentéisme / dépassement
        'detail':                []
    }

    for examen in examens:
        rapport['examens_traites'] += 1
        nb_requis   = examen.nb_surveillants_requis
        nb_affectes = 0
        ids_assignes = []

        detail = {
            'examen':       str(examen),
            'date':         str(examen.date_exam),
            'nb_requis':    nb_requis,
            'surveillants': [],
            'manquants':    0
        }

        # ÉTAPE 3 — Responsable de matière
        responsable = examen.enseignant_responsable
        if responsable:
            dispo  = enseignant_est_disponible(responsable, examen.date_exam,
                                               examen.heure_debut, examen.heure_fin)
            occupe = enseignant_est_occupe(responsable, examen.date_exam,
                                           examen.heure_debut, examen.heure_fin)
            if dispo and not occupe:
                Surveillance.objects.create(
                    enseignant=responsable, examen=examen, role='responsable'
                )
                duree = calculer_duree_heures(examen.heure_debut, examen.heure_fin)
                responsable.heures_effectuees += duree
                responsable.save()
                nb_affectes += 1
                ids_assignes.append(responsable.id)
                detail['surveillants'].append(
                    {'nom': str(responsable), 'role': 'responsable'}
                )

        # ÉTAPE 4 — Compléter via recherche dichotomique
        nb_manquant = nb_requis - nb_affectes

        if nb_manquant > 0:
            candidats = recherche_dichotomique_disponibles(
                examen.date_exam, examen.heure_debut, examen.heure_fin,
                exclusions_ids=ids_assignes
            )

            for ens in candidats:
                if nb_manquant <= 0:
                    break
                # Priorité aux enseignants qui n'ont pas encore atteint leur quota
                if ens.heures_effectuees < ens.heures_surveillance_dues:
                    Surveillance.objects.create(
                        enseignant=ens, examen=examen, role='surveillant'
                    )
                    duree = calculer_duree_heures(examen.heure_debut, examen.heure_fin)
                    ens.heures_effectuees += duree
                    ens.save()
                    nb_affectes  += 1
                    nb_manquant  -= 1
                    ids_assignes.append(ens.id)
                    detail['surveillants'].append(
                        {'nom': str(ens), 'role': 'surveillant'}
                    )

            # Si encore manquant → prendre n'importe quel disponible
            if nb_manquant > 0:
                for ens in candidats:
                    if nb_manquant <= 0:
                        break
                    if ens.id not in ids_assignes:
                        Surveillance.objects.create(
                            enseignant=ens, examen=examen, role='remplacant'
                        )
                        duree = calculer_duree_heures(examen.heure_debut, examen.heure_fin)
                        ens.heures_effectuees += duree
                        ens.save()
                        nb_affectes  += 1
                        nb_manquant  -= 1
                        ids_assignes.append(ens.id)
                        detail['surveillants'].append(
                            {'nom': str(ens), 'role': 'remplacant'}
                        )

        # Résultat de cet examen
        detail['manquants'] = max(0, nb_requis - nb_affectes)
        rapport['detail'].append(detail)

        if detail['manquants'] == 0:
            rapport['affectations_reussies'] += 1
        else:
            rapport['examens_incomplets'].append(
                {'examen': str(examen), 'manquants': detail['manquants']}
            )

    # ÉTAPE 6 — Alertes charge (absentéisme + dépassement)
    # ← manquait dans la version précédente
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