# Django Redmine

Clone fonctionnel de Redmine construit avec **Django 5.2**, **Tailwind CSS** (CDN), **HTMX** et **Alpine.js**.

---

## Fonctionnalités

### Gestion des projets
- Création / modification / suppression de projets (suppression réservée au créateur)
- Hiérarchie parent / sous-projet
- Projets publics ou privés
- Membres avec rôles personnalisés et permissions granulaires
- Liens d'invitation (token UUID, usage unique, expiration 7 jours)

### Tickets
- Trackers, statuts, priorités, workflow de transitions par rôle
- Vue **Kanban** (défaut) avec glisser-déposer entre colonnes
- Vue **Liste** tabulaire avec filtres avancés
- Création, modification, duplication, suppression
- **Import Excel** (.xlsx) : analyse + prévisualisation + confirmation
- Modèle Excel téléchargeable
- Champs : sujet, description, tracker, priorité, statut, assigné, dates, heures estimées, avancement, version cible, ticket parent, sous-tickets
- Relations entre tickets (bloque, précède, duplique…)
- Surveillance de tickets (Watcher) avec toggle HTMX

### Historique & commentaires
- Journal complet de toutes les modifications (statut, priorité, assigné, dates, etc.)
- Timeline visuelle avec icônes par type de champ et valeurs lisibles
- Commentaires avec insertion HTMX (sans rechargement de page)
- Changement de statut inline (HTMX)
- Slider avancement inline (HTMX)

### Versions & Roadmap
- Gestion des versions (ouverte / verrouillée / fermée)
- Roadmap avec progression par version
- Backlog (tickets sans version)

### Diagramme de Gantt
- Frappe Gantt (CDN) rendu côté serveur
- Filtres tracker / version / assigné / mode (jour, semaine, mois)
- Codes couleur : terminé (vert), en retard (rouge), en cours (bleu)

### Suivi du temps
- Saisie d'heures par ticket ou par projet
- Rapport agrégé par activité / utilisateur / période
- Intégration dans le tableau de bord personnel

### Wiki
- Pages Markdown avec Table des matières automatique
- Liens wiki `[[Nom de page]]`
- Historique de révisions, diff, rollback
- Barre d'outils Markdown dans l'éditeur

### API REST
- `GET/POST /api/v1/projects/`
- `GET/POST /api/v1/issues/` + actions journals
- `GET/POST /api/v1/versions/`
- `GET/POST /api/v1/time-entries/`
- `GET/POST /api/v1/wiki/`
- Données de référence : trackers, statuts, priorités, activités
- Authentification : Token (`Authorization: Token <token>`) ou session

### Notifications email
- Préférences par utilisateur (ticket assigné, mis à jour, commenté, wiki édité)
- Backend console en développement

### Champs personnalisés
- 8 types : texte, zone de texte, entier, décimal, date, booléen, liste, liste multiple
- Scope par tracker et/ou projet
- Interface d'administration réservée au staff
- Exposés dans l'API et l'historique

### Interface
- Thème Redmine (nav `#3D4B5A`, rouge `#C31A1A`, bleu `#5D8AB4`)
- **Mode sombre** (dark par défaut, toggle ☀/🌙, persisté en localStorage)
- Formulaires avec bordures visibles, focus ring, labels gras
- Boutons cohérents `.btn-primary` / `.btn-secondary` / `.btn-danger`
- Breadcrumbs, messages flash, pagination

---

## Stack technique

| Couche | Technologie |
|--------|-------------|
| Backend | Python 3.11, Django 5.2 |
| Base de données | SQLite (dev) / PostgreSQL (prod) |
| Frontend | Tailwind CSS CDN, HTMX 1.9, Alpine.js 3 |
| Gantt | Frappe Gantt 0.6.1 (CDN) |
| API | Django REST Framework 3.15 |
| Excel | openpyxl 3.1 |
| Email | Backend console (dev) / SMTP (prod) |

---

## Installation

### Prérequis
- Python 3.11+
- (Optionnel) PostgreSQL pour la production

### Démarrage rapide

```bash
# 1. Cloner le dépôt
git clone <url-du-repo>
cd django-redmine

# 2. Créer et activer le virtualenv
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer l'environnement
cp .env.example .env
# Éditer .env si nécessaire (SECRET_KEY, base de données, email…)

# 5. Appliquer les migrations
python manage.py migrate

# 6. Charger les données initiales (trackers, statuts, priorités, rôles, workflow)
python manage.py load_defaults

# 7. Créer un superutilisateur
python manage.py createsuperuser

# 8. Lancer le serveur
python manage.py runserver
```

Ouvrir : http://localhost:8000

---

## Variables d'environnement (`.env`)

| Variable | Valeur par défaut | Description |
|----------|-------------------|-------------|
| `DEBUG` | `True` | Mode debug Django |
| `SECRET_KEY` | `change-me-in-production` | Clé secrète Django |
| `DATABASE_URL` | `postgres://…` | URL base de données (SQLite si absent) |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Hôtes autorisés |
| `EMAIL_BACKEND` | `console` | Backend email |
| `EMAIL_HOST` | `smtp.example.com` | Serveur SMTP |
| `EMAIL_PORT` | `587` | Port SMTP |
| `EMAIL_HOST_USER` | _(vide)_ | Utilisateur SMTP |
| `EMAIL_HOST_PASSWORD` | _(vide)_ | Mot de passe SMTP |
| `EMAIL_USE_TLS` | `True` | TLS activé |
| `DEFAULT_FROM_EMAIL` | `noreply@example.com` | Expéditeur par défaut |
| `SITE_URL` | `http://localhost:8000` | URL base du site (liens emails) |

