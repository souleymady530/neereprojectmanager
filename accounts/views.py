from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import CreateView, UpdateView, TemplateView
from django.urls import reverse_lazy
from .forms import RegisterForm, ProfileForm
from .models import User
from issues.models import Issue
from projects.models import Membership


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = "registration/register.html"
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Compte créé. Vous pouvez vous connecter.")
        return response


class ProfileView(LoginRequiredMixin, UpdateView):
    form_class = ProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("my:profile")

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Profil mis à jour.")
        return super().form_valid(form)


class MyPageView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/my_page.html"

    def get_context_data(self, **kwargs):
        from timetracking.models import TimeEntry
        from django.db.models import Sum
        import datetime
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
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
        ctx["week_hours"] = (
            TimeEntry.objects.filter(user=user, spent_on__gte=week_ago)
            .aggregate(t=Sum("hours"))["t"] or 0
        )
        return ctx
