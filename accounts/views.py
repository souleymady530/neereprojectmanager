from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView, UpdateView, TemplateView, View
from django.urls import reverse_lazy
from .forms import RegisterForm, ProfileForm
from .models import User
from issues.models import Issue
from projects.models import Membership


class RegisterView(View):
    """L'inscription directe est désactivée. Utiliser un lien d'invitation."""

    def get(self, request, *args, **kwargs):
        messages.error(request, "L'inscription est sur invitation uniquement. Demandez un lien à votre chef de projet.")
        return redirect("login")

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)


class AcceptInvitationView(CreateView):
    """Inscription via lien d'invitation : crée le compte et ajoute au projet."""

    form_class = RegisterForm
    template_name = "registration/accept_invitation.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        from projects.models import ProjectInvitation
        self.invitation = get_object_or_404(ProjectInvitation, token=kwargs["token"])

    def get(self, request, *args, **kwargs):
        if not self.invitation.is_valid:
            messages.error(request, "Ce lien d'invitation est invalide ou a déjà été utilisé.")
            return redirect("login")
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        from django.utils import timezone
        user = form.save()
        self.invitation.used_by = user
        self.invitation.used_at = timezone.now()
        self.invitation.save()
        membership, _ = Membership.objects.get_or_create(
            user=user, project=self.invitation.project
        )
        membership.roles.set(self.invitation.roles.all())
        messages.success(
            self.request,
            f"Compte créé ! Vous avez rejoint « {self.invitation.project.name} ». Connectez-vous."
        )
        return redirect("login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["invitation"] = self.invitation
        return ctx


class ProfileView(LoginRequiredMixin, UpdateView):
    form_class = ProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("my:profile")

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        user = form.save(commit=False)
        if self.request.POST.get("clear_avatar") == "1":
            if user.avatar:
                user.avatar.delete(save=False)
            user.avatar = None
        user.save()
        messages.success(self.request, "Profil mis à jour.")
        return redirect(self.success_url)


class MyPageView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/my_page.html"

    def get_context_data(self, **kwargs):
        from timetracking.models import TimeEntry
        from issues.models import Watcher
        from django.db.models import Sum, Count
        import datetime
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        # Décomptes précis pour les stat cards
        ctx["assigned_open_count"] = Issue.objects.filter(
            assigned_to=user, status__is_closed=False
        ).count()
        from projects.models import Project
        if user.is_superuser:
            ctx["project_count"] = Project.objects.count()
        else:
            member_ids = Membership.objects.filter(user=user).values_list("project_id", flat=True)
            public_ids = Project.objects.filter(is_public=True).values_list("id", flat=True)
            ctx["project_count"] = Project.objects.filter(
                id__in=set(member_ids) | set(public_ids)
            ).count()

        # Tickets surveillés ouverts
        ctx["watched_open_count"] = Watcher.objects.filter(
            user=user, issue__status__is_closed=False
        ).count()

        # Tickets assignés pour l'affichage (liste limitée)
        ctx["assigned_issues"] = (
            Issue.objects.filter(assigned_to=user, status__is_closed=False)
            .select_related("project", "tracker", "status", "priority")
            .order_by("-updated_at")[:20]
        )
        ctx["memberships"] = (
            Membership.objects.filter(user=user)
            .select_related("project")
            .prefetch_related("roles")
        )

        # Saisies de temps récentes (7 derniers jours)
        week_ago = datetime.date.today() - datetime.timedelta(days=7)
        ctx["recent_time_entries"] = (
            TimeEntry.objects.filter(user=user, spent_on__gte=week_ago)
            .select_related("project", "activity", "issue")
            .order_by("-spent_on", "-created_at")[:10]
        )
        raw_hours = (
            TimeEntry.objects.filter(user=user, spent_on__gte=week_ago)
            .aggregate(t=Sum("hours"))["t"] or 0
        )
        ctx["week_hours"] = round(float(raw_hours), 1)
        return ctx