---

## Structure des applications

```
pm/               Configuration Django (settings, urls, wsgi)
accounts/         Modèle User (AbstractUser), profil, tableau de bord
core/             Permissions projet (get_user_project_permissions, mixins)
projects/         Project, Role, Membership, ProjectInvitation
issues/           Tracker, IssueStatus, IssuePriority, WorkflowTransition,
                  Issue, Journal, JournalDetail, IssueRelation, Watcher
                  + services.py, filters.py, import_excel.py
versions/         Version, Roadmap
timetracking/     TimeActivity, TimeEntry, rapport
wiki/             WikiPage, WikiPageRevision, Markdown + diff
notifications/    NotificationPreference, emails.py
customfields/     CustomField, CustomFieldValue (8 types)
api/              DRF ViewSets, serializers, Token auth
```

---

## URLs principales

| URL | Description |
|-----|-------------|
| `/` | Redirige vers le tableau de bord |
| `/my/page/` | Tableau de bord personnel |
| `/projects/` | Liste des projets |
| `/projects/<id>/` | Aperçu du projet |
| `/projects/<id>/issues/` | Kanban du projet |
| `/projects/<id>/issues/list/` | Liste des tickets |
| `/projects/<id>/issues/import/` | Import Excel |
| `/projects/<id>/gantt/` | Diagramme de Gantt |
| `/projects/<id>/roadmap/` | Roadmap & versions |
| `/projects/<id>/wiki/` | Wiki du projet |
| `/projects/<id>/settings/` | Paramètres & membres & invitations |
| `/issues/` | Kanban global |
| `/issues/list/` | Liste globale |
| `/issues/<pk>/` | Détail d'un ticket |
| `/api/v1/` | API REST |
| `/accounts/invite/<token>/` | Inscription par invitation |

---

## Gestion des accès

### Inscription
L'inscription directe est **désactivée**. Un chef de projet génère un lien d'invitation depuis les paramètres du projet. Le lien est à usage unique et expire après 7 jours.

### Permissions
Les permissions sont gérées par **rôles** assignés aux membres de chaque projet :

| Code | Description |
|------|-------------|
| `view_issues` | Voir les tickets |
| `add_issues` | Créer des tickets |
| `edit_issues` | Modifier les tickets |
| `delete_issues` | Supprimer les tickets |
| `log_time` | Saisir du temps |
| `view_time_entries` | Voir les temps |
| `manage_members` | Gérer les membres |
| `manage_versions` | Gérer les versions |
| `manage_project` | Gérer le projet |
| `view_wiki` | Voir le wiki |
| `edit_wiki` | Éditer le wiki |
| `delete_wiki_pages` | Supprimer des pages wiki |

### Suppression de projet
Seul le **créateur** du projet (ou un superutilisateur) peut le supprimer. Si le projet contient des tickets, la saisie du nom exact du projet est requise pour confirmer.

---

## Import Excel

Format attendu : fichier `.xlsx` avec une ligne d'en-tête.

| Colonne | Obligatoire | Notes |
|---------|-------------|-------|
| Sujet | ✅ | Texte libre (255 car. max) |
| Description | | Texte long |
| Tracker | | Nom du tracker ; défaut si inconnu |
| Priorité | | Nom de la priorité ; défaut si inconnue |
| Statut | | Nom du statut ; défaut si inconnu |
| Assigné à | | Username ou email |
| Date début | | YYYY-MM-DD ou DD/MM/YYYY |
| Date échéance | | YYYY-MM-DD ou DD/MM/YYYY |
| Heures estimées | | Nombre décimal |
| Avancement | | Entier 0–100 |
| Version cible | | Nom de la version du projet |

Un modèle vide est téléchargeable depuis la page d'import.

---

## API REST

### Authentification

```bash
# Obtenir un token
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -d "username=admin&password=..."

# Utiliser le token
curl http://localhost:8000/api/v1/projects/ \
  -H "Authorization: Token <votre_token>"
```

### Endpoints principaux

```
GET  /api/v1/projects/
POST /api/v1/projects/

GET  /api/v1/issues/
POST /api/v1/issues/
GET  /api/v1/issues/<pk>/
GET  /api/v1/issues/<pk>/journals/

GET  /api/v1/time-entries/
POST /api/v1/time-entries/

GET  /api/v1/wiki/
POST /api/v1/wiki/

GET  /api/v1/trackers/
GET  /api/v1/statuses/
GET  /api/v1/priorities/
GET  /api/v1/activities/
```

---

## Commandes utiles

```bash
# Données initiales
python manage.py load_defaults

# Superutilisateur
python manage.py createsuperuser

# Serveur de développement
python manage.py runserver

# Migrations
python manage.py makemigrations
python manage.py migrate
```

---

## Licence

Projet interne — tous droits réservés.
