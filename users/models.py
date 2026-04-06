from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLES = [
        ('admin', 'Administrateur'),
        ('enseignant', 'Enseignant'),
        ('chef_departement', 'Chef de département'),
    ]
    role = models.CharField(max_length=20, choices=ROLES, default='enseignant')

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_enseignant(self):
        return self.role == 'enseignant'

    @property
    def is_chef(self):
        return self.role == 'chef_departement'


class Departement(models.Model):
    nom = models.CharField(max_length=100)
    chef = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='departement_dirige',
        limit_choices_to={'role': 'chef_departement'}
    )

    def __str__(self):
        return self.nom


class Enseignant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profil_enseignant')
    departement = models.ForeignKey(Departement, on_delete=models.SET_NULL, null=True, related_name='enseignants')
    heures_enseignement = models.FloatField(default=0, help_text="Heures d'enseignement par semaine")

    # Ces champs sont calculés automatiquement
    heures_surveillance_dues = models.FloatField(default=0, help_text="= heures_enseignement + report absences")
    heures_effectuees = models.FloatField(default=0, help_text="Heures de surveillance déjà effectuées")

    def __str__(self):
        return str(self.user)

    @property
    def heures_restantes(self):
        return max(0, self.heures_surveillance_dues - self.heures_effectuees)

    def recalculer_heures_dues(self):
        """Recalcule les heures dues en ajoutant les reports d'absentéisme."""
        from surveillances.models import Absenteisme
        reports = Absenteisme.objects.filter(
            enseignant=self
        ).aggregate(total=models.Sum('heures_reportees'))['total'] or 0
        self.heures_surveillance_dues = self.heures_enseignement + reports
        self.save()