from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from .models import NotificationPreference
from .forms import NotificationPreferenceForm


class NotificationPreferenceView(LoginRequiredMixin, UpdateView):
    form_class = NotificationPreferenceForm
    template_name = "notifications/preferences.html"
    success_url = reverse_lazy("my:notifications")

    def get_object(self):
        return NotificationPreference.for_user(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Préférences de notification mises à jour.")
        return super().form_valid(form)
