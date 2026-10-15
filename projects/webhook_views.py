"""
Endpoint pour recevoir les webhooks GitHub / GitLab.

Format de commit supporté :
  fixes #12, closes #12, fix #12, close #12   → ferme le ticket
  ref #12, refs #12, see #12                  → ajoute un commentaire

URL à configurer dans GitHub/GitLab :
  https://project.neerelab-technologysarl.com/webhooks/git/<token>/
"""
import hashlib
import hmac
import json
import re

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import GitWebhook
from issues.models import Issue, Journal


CLOSE_PATTERNS = re.compile(
    r'\b(?:fix(?:e[sd]?)?|close[sd]?|resolve[sd]?)\s+#(\d+)',
    re.IGNORECASE,
)
REF_PATTERNS = re.compile(
    r'\b(?:refs?|see|mention[sd]?)\s+#(\d+)',
    re.IGNORECASE,
)


def _extract_commits(payload: dict, source: str) -> list[dict]:
    """Extrait la liste de commits selon la plateforme."""
    if source == "github":
        return payload.get("commits", [])
    if source == "gitlab":
        return payload.get("commits", [])
    return []


def _commit_message(commit: dict, source: str) -> str:
    if source == "github":
        return commit.get("message", "")
    if source == "gitlab":
        return commit.get("message", "")
    return ""


def _commit_url(commit: dict, source: str) -> str:
    if source == "github":
        return commit.get("url", "")
    if source == "gitlab":
        return commit.get("url", "")
    return ""


@method_decorator(csrf_exempt, name="dispatch")
class GitWebhookView(View):
    def post(self, request, token):
        try:
            hook = GitWebhook.objects.select_related("project", "close_status").get(token=token)
        except GitWebhook.DoesNotExist:
            return JsonResponse({"error": "Token invalide."}, status=404)

        # Détecter la plateforme
        ua = request.headers.get("User-Agent", "")
        event_gh = request.headers.get("X-GitHub-Event", "")
        event_gl = request.headers.get("X-Gitlab-Event", "")

        if event_gh:
            source = "github"
        elif event_gl:
            source = "gitlab"
        else:
            source = "unknown"

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "JSON invalide."}, status=400)

        commits = _extract_commits(payload, source)
        project = hook.project
        processed = []

        for commit in commits:
            message = _commit_message(commit, source)
            url = _commit_url(commit, source)
            author = commit.get("author", {}).get("name", "inconnu")

            # Tickets à fermer
            for match in CLOSE_PATTERNS.finditer(message):
                issue_id = int(match.group(1))
                try:
                    issue = Issue.objects.get(pk=issue_id, project=project)
                except Issue.DoesNotExist:
                    continue

                note = f"Fermé via commit [`{message[:72].strip()}`]({url}) par **{author}**."
                if hook.close_status:
                    old_status = issue.status
                    issue.status = hook.close_status
                    issue.save()
                    journal = Journal.objects.create(
                        issue=issue,
                        user=None,
                        notes=note,
                    )
                    from issues.models import JournalDetail
                    JournalDetail.objects.create(
                        journal=journal,
                        field="status",
                        old_value=str(old_status),
                        new_value=str(hook.close_status),
                    )
                else:
                    Journal.objects.create(issue=issue, user=None, notes=note)

                processed.append({"action": "close", "issue": issue_id})

            # Tickets référencés
            for match in REF_PATTERNS.finditer(message):
                issue_id = int(match.group(1))
                try:
                    issue = Issue.objects.get(pk=issue_id, project=project)
                except Issue.DoesNotExist:
                    continue

                note = f"Référencé dans le commit [`{message[:72].strip()}`]({url}) par **{author}**."
                Journal.objects.create(issue=issue, user=None, notes=note)
                processed.append({"action": "ref", "issue": issue_id})

        return JsonResponse({"ok": True, "processed": processed})
