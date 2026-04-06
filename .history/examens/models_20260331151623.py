from django.db import models
import math


class Examen(models.Model):
    matiere = models.CharField(max_length=100)
    classe = models.CharField(max_length=50)
    date_exam = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    salle = models.CharField(max_length=50)
    nb_etudiants = models.IntegerField(default=30)
    enseignant_responsable = models.ForeignKey(
        'users.Enseignant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='examens_responsable'
    )

    # Calculé automatiquement à la sauvegarde
    nb_surveillants_requis = models.IntegerField(default=1)

    def save(self, *args, **kwargs):
        # Règle : 1 surveillant par tranche de 30 étudiants
        self.nb_surveillants_requis = max(1, math.ceil(self.nb_etudiants / 30))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.matiere} — {self.classe} — {self.date_exam}"

    class Meta:
        ordering = ['date_exam', 'heure_debut']