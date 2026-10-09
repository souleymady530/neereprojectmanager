"""
Commande de seed : crée les utilisateurs initiaux de la plateforme.

Usage :
    python manage.py seed_users
    python manage.py seed_users --password MonMotDePasse123

Les utilisateurs créés sont des staff (is_staff=True) ce qui leur permet
de gérer les champs personnalisés et d'avoir accès à l'administration.
Ils peuvent créer des projets et inviter d'autres membres.

Si un utilisateur existe déjà (même email), il est mis à jour sans écraser
le mot de passe existant (sauf si --password est fourni).
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

SEED_USERS = [
    {
        "email": "abdouladama7@gmail.com",
        "username": "abdouladama",
        "first_name": "Abdoul",
        "last_name": "Adama",
        "is_staff": True,
        "is_superuser": False,
    },
    {
        "email": "souleymadyouedraogo@gmail.com",
        "username": "souleymadyou",
        "first_name": "Souleymad",
        "last_name": "Yoùedraogo",
        "is_staff": True,
        "is_superuser": False,
    },
]


class Command(BaseCommand):
    help = "Crée les utilisateurs initiaux (admins projet) de la plateforme."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="Neere@2026",
            help="Mot de passe commun pour tous les utilisateurs seedés (défaut : Neere@2026)",
        )
        parser.add_argument(
            "--force-password",
            action="store_true",
            help="Réinitialise le mot de passe même si l'utilisateur existe déjà.",
        )

    def handle(self, *args, **options):
        password = options["password"]
        force_pw = options["force_password"]

        self.stdout.write(self.style.MIGRATE_HEADING("=== Seed utilisateurs ==="))

        for data in SEED_USERS:
            email = data["email"]
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": data["username"],
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "is_staff": data["is_staff"],
                    "is_superuser": data["is_superuser"],
                },
            )

            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ Créé   : {user.get_full_name()} <{email}>  "
                        f"(username: {user.username})"
                    )
                )
            else:
                # Mettre à jour les champs sans toucher au mot de passe
                changed = False
                for field in ("first_name", "last_name", "is_staff", "is_superuser"):
                    if getattr(user, field) != data[field]:
                        setattr(user, field, data[field])
                        changed = True
                if force_pw:
                    user.set_password(password)
                    changed = True
                if changed:
                    user.save()
                self.stdout.write(
                    self.style.WARNING(
                        f"  ~ Existant: {user.get_full_name()} <{email}>  "
                        f"(username: {user.username})"
                        + (" → mot de passe réinitialisé" if force_pw else "")
                    )
                )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Seed terminé."))
        self.stdout.write(
            f"  Mot de passe par défaut : {password}"
            if not force_pw
            else f"  Mot de passe appliqué   : {password}"
        )
        self.stdout.write(
            "  Modifiable via : python manage.py changepassword <username>"
        )
