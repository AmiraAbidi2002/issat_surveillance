# 📅 Système de Planification des Surveillances d'Examens — Backend

Backend du système intelligent de planification des surveillances d'examens universitaires, développé avec **Django** et **Python**.

Ce projet a été réalisé dans le cadre d'un mini-projet au **Département Informatique de l'Institut Supérieur des Sciences Appliquées et de Technologie de Sousse (ISSATSO)**.

## 📌 Présentation

La planification des surveillances d'examens est souvent réalisée manuellement à l'aide de fichiers Excel, ce qui peut entraîner :

* une répartition inéquitable des charges ;
* des erreurs humaines ;
* une gestion difficile des disponibilités ;
* une perte de temps ;
* une prise en compte limitée des contraintes des enseignants.

Le backend fournit les services nécessaires pour automatiser ce processus : gestion des données, traitement des fichiers Excel, exposition des API et génération du planning de surveillance.

## 🎯 Objectifs

Le backend a pour objectifs de :

* gérer les enseignants et leurs disponibilités ;
* gérer les examens et les affectations ;
* importer et traiter les données Excel ;
* fournir des API pour communiquer avec le frontend React ;
* automatiser la génération du planning ;
* répartir les surveillances de manière équilibrée ;
* gérer les contraintes d'indisponibilité ;
* permettre la validation du planning.

## 🏗️ Architecture

Le système global repose sur une architecture **Frontend / Backend** :

```text
                    ┌──────────────────────┐
                    │     Frontend React   │
                    │      Dashboard       │
                    └──────────┬───────────┘
                               │
                               │ HTTP / API
                               ▼
                    ┌──────────────────────┐
                    │    Backend Django    │
                    │                      │
                    │  REST API / Logic    │
                    │  Business Logic      │
                    │  Excel Processing    │
                    │  Planning Algorithm  │
                    └──────────┬───────────┘
                               │
                 ┌─────────────┴─────────────┐
                 ▼                           ▼
        ┌────────────────┐          ┌────────────────┐
        │     SQLite     │          │     Pandas     │
        │    Database    │          │  Excel / Data  │
        └────────────────┘          └────────────────┘
```

## 🛠️ Technologies utilisées

| Technologie           | Utilisation                              |
| --------------------- | ---------------------------------------- |
| Python                | Langage principal                        |
| Django                | Framework backend                        |
| Django REST Framework | Développement des API                    |
| SQLite                | Base de données                          |
| Pandas                | Lecture et traitement des fichiers Excel |
| Git / GitHub          | Gestion du code source                   |

Le choix de Django est basé notamment sur sa structure, ses mécanismes de sécurité intégrés et son ORM. SQLite a été retenue comme solution légère et adaptée à un projet académique.

## ⚙️ Fonctionnalités du Backend

### 👨‍🏫 Gestion des enseignants

Le backend permet de gérer les informations relatives aux enseignants ainsi que leurs disponibilités et contraintes.

### 📚 Gestion des examens

Les examens sont enregistrés avec les informations nécessaires à leur planification, notamment la date et les horaires.

### 📊 Importation Excel

Les données peuvent être importées depuis un fichier Excel.

Le traitement est réalisé avec **Pandas**, qui permet de lire et manipuler efficacement les données Excel.

### 🔄 Génération automatique du planning

Le backend applique un algorithme de répartition afin d'affecter automatiquement les enseignants aux différentes surveillances.

### ⚖️ Équilibrage des charges

L'algorithme cherche à répartir les heures de surveillance de manière équilibrée tout en respectant les contraintes définies.

### 🔌 API

Le backend expose des API permettant au frontend React de :

* récupérer les enseignants ;
* récupérer les examens ;
* gérer les disponibilités ;
* importer les données ;
* lancer la génération du planning ;
* récupérer les affectations ;
* consulter le planning.

## 🧠 Algorithme de planification

Le système utilise une approche hybride basée sur :

**Algorithme glouton + recherche dichotomique**

Le fonctionnement général est organisé en plusieurs étapes :

```text
1. Réinitialisation
        ↓
2. Tri des examens
        ↓
3. Affectation du responsable de matière
        ↓
4. Recherche des enseignants disponibles
        ↓
5. Affectation selon la charge restante
        ↓
6. Fallback pour les postes vacants
        ↓
7. Génération des alertes
        ↓
8. Planning final
```

L'algorithme traite les examens chronologiquement, affecte prioritairement le responsable de matière, recherche ensuite les enseignants disponibles selon leur charge restante et prévoit un mécanisme de remplacement lorsque des postes restent vacants.

## 🗃️ Modèle de données

Les principales entités du système sont :

* `Enseignant`
* `Utilisateur`
* `Examen`
* `Affectation`
* `Surveillance`
* `Département`
* `Absentéisme`
* `Disponibilité`

Ces entités permettent de représenter les enseignants, les examens, les disponibilités et les affectations nécessaires à la génération du planning.

## 🚀 Installation

### 1. Cloner le repository

```bash
git clone https://github.com/AmiraAbidi2002/jendouba-agroconnect-backend.git
cd jendouba-agroconnect-backend
```

> Remplace l'URL ci-dessus par l'URL réelle de ton repository backend si son nom est différent.

### 2. Créer un environnement virtuel

Sous Windows :

```bash
python -m venv venv
venv\Scripts\activate
```

Sous Linux / macOS :

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Appliquer les migrations

```bash
python manage.py migrate
```

### 5. Créer un compte administrateur

```bash
python manage.py createsuperuser
```

### 6. Lancer le serveur

```bash
python manage.py runserver
```

Le backend sera alors accessible localement à :

```text
http://127.0.0.1:8000/
```

## 🔗 Communication avec le Frontend

Le frontend de l'application est développé avec **React**.

La communication entre les deux parties se fait via les API du backend Django :

```text
React
  │
  │ HTTP Requests
  ▼
Django API
  │
  ├── Database
  ├── Excel Processing
  └── Planning Algorithm
```

Le frontend permet notamment l'import du fichier Excel, l'affichage du planning et la validation, tandis que Django assure le traitement côté serveur.

## 👥 Équipe

Projet réalisé par :

* **Amira Abidi** — Backend
* **Sarra Ben Rejeb** — Frontend
* **Ghada Zhani** — Algorithme & Intégration

Le développement a été organisé selon la méthodologie **Agile Scrum**, avec 6 sprints de deux semaines.

### Contribution Backend — Amira Abidi

* Développement des modèles Django
* Gestion de la base de données SQLite
* Développement des API
* Implémentation de la logique métier
* Intégration du backend avec les autres composants

## 📈 Perspectives

Les évolutions envisagées comprennent :

* optimisation de l'algorithme pour de grands volumes d'examens ;
* gestion des salles et de leurs capacités ;
* interface de modification du planning par glisser-déposer ;
* notifications automatiques aux enseignants ;
* amélioration de la scalabilité et du déploiement.
