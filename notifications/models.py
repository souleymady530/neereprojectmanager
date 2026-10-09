from django.conf import settings
from django.db import models


class NotificationPreference(models.Model):
    """Préférences de notification par utilisateur — une ligne par utilisateur."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_pref",
    )
    # --- Tickets ---
    # Reçoit un email quand un ticket lui est assigné
    notify_assigned = models.BooleanField("ticket assigné à moi", default=True)
    # Reçoit un email quand un ticket qu'il surveille est modifié
    notify_issue_updated = models.BooleanField("ticket modifié (que je surveille)", default=True)
    # Reçoit un email quand un ticket qu'il surveille reçoit un commentaire
    notify_issue_commented = models.BooleanField("nouveau commentaire (que je surveille)", default=True)
    # Reçoit un email quand un ticket lui est assigné directement
    notify_mentioned = models.BooleanField("mentionné dans un commentaire", default=True)

    # --- Wiki ---
    notify_wiki_edited = models.BooleanField("page wiki modifiée", default=False)

    class Meta:
        verbose_name = "préférence de notification"
        verbose_name_plural = "préférences de notification"

    def __str__(self):
        return f"Préférences de {self.user}"

    @classmethod
    def for_user(cls, user):
        """Retourne les préférences de l'utilisateur, les crée si elles n'existent pas."""
        pref, _ = cls.objects.get_or_create(user=user)
        return pref
