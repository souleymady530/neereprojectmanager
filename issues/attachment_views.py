import os
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.views import View

from core.permissions import get_user_project_permissions
from .models import Issue, Attachment


class AttachmentUploadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        issue = get_object_or_404(Issue.objects.visible_to(request.user), pk=pk)
        perms = get_user_project_permissions(request.user, issue.project)
        if "edit_issues" not in perms and issue.author != request.user:
            return JsonResponse({"error": "Permission refusée."}, status=403)

        files = request.FILES.getlist("files")
        if not files:
            return JsonResponse({"error": "Aucun fichier reçu."}, status=400)

        created = []
        for f in files:
            if f.size > getattr(__import__("django.conf", fromlist=["settings"]).settings, "MAX_UPLOAD_SIZE", 10 * 1024 * 1024):
                continue
            att = Attachment.objects.create(
                issue=issue,
                uploaded_by=request.user,
                file=f,
                filename=f.name,
                file_size=f.size,
            )
            created.append({
                "id": att.pk,
                "filename": att.filename,
                "size": att.size_display,
                "url": att.file.url,
            })

        return JsonResponse({"attachments": created})


class AttachmentDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        att = get_object_or_404(Attachment, pk=pk)
        issue = att.issue
        perms = get_user_project_permissions(request.user, issue.project)
        if att.uploaded_by != request.user and "edit_issues" not in perms:
            return JsonResponse({"error": "Permission refusée."}, status=403)

        # Supprimer le fichier physique
        if att.file and os.path.isfile(att.file.path):
            os.remove(att.file.path)
        att.delete()
        return JsonResponse({"ok": True})
