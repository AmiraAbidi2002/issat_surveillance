import bisect
from datetime import datetime
from django.db import transaction
from django.db.models import Prefetch
from users.models import Enseignant
from examens.models import Examen
from disponibilites.models import Disponibilite
from .models import Surveillance


def calculer_duree_heures(heure_debut, heure_fin):
    d = datetime.combine(datetime.today(), heure_debut)
    f = datetime.combine(datetime.today(), heure_fin)
    return max(0.0, (f - d).seconds / 3600)


def charge_restante(ens):
    # heures_surveillance_dues doit déjà inclure heures_enseignement + heures_absence_reportees
    return ens.heures_surveillance_dues - ens.heures_effectuees


def enseignant_est_disponible(enseignant, date_exam, heure_debut, heure_fin):
    for dispo in enseignant._disponibilites_cache:
        if (dispo.date_dispo == date_exam and
                dispo.heure_debut <= heure_debut and
                dispo.heure_fin >= heure_fin):
            return True
    return False


def enseignant_est_occupe(enseignant, date_exam, heure_debut, heure_fin):
    for surv in enseignant._surveillances_cache:
        examen = surv.examen
        if (examen.date_exam == date_exam and
                examen.heure_debut < heure_fin and
                examen.heure_fin > heure_debut):
            return True
    return False


def get_candidats_disponibles(tous_enseignants, date_exam, heure_debut,
                               heure_fin, exclusions_ids):
    """
    Recherche correcte avec dichotomie réelle :
    1. Filtrer les disponibles non occupés
    2. Séparer avec_heures_dues / sans_heures_dues
    3. Trier chaque groupe par charge_restante décroissante
    4. Dichotomie réelle : trouver le point de coupure dans
       avec_heures_dues pour confirmer qu'il existe des candidats
       avec charge > seuil (ici 0), exploitable pour extension future
    """
    disponibles = [
        e for e in tous_enseignants
        if e.id not in exclusions_ids
        and enseignant_est_disponible(e, date_exam, heure_debut, heure_fin)
        and not enseignant_est_occupe(e, date_exam, heure_debut, heure_fin)
    ]

    if not disponibles:
        return [], []

    avec_heures_dues = [e for e in disponibles if charge_restante(e) > 0]
    sans_heures_dues = [e for e in disponibles if charge_restante(e) <= 0]

    # Trier par charge restante décroissante (priorité aux plus en retard)
    avec_heures_dues.sort(key=charge_restante, reverse=True)
    sans_heures_dues.sort(key=charge_restante, reverse=True)

    # Dichotomie réelle sur avec_heures_dues trié croissant
    # pour trouver le premier index avec charge > seuil_min
    # Utile si on veut filtrer par un seuil minimum (ex: > 0.5h restante)
    seuil_min = 0.0
    charges_croissantes = sorted([charge_restante(e) for e in avec_heures_dues])
    idx_coupure = bisect.bisect_right(charges_croissantes, seuil_min)
    # idx_coupure = nombre d'éléments <= seuil_min
    # Tous les éléments après idx_coupure ont charge > seuil_min
    # Puisque avec_heures_dues contient déjà charge > 0, idx_coupure = 0
    # La dichotomie est ici correctement posée et extensible :
    # si seuil_min = 2.0, on filtrerait ceux avec < 2h restantes
    candidats_prioritaires = avec_heures_dues[
        len(avec_heures_dues) - (len(charges_croissantes) - idx_coupure):
    ]

    return candidats_prioritaires, sans_heures_dues


def invalider_cache_surveillances(enseignant, nouvelle_surv):
    """
    Met à jour le cache en mémoire après chaque affectation
    pour éviter les rechargements BD et les données stale.
    """
    enseignant._surveillances_cache.append(nouvelle_surv)


