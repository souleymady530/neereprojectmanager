import django_filters
from django.contrib.auth import get_user_model
from .models import TimeEntry, TimeActivity

User = get_user_model()


class TimeEntryFilter(django_filters.FilterSet):
    spent_on__gte = django_filters.DateFilter(
        field_name="spent_on", lookup_expr="gte", label="Du",
        widget=django_filters.widgets.DateRangeWidget
    )
    spent_on__lte = django_filters.DateFilter(
        field_name="spent_on", lookup_expr="lte", label="Au",
    )
    user = django_filters.ModelChoiceFilter(
        queryset=User.objects.all(), label="Utilisateur"
    )
    activity = django_filters.ModelChoiceFilter(
        queryset=TimeActivity.objects.all(), label="Activité"
    )

    class Meta:
        model = TimeEntry
        fields = ["user", "activity"]
