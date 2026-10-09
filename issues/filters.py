import django_filters
from .models import Issue, Tracker, IssueStatus, IssuePriority
from django.contrib.auth import get_user_model
from versions.models import Version

User = get_user_model()


class IssueFilter(django_filters.FilterSet):
    subject = django_filters.CharFilter(lookup_expr="icontains", label="Sujet contient")
    tracker = django_filters.ModelMultipleChoiceFilter(queryset=Tracker.objects.all())
    status = django_filters.ModelMultipleChoiceFilter(queryset=IssueStatus.objects.all())
    priority = django_filters.ModelMultipleChoiceFilter(queryset=IssuePriority.objects.all())
    assigned_to = django_filters.ModelChoiceFilter(
        queryset=User.objects.all(), label="Assigné à"
    )
    fixed_version = django_filters.ModelChoiceFilter(
        queryset=Version.objects.all(), label="Version cible"
    )
    open_only = django_filters.BooleanFilter(
        field_name="status__is_closed",
        lookup_expr="exact",
        exclude=True,
        label="Tickets ouverts seulement",
    )

    class Meta:
        model = Issue
        fields = ["tracker", "status", "priority", "assigned_to", "fixed_version"]
