from django.db import models
from django.core.exceptions import ValidationError


class Disponibilite(models.Model):
    enseignant = models.ForeignKey(
        'users.Enseignant',
        on_delete=models.CASCADE,
        related_name='disponibilites'
    )
    date_dispo = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()

    class Meta:
        ordering = ['date_dispo', 'heure_debut']
        # Un enseignant ne peut pas avoir 2 créneaux identiques
        unique_together = ['enseignant', 'date_dispo', 'heure_debut']

    def clean(self):
        if self.heure_fin <= self.heure_debut:
            raise ValidationError("L'heure de fin doit être après l'heure de début.")

    def __str__(self):
        return f"{self.enseignant} — {self.date_dispo} {self.heure_debut}→{self.heure_fin}"