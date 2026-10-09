from collections import defaultdict
from django.db.models import Sum
from django.utils import timezone

from projects.models import ProjectMember
from workspaces.views import can_manage
from .models import WorkLog
from .utils import current_jalali_month, month_range, human_duration


def workspace_member_for_user(workspace, user):
    return workspace.members.filter(user=user, is_active=True).first()


def can_manage_project_time(project, user):
    if can_manage(project.workspace, user):
        return True
    if project.manager and project.manager.user_id == user.id:
        return True
    return ProjectMember.objects.filter(
        project=project,
        workspace_member__user=user,
        is_active=True,
        role='manager',
    ).exists()


def active_timer_for_user(user):
    return WorkLog.objects.select_related('project', 'task', 'member').filter(
        member__user=user,
        ended_at__isnull=True,
    ).first()


def month_summary(queryset, jy=None, jm=None):
    if jy is None or jm is None:
        jy, jm = current_jalali_month()
    start, end = month_range(jy, jm)
    completed = queryset.filter(started_at__gte=start, started_at__lt=end, ended_at__isnull=False)
    total_seconds = completed.aggregate(total=Sum('duration_seconds'))['total'] or 0
    return {
        'jy': jy,
        'jm': jm,
        'start': start,
        'end': end,
        'total_seconds': total_seconds,
        'total_human': human_duration(total_seconds),
        'count': completed.count(),
    }


def report_breakdowns(queryset, start, end):
    qs = queryset.filter(started_at__gte=start, started_at__lt=end, ended_at__isnull=False)
    by_member = list(qs.values('member_id', 'member__name').annotate(total=Sum('duration_seconds')).order_by('-total'))
    by_project = list(qs.values('project_id', 'project__name').annotate(total=Sum('duration_seconds')).order_by('-total'))
    return by_member, by_project
