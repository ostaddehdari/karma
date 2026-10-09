from datetime import timedelta
from django.utils import timezone
from .models import ActivityEvent
from communication.models import Notification


def has_project_access(project, user):
    from .permissions import can_view_project
    return can_view_project(project, user)



def can_review_project(project, user):
    """کارفرما/مدیر میز یا مسئول پروژه می‌تواند کار تکمیل‌شده را بازگشایی کند."""
    from workspaces.views import can_manage
    from .models import ProjectMember
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


def log(project, user, verb, description):
    ActivityEvent.objects.create(project=project, actor=user, verb=verb, description=description)


def notify(user, title, body, url=''):
    if user:
        Notification.objects.create(user=user, title=title, body=body, url=url)


def project_progress_snapshot(project, tasks=None):
    """خلاصه مدیریتی پیشرفت برای صفحه پروژه؛ بدون تغییر داده‌ها."""
    today = timezone.localdate()
    if tasks is None:
        tasks = list(project.tasks.prefetch_related('checklist').select_related('assignee', 'task_list'))
    else:
        tasks = list(tasks)

    total = len(tasks)
    completed = sum(1 for t in tasks if t.status == 'done')
    ready = sum(1 for t in tasks if t.status != 'done' and t.effective_progress == 100)
    started = sum(1 for t in tasks if 0 < t.effective_progress < 100)
    untouched = sum(1 for t in tasks if t.effective_progress == 0)
    overdue = sum(1 for t in tasks if t.status != 'done' and t.due_date and t.due_date < today)
    due_soon = sum(1 for t in tasks if t.status != 'done' and t.due_date and today <= t.due_date <= today + timedelta(days=3))

    checklist_total = 0
    checklist_done = 0
    for task in tasks:
        items = list(task.checklist.all())
        checklist_total += len(items)
        checklist_done += sum(1 for item in items if item.is_done)

    checklist_percent = round(checklist_done * 100 / checklist_total) if checklist_total else 0
    overall = project.progress_cache

    if overall == 0:
        stage = 'شروع نشده'
        stage_icon = 'fa-seedling'
    elif overall < 25:
        stage = 'شروع پروژه'
        stage_icon = 'fa-person-running'
    elif overall < 50:
        stage = 'در حال شکل‌گیری'
        stage_icon = 'fa-layer-group'
    elif overall < 75:
        stage = 'نیمه راه'
        stage_icon = 'fa-route'
    elif overall < 100:
        stage = 'نزدیک پایان'
        stage_icon = 'fa-flag-checkered'
    else:
        stage = 'پیشرفت کامل'
        stage_icon = 'fa-trophy'

    if total == 0:
        health = 'بدون داده'
        health_class = 'neutral'
        health_icon = 'fa-circle-info'
    elif overdue >= max(2, round(total * .25)):
        health = 'نیازمند اقدام فوری'
        health_class = 'danger'
        health_icon = 'fa-triangle-exclamation'
    elif overdue:
        health = 'نیازمند توجه'
        health_class = 'warning'
        health_icon = 'fa-bell'
    elif overall >= 75:
        health = 'وضعیت عالی'
        health_class = 'success'
        health_icon = 'fa-heart-pulse'
    else:
        health = 'در مسیر مناسب'
        health_class = 'good'
        health_icon = 'fa-arrow-trend-up'

    status_counts = {key: 0 for key, _ in project.tasks.model.STATUS}
    for task in tasks:
        status_counts[task.status] = status_counts.get(task.status, 0) + 1

    status_segments = []
    labels = dict(project.tasks.model.STATUS)
    for key in ['done', 'doing', 'review', 'todo', 'blocked']:
        count = status_counts.get(key, 0)
        percent = round(count * 100 / total) if total else 0
        status_segments.append({'key': key, 'label': labels.get(key, key), 'count': count, 'percent': percent})

    milestone_total = project.milestones.count()
    milestone_done = project.milestones.filter(is_done=True).count()
    milestone_percent = round(milestone_done * 100 / milestone_total) if milestone_total else 0

    return {
        'overall': overall,
        'stage': stage,
        'stage_icon': stage_icon,
        'health': health,
        'health_class': health_class,
        'health_icon': health_icon,
        'total_tasks': total,
        'completed_tasks': completed,
        'ready_tasks': ready,
        'started_tasks': started,
        'untouched_tasks': untouched,
        'overdue_tasks': overdue,
        'due_soon_tasks': due_soon,
        'task_completion_percent': round(completed * 100 / total) if total else 0,
        'checklist_total': checklist_total,
        'checklist_done': checklist_done,
        'checklist_percent': checklist_percent,
        'status_segments': status_segments,
        'milestone_total': milestone_total,
        'milestone_done': milestone_done,
        'milestone_percent': milestone_percent,
    }
