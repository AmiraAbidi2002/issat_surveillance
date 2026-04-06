from datetime import datetime
from users.models import Enseignant
from examens.models import Examen
from disponibilites.models import Disponibilite
from .models import Surveillance


def enseignant_est_disponible(enseignant, date_exam, heure_debut, heure_fin):
    """
    Vérifie si un enseignant a un créneau de disponibilité
    qui couvre toute la durée de l'examen.
    """
    return Disponibilite.objects.filter(
        enseignant=enseignant,
        date_dispo=date_exam,
        heure_debut__lte=heure_debut,
        heure_fin__gte=heure_fin
    ).exists()


def enseignant_est_occupe(enseignant, date_exam, heure_debut, heure_fin):
    """
    Vérifie si un enseignant est déjà assigné à un autre examen
    qui chevauche ce créneau.
    """
    return Surveillance.objects.filter(
        enseignant=enseignant,
        examen__date_exam=date_exam,
        examen__heure_debut__lt=heure_fin,
        examen__heure_fin__gt=heure_debut
    ).exists()


def calculer_duree_heures(heure_debut, heure_fin):
    """Calcule la durée en heures entre deux objets time."""
    debut = datetime.combine(datetime.today(), heure_debut)
    fin   = datetime.combine(datetime.today(), heure_fin)
    return (fin - debut).seconds / 3600


def planifier_surveillances():
    """
    Algorithme principal de planification.

    ÉTAPE 1 : Trier les examens par date et heure
    ÉTAPE 2 : Affecter le responsable de matière
    ÉTAPE 3 : Compléter avec les enseignants disponibles
               (priorité aux moins chargés)
    ÉTAPE 4 : Rapport final
    """

    # Supprimer les anciennes affectations avant de replanifier
    Surveillance.objects.all().delete()

    # Récupérer tous les examens triés par date et heure
    examens = Examen.objects.all().order_by('date_exam', 'heure_debut')

    # Récupérer tous les enseignants
    tous_enseignants = list(
        Enseignant.objects.select_related('user').all()
    )

    rapport = {
        'examens_traites':      0,
        'affectations_reussies': 0,
        'examens_incomplets':   [],
        'detail':               []
    }

    for examen in examens:
        rapport['examens_traites'] += 1

        nb_requis      = examen.nb_surveillants_requis
        nb_affectes    = 0
        detail_examen  = {
            'examen':        str(examen),
            'nb_requis':     nb_requis,
            'surveillants':  [],
            'manquants':     0
        }

        # ─────────────────────────────────────────────────
        # ÉTAPE 2 : Affecter le responsable de matière
        # ─────────────────────────────────────────────────
        responsable = examen.enseignant_responsable

        if responsable:
            disponible = enseignant_est_disponible(
                responsable,
                examen.date_exam,
                examen.heure_debut,
                examen.heure_fin
            )
            occupe = enseignant_est_occupe(
                responsable,
                examen.date_exam,
                examen.heure_debut,
                examen.heure_fin
            )

            if disponible and not occupe:
                Surveillance.objects.create(
                    enseignant=responsable,
                    examen=examen,
                    role='responsable'
                )
                # Mettre à jour les heures effectuées
                duree = calculer_duree_heures(examen.heure_debut, examen.heure_fin)
                responsable.heures_effectuees += duree
                responsable.save()

                nb_affectes += 1
                detail_examen['surveillants'].append({
                    'nom':  str(responsable),
                    'role': 'responsable'
                })

        # ─────────────────────────────────────────────────
        # ÉTAPE 3 : Compléter avec d'autres enseignants
        # ─────────────────────────────────────────────────
        nb_manquant = nb_requis - nb_affectes

        if nb_manquant > 0:
            # Trouver les enseignants disponibles et non occupés
            candidats = []

            for ens in tous_enseignants:
                # Ne pas réassigner le responsable
                if responsable and ens.id == responsable.id:
                    continue

                dispo  = enseignant_est_disponible(
                    ens, examen.date_exam,
                    examen.heure_debut, examen.heure_fin
                )
                occupe = enseignant_est_occupe(
                    ens, examen.date_exam,
                    examen.heure_debut, examen.heure_fin
                )

                if dispo and not occupe:
                    candidats.append(ens)

            # Trier par heures effectuées (les moins chargés d'abord)
            candidats.sort(key=lambda e: e.heures_effectuees)

            for ens in candidats:
                if nb_manquant <= 0:
                    break

                # Priorité aux enseignants qui n'ont pas atteint leur quota
                if ens.heures_effectuees < ens.heures_surveillance_dues:
                    Surveillance.objects.create(
                        enseignant=ens,
                        examen=examen,
                        role='surveillant'
                    )
                    duree = calculer_duree_heures(examen.heure_debut, examen.heure_fin)
                    ens.heures_effectuees += duree
                    ens.save()

                    nb_affectes  += 1
                    nb_manquant  -= 1
                    detail_examen['surveillants'].append({
                        'nom':  str(ens),
                        'role': 'surveillant'
                    })

            # Si encore des manquants → prendre n'importe quel disponible
            if nb_manquant > 0:
                for ens in candidats:
                    if nb_manquant <= 0:
                        break

                    # Vérifier qu'il n'est pas déjà assigné à cet examen
                    deja_assigne = Surveillance.objects.filter(
                        enseignant=ens, examen=examen
                    ).exists()

                    if not deja_assigne:
                        Surveillance.objects.create(
                            enseignant=ens,
                            examen=examen,
                            role='remplacant'
                        )
                        duree = calculer_duree_heures(examen.heure_debut, examen.heure_fin)
                        ens.heures_effectuees += duree
                        ens.save()

                        nb_affectes  += 1
                        nb_manquant  -= 1
                        detail_examen['surveillants'].append({
                            'nom':  str(ens),
                            'role': 'remplaçant'
                        })

        # ─────────────────────────────────────────────────
        # Enregistrer le résultat de cet examen
        # ─────────────────────────────────────────────────
        detail_examen['manquants'] = max(0, nb_requis - nb_affectes)
        rapport['detail'].append(detail_examen)

        if detail_examen['manquants'] == 0:
            rapport['affectations_reussies'] += 1
        else:
            rapport['examens_incomplets'].append({
                'examen':    str(examen),
                'manquants': detail_examen['manquants']
            })

    return rapport