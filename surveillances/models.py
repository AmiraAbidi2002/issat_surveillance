from django.db import models


class Surveillance(models.Model):
    ROLES = [
        ('responsable', 'Responsable de matière'),
        ('surveillant', 'Surveillant'),
        ('remplacant', 'Remplaçant'),
    ]

    enseignant = models.ForeignKey(
        'users.Enseignant',
        on_delete=models.CASCADE,
        related_name='surveillances'
    )
    examen = models.ForeignKey(
        'examens.Examen',
        on_delete=models.CASCADE,
        related_name='surveillants'
    )
    role = models.CharField(max_length=20, choices=ROLES, default='surveillant')
    present = models.BooleanField(default=True)
    motif_absence = models.TextField(blank=True)
    date_affectation = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Un enseignant ne peut pas être assigné 2 fois au même examen
        unique_together = ['enseignant', 'examen']

    def __str__(self):
        statut = "✓" if self.present else "✗"
        return f"{statut} {self.enseignant} → {self.examen}"


class Absenteisme(models.Model):
    """Enregistre les absences non justifiées et les heures à reporter."""
    enseignant = models.ForeignKey(
        'users.Enseignant',
        on_delete=models.CASCADE,
        related_name='absences'
    )
    surveillance = models.OneToOneField(
        Surveillance,
        on_delete=models.CASCADE,
        related_name='absenteisme'
    )
    semestre = models.IntegerField()   # 1 ou 2
    annee = models.IntegerField()      # ex: 2025
    heures_reportees = models.FloatField()  # durée de l'examen manqué

    def __str__(self):
        return f"Absence {self.enseignant} — S{self.semestre} {self.annee} — {self.heures_reportees}h"