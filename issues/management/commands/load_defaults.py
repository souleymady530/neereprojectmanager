"""
Charge les données initiales : trackers, statuts, priorités, rôles et workflow par défaut.
Usage : python manage.py load_defaults
"""

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Crée les données initiales (trackers, statuts, priorités, rôles, workflow)"

    @transaction.atomic
    def handle(self, *args, **options):
        from issues.models import Tracker, IssueStatus, IssuePriority, WorkflowTransition
        from projects.models import Role

        # --- Statuts ---
        statuses_data = [
            ("Nouveau", False, 1),
            ("En cours", False, 2),
            ("Résolu", False, 3),
            ("Retour", False, 4),
            ("Fermé", True, 5),
            ("Rejeté", True, 6),
        ]
        statuses = {}
        for name, is_closed, pos in statuses_data:
            s, created = IssueStatus.objects.get_or_create(
                name=name, defaults={"is_closed": is_closed, "position": pos}
            )
            statuses[name] = s
            if created:
                self.stdout.write(f"  Statut créé : {name}")

        # --- Priorités ---
        priorities_data = [
            ("Basse", 1, False, "#6b7280"),
            ("Normale", 2, True, "#3b82f6"),
            ("Haute", 3, False, "#f59e0b"),
            ("Urgente", 4, False, "#ef4444"),
            ("Immédiate", 5, False, "#7c3aed"),
        ]
        for name, pos, is_default, color in priorities_data:
            p, created = IssuePriority.objects.get_or_create(
                name=name, defaults={"position": pos, "is_default": is_default, "color": color}
            )
            if created:
                self.stdout.write(f"  Priorité créée : {name}")

        # --- Trackers ---
        trackers_data = [
            ("Anomalie", 1),
            ("Fonctionnalité", 2),
            ("Support", 3),
        ]
        trackers = {}
        for name, pos in trackers_data:
            t, created = Tracker.objects.get_or_create(
                name=name,
                defaults={"position": pos, "default_status": statuses["Nouveau"]},
            )
            trackers[name] = t
            if created:
                self.stdout.write(f"  Tracker créé : {name}")

        # --- Rôles ---
        roles_data = [
            ("Manager", 1, [
                "view_issues", "add_issues", "edit_issues", "delete_issues",
                "log_time", "view_time_entries",
                "manage_members", "manage_versions", "manage_project",
                "view_wiki", "edit_wiki", "delete_wiki_pages",
            ]),
            ("Développeur", 2, [
                "view_issues", "add_issues", "edit_issues",
                "log_time", "view_time_entries",
                "view_wiki", "edit_wiki",
            ]),
            ("Rapporteur", 3, [
                "view_issues", "add_issues",
                "view_wiki",
            ]),
        ]
        roles = {}
        for name, pos, perms in roles_data:
            r, created = Role.objects.get_or_create(
                name=name, defaults={"position": pos, "permissions": perms}
            )
            roles[name] = r
            if created:
                self.stdout.write(f"  Rôle créé : {name}")

        # --- Workflow : transitions par défaut ---
        # Pour chaque tracker × rôle, définir les transitions autorisées
        workflow = [
            # (old_status_name, new_status_name)
            ("Nouveau", "En cours"),
            ("Nouveau", "Rejeté"),
            ("En cours", "Résolu"),
            ("En cours", "Rejeté"),
            ("Résolu", "Fermé"),
            ("Résolu", "Retour"),
            ("Retour", "En cours"),
            ("Retour", "Rejeté"),
        ]
        dev_workflow = workflow + [
            ("Nouveau", "Résolu"),
        ]
        reporter_workflow = [
            ("Résolu", "Retour"),
            ("Résolu", "Fermé"),
        ]

        role_workflows = {
            "Manager": workflow,
            "Développeur": dev_workflow,
            "Rapporteur": reporter_workflow,
        }

        created_count = 0
        for tracker in trackers.values():
            for role_name, transitions in role_workflows.items():
                role = roles[role_name]
                for old_name, new_name in transitions:
                    _, created = WorkflowTransition.objects.get_or_create(
                        tracker=tracker,
                        role=role,
                        old_status=statuses[old_name],
                        new_status=statuses[new_name],
                    )
                    if created:
                        created_count += 1

        self.stdout.write(f"  {created_count} transitions de workflow créées.")

        # --- Activités de temps ---
        from timetracking.models import TimeActivity
        activities_data = [
            ("Développement", 1, False),
            ("Conception", 2, False),
            ("Tests", 3, False),
            ("Réunion", 4, False),
            ("Déploiement", 5, False),
            ("Support", 6, True),
        ]
        for name, pos, is_default in activities_data:
            _, created = TimeActivity.objects.get_or_create(
                name=name, defaults={"position": pos, "is_default": is_default}
            )
            if created:
                self.stdout.write(f"  Activité créée : {name}")

        self.stdout.write(self.style.SUCCESS("Données initiales chargées."))
