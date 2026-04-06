"""
Lancez avec : python manage.py shell < populate_db.py
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import User, Departement, Enseignant

# Créer les départements
dept_info = Departement.objects.get_or_create(nom="Informatique")[0]
dept_math = Departement.objects.get_or_create(nom="Mathématiques")[0]
dept_meca = Departement.objects.get_or_create(nom="Mécanique")[0]
dept_phys = Departement.objects.get_or_create(nom="Physique")[0]

# Données enseignants : (username, prenom, nom, email, heures, dept)
data = [
    ("ben_ali",   "Mohamed",  "Ben Ali",    "benali@issat.tn",    9,  dept_info),
    ("trabelsi",  "Sonia",    "Trabelsi",   "trabelsi@issat.tn",  12, dept_info),
    ("mansour",   "Karim",    "Mansour",    "mansour@issat.tn",   6,  dept_info),
    ("kchaou",    "Fatma",    "Kchaou",     "kchaou@issat.tn",    9,  dept_info),
    ("jlassi",    "Hedi",     "Jlassi",     "jlassi@issat.tn",    15, dept_info),
    ("gharbi",    "Leila",    "Gharbi",     "gharbi@issat.tn",    9,  dept_info),
    ("hamdi",     "Youssef",  "Hamdi",      "hamdi@issat.tn",     12, dept_math),
    ("bouaziz",   "Rim",      "Bouaziz",    "bouaziz@issat.tn",   9,  dept_math),
    ("saidi",     "Amine",    "Saidi",      "saidi@issat.tn",     6,  dept_math),
    ("ferchichi", "Nadia",    "Ferchichi",  "ferchichi@issat.tn", 9,  dept_math),
    ("ouertani",  "Slim",     "Ouertani",   "ouertani@issat.tn",  12, dept_meca),
    ("zouaghi",   "Asma",     "Zouaghi",    "zouaghi@issat.tn",   9,  dept_meca),
    ("belhaj",    "Tarek",    "Belhaj",     "belhaj@issat.tn",    9,  dept_meca),
    ("chaabane",  "Olfa",     "Chaabane",   "chaabane@issat.tn",  6,  dept_phys),
    ("mhiri",     "Wael",     "Mhiri",      "mhiri@issat.tn",     12, dept_phys),
]

for username, prenom, nom, email, heures, dept in data:
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'first_name': prenom,
            'last_name':  nom,
            'email':      email,
            'role':       'enseignant',
        }
    )
    if created:
        user.set_password('Issat2025!')
        user.save()
    Enseignant.objects.get_or_create(
        user=user,
        defaults={
            'departement':           dept,
            'heures_enseignement':   heures,
            'heures_surveillance_dues': heures,
        }
    )

print(f"✅ {len(data)} enseignants créés.")