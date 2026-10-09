from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, View

from .models import CustomField
from .forms import CustomFieldAdminForm


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Réserve l'accès aux membres du staff (is_staff=True)."""
    def test_func(self):
        return self.request.user.is_staff


class CustomFieldListView(StaffRequiredMixin, ListView):
    model = CustomField
    template_name = "customfields/list.html"
    context_object_name = "fields"
    queryset = CustomField.objects.prefetch_related("trackers", "projects")


class CustomFieldCreateView(StaffRequiredMixin, CreateView):
    model = CustomField
    form_class = CustomFieldAdminForm
    template_name = "customfields/form.html"
    success_url = reverse_lazy("customfields:list")

    def form_valid(self, form):
        messages.success(self.request, "Champ personnalisé créé.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Nouveau champ personnalisé"
        return ctx


class CustomFieldUpdateView(StaffRequiredMixin, UpdateView):
    model = CustomField
    form_class = CustomFieldAdminForm
    template_name = "customfields/form.html"
    success_url = reverse_lazy("customfields:list")

    def form_valid(self, form):
        messages.success(self.request, "Champ mis à jour.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"Modifier : {self.object.name}"
        return ctx


class CustomFieldDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        cf = CustomField.objects.get(pk=pk)
        name = cf.name
        cf.delete()
        messages.success(request, f"Champ « {name} » supprimé.")
        return redirect("customfields:list")