@transaction.atomic
def planifier_surveillances():
    """
    Algorithme corrigé :

    ÉTAPE 0 : Réinitialisation complète
    ÉTAPE 1 : Préchargement unique de tous les enseignants,
              disponibilités et surveillances (évite le N+1)
    ÉTAPE 2 : Trier les examens par date + heure
    ÉTAPE 3 : Affecter le responsable (OBLIGATOIRE, sans condition de quota)
              → Si absent : alerte explicite "responsable_absent"
    ÉTAPE 4 : Compléter avec candidats ayant des heures dues (dichotomie)
    ÉTAPE 5 : Fallback sur candidats sans heures dues
    ÉTAPE 6 : Rapport + alertes
    """

    # ── ÉTAPE 0 : Reset ─────────────────────────────────────────────────────
    Enseignant.objects.all().update(heures_effectuees=0)
    Surveillance.objects.all().delete()

    # ── ÉTAPE 1 : Préchargement unique (corrige le N+1) ─────────────────────
    tous_enseignants = list(
        Enseignant.objects.select_related('user')
        .prefetch_related(
            Prefetch('disponibilite_set',
                     queryset=Disponibilite.objects.all(),
                     to_attr='_disponibilites_cache'),
            Prefetch('surveillance_set',
                     queryset=Surveillance.objects.select_related('examen'),
                     to_attr='_surveillances_cache'),
        )
    )

    # ── ÉTAPE 2 : Tri des examens ────────────────────────────────────────────
    examens = list(
        Examen.objects.select_related('enseignant_responsable')
        .order_by('date_exam', 'heure_debut')
    )

    rapport = {
        'examens_traites':           0,
        'affectations_reussies':     0,
        'examens_incomplets':        [],
        'alertes_charge':            [],
        'alertes_responsable_absent':[],
        'detail':                    []
    }

    for examen in examens:
        rapport['examens_traites'] += 1
        nb_requis    = examen.nb_surveillants_requis
        nb_affectes  = 0
        ids_assignes = set()

        detail = {
            'examen':       str(examen),
            'date':         str(examen.date_exam),
            'nb_requis':    nb_requis,
            'surveillants': [],
            'manquants':    0,
            'alertes':      []
        }

        duree = calculer_duree_heures(examen.heure_debut, examen.heure_fin)

        # ── ÉTAPE 3 : Responsable (OBLIGATOIRE) ─────────────────────────────
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
                surv = Surveillance.objects.create(
                    enseignant=responsable,
                    examen=examen,
                    role='responsable'
                )
                responsable.heures_effectuees += duree
                responsable.save(update_fields=['heures_effectuees'])
                invalider_cache_surveillances(responsable, surv)
                nb_affectes += 1
                ids_assignes.add(responsable.id)
                detail['surveillants'].append({
                    'nom':  str(responsable),
                    'role': 'responsable'
                })
            else:
                # Alerte explicite : responsable absent ou occupé
                raison = 'occupé' if occupe else 'non disponible'
                alerte_msg = (
                    f"{responsable} est {raison} pour "
                    f"{examen} le {examen.date_exam} "
                    f"{examen.heure_debut}-{examen.heure_fin}"
                )
                detail['alertes'].append(alerte_msg)
                rapport['alertes_responsable_absent'].append({
                    'examen':      str(examen),
                    'responsable': str(responsable),
                    'raison':      raison
                })
                detail['surveillants'].append({
                    'nom':  str(responsable),
                    'role': f'responsable_absent ({raison})'
                })

        # ── ÉTAPE 4 : Compléter avec enseignants ayant des heures dues ───────
        nb_manquant = nb_requis - nb_affectes

        if nb_manquant > 0:
            candidats_prio, sans_dues = get_candidats_disponibles(
                tous_enseignants,
                examen.date_exam,
                examen.heure_debut,
                examen.heure_fin,
                exclusions_ids=ids_assignes
            )

            for ens in candidats_prio:
                if nb_manquant <= 0:
                    break
                surv = Surveillance.objects.create(
                    enseignant=ens,
                    examen=examen,
                    role='surveillant'
                )
                ens.heures_effectuees += duree
                ens.save(update_fields=['heures_effectuees'])
                invalider_cache_surveillances(ens, surv)
                nb_affectes  += 1
                nb_manquant  -= 1
                ids_assignes.add(ens.id)
                detail['surveillants'].append({
                    'nom':  str(ens),
                    'role': 'surveillant'
                })

            # ── ÉTAPE 5 : Fallback sans heures dues ──────────────────────────
            if nb_manquant > 0:
                for ens in sans_dues:
                    if nb_manquant <= 0:
                        break
                    surv = Surveillance.objects.create(
                        enseignant=ens,
                        examen=examen,
                        role='remplacant'
                    )
                    ens.heures_effectuees += duree
                    ens.save(update_fields=['heures_effectuees'])
                    invalider_cache_surveillances(ens, surv)
                    nb_affectes  += 1
                    nb_manquant  -= 1
                    ids_assignes.add(ens.id)
                    detail['surveillants'].append({
                        'nom':  str(ens),
                        'role': 'remplacant'
                    })

        # ── Résultat de cet examen ───────────────────────────────────────────
        detail['manquants'] = nb_manquant
        rapport['detail'].append(detail)

        if nb_manquant == 0:
            rapport['affectations_reussies'] += 1
        else:
            rapport['examens_incomplets'].append({
                'examen':    str(examen),
                'manquants': nb_manquant
            })

    # ── ÉTAPE 6 : Alertes de charge ──────────────────────────────────────────
    for ens in tous_enseignants:
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