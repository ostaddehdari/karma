from collections import defaultdict
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from dashboard.jalali import gregorian_to_jalali, to_fa_digits
from projects.models import Project
from projects.services import has_project_access
from workspaces.models import Workspace
from workspaces.views import can_access_workspace, can_manage
from .forms import ManualWorkLogForm, TimerStartForm
from .models import WorkLog
from .services import active_timer_for_user, can_manage_project_time, month_summary, report_breakdowns, workspace_member_for_user
from .utils import format_jalali_month, human_duration, jalali_month_label, month_range, parse_jalali_month, jalali_month_days


def _return(request, default_name='time_report', **kwargs):
    target = request.POST.get('next') or request.GET.get('next')
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(target)
    return redirect(default_name, **kwargs)


@login_required
def worklog_manual_add(request, project_id):
    project = get_object_or_404(Project, pk=project_id, is_archived=False)
    if not has_project_access(project, request.user):
        return redirect('dashboard')
    member = workspace_member_for_user(project.workspace, request.user)
    if not member:
        messages.error(request, 'عضویت شما در این میزکار برای ثبت زمان پیدا نشد.')
        return redirect('project_detail', pk=project.pk)

    task_id = request.POST.get('task') or request.GET.get('task')
    selected_task = project.tasks.filter(pk=task_id).first() if task_id else None
    form = ManualWorkLogForm(request.POST or None, project=project, task=selected_task)
    if request.method == 'POST' and form.is_valid():
        started_at = form.cleaned_data['started_at']
        ended_at = form.cleaned_data['ended_at']
        overlap = WorkLog.objects.filter(member=member, started_at__lt=ended_at).filter(
            Q(ended_at__gt=started_at) | Q(ended_at__isnull=True)
        ).exists()
        if overlap:
            form.add_error(None, 'این بازه با یک گزارش ساعت کاری دیگر شما هم‌پوشانی دارد.')
            return render(request, 'timetracking/manual_form.html', {'form': form, 'project': project, 'selected_task': selected_task})
        WorkLog.objects.create(
            project=project,
            task=form.cleaned_data.get('task') or selected_task,
            member=member,
            entry_type=WorkLog.MANUAL,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=int((ended_at - started_at).total_seconds()),
            note=form.cleaned_data.get('note', ''),
            created_by=request.user,
        )
        from projects.services import log
        log(project, request.user, 'worklog_created', f'گزارش کاری {human_duration((ended_at-started_at).total_seconds())} ثبت شد.')
        messages.success(request, 'بازه کاری با موفقیت ثبت شد.')
        return _return(request, 'project_detail', pk=project.pk)

    return render(request, 'timetracking/manual_form.html', {
        'form': form,
        'project': project,
        'selected_task': selected_task,
    })


@login_required
def timer_start(request, project_id):
    project = get_object_or_404(Project, pk=project_id, is_archived=False)
    if request.method != 'POST' or not has_project_access(project, request.user):
        return redirect('project_detail', pk=project.pk)
    member = workspace_member_for_user(project.workspace, request.user)
    if not member:
        messages.error(request, 'عضویت شما در میزکار برای شروع تایمر پیدا نشد.')
        return redirect('project_detail', pk=project.pk)

    task_id = request.POST.get('task')
    selected_task = project.tasks.filter(pk=task_id).first() if task_id else None
    form = TimerStartForm(request.POST, project=project, task=selected_task)
    if form.is_valid():
        try:
            with transaction.atomic():
                locked_member = type(member).objects.select_for_update().get(pk=member.pk)
                now = timezone.now()
                if WorkLog.objects.filter(member=locked_member, ended_at__isnull=True).exists():
                    raise IntegrityError('active_timer_exists')
                if WorkLog.objects.filter(member=locked_member, started_at__lte=now, ended_at__gt=now).exists():
                    raise IntegrityError('overlapping_worklog')
                item = WorkLog.objects.create(
                    project=project, task=form.cleaned_data.get('task') or selected_task,
                    member=locked_member, entry_type=WorkLog.TIMER, started_at=now,
                    note=form.cleaned_data.get('note', ''), created_by=request.user,
                )
        except IntegrityError:
            messages.warning(request, 'یک تایمر یا بازه کاری هم‌زمان فعال است؛ ابتدا آن را متوقف کنید.')
            return _return(request, 'project_detail', pk=project.pk)
        from projects.services import log
        scope = f' روی «{item.task.title}»' if item.task else ''
        log(project, request.user, 'timer_started', f'تایمر کاری{scope} شروع شد.')
        messages.success(request, 'تایمر شروع شد؛ هر زمان کار تمام شد دکمه «اتمام» را بزنید.')
    else:
        messages.error(request, 'اطلاعات تایمر معتبر نیست.')
    return _return(request, 'project_detail', pk=project.pk)


@login_required
def timer_stop(request, log_id):
    item = get_object_or_404(WorkLog.objects.select_related('project', 'member', 'task'), pk=log_id)
    if request.method != 'POST':
        return redirect('time_report')
    if item.member.user_id != request.user.id and not can_manage_project_time(item.project, request.user):
        messages.error(request, 'اجازه توقف این تایمر را ندارید.')
        return redirect('time_report')
    if item.ended_at:
        messages.info(request, 'این تایمر قبلاً متوقف شده است.')
    else:
        item.stop()
        from projects.services import log
        log(item.project, request.user, 'timer_stopped', f'تایمر کاری با مدت {human_duration(item.duration_seconds)} متوقف شد.')
        messages.success(request, f'زمان ثبت شد: {human_duration(item.duration_seconds)}')
    return _return(request, 'project_detail', pk=item.project_id)


@login_required
def worklog_delete(request, log_id):
    item = get_object_or_404(WorkLog.objects.select_related('project', 'member'), pk=log_id)
    if request.method != 'POST':
        return redirect('time_report')
    if item.member.user_id != request.user.id and not can_manage_project_time(item.project, request.user):
        messages.error(request, 'اجازه حذف این گزارش را ندارید.')
        return redirect('time_report')
    project = item.project
    duration = item.effective_seconds
    item.delete()
    from projects.services import log
    log(project, request.user, 'worklog_deleted', f'یک گزارش ساعت کاری ({human_duration(duration)}) حذف شد.')
    messages.success(request, 'گزارش ساعت کاری حذف شد.')
    return _return(request, 'time_report')


@login_required
def time_report(request):
    month_raw = request.GET.get('month', '').strip()
    try:
        jy, jm = parse_jalali_month(month_raw)
    except ValueError as exc:
        messages.warning(request, str(exc))
        jy, jm = parse_jalali_month('')
    start, end = month_range(jy, jm)

    accessible_workspaces = Workspace.objects.filter(
        Q(owner=request.user) | Q(members__user=request.user, members__is_active=True),
        is_archived=False,
    ).distinct().order_by('name')

    workspace = None
    project = None
    ws_id = request.GET.get('workspace')
    project_id = request.GET.get('project')
    member_id = request.GET.get('member')
    if ws_id:
        workspace = get_object_or_404(accessible_workspaces, pk=ws_id)
    if project_id:
        project = get_object_or_404(Project, pk=project_id, is_archived=False)
        if not has_project_access(project, request.user):
            return redirect('time_report')
        workspace = project.workspace

    base = WorkLog.objects.select_related('project', 'task', 'member', 'member__user')
    manager_mode = bool(workspace and can_manage(workspace, request.user))
    if project and can_manage_project_time(project, request.user):
        manager_mode = True

    if project:
        base = base.filter(project=project)
    elif workspace:
        base = base.filter(project__workspace=workspace)
    else:
        base = base.filter(member__user=request.user)

    if member_id and manager_mode:
        base = base.filter(member_id=member_id)
    elif not manager_mode:
        base = base.filter(member__user=request.user)

    monthly_qs = base.filter(started_at__gte=start, started_at__lt=end)
    completed_qs = monthly_qs.filter(ended_at__isnull=False)
    total_seconds = completed_qs.aggregate(total=Sum('duration_seconds'))['total'] or 0
    logs = list(monthly_qs[:250])
    by_member, by_project = report_breakdowns(base, start, end)
    for row in by_member:
        row['human'] = human_duration(row['total'])
    for row in by_project:
        row['human'] = human_duration(row['total'])

    daily = defaultdict(int)
    for row in completed_qs.values('started_at', 'duration_seconds'):
        local = timezone.localtime(row['started_at'])
        _, _, jd = gregorian_to_jalali(local.year, local.month, local.day)
        daily[jd] += row['duration_seconds'] or 0
    chart_days = list(range(1, jalali_month_days(jy, jm) + 1))
    chart_values = [round(daily[d] / 3600, 2) for d in chart_days]

    projects = Project.objects.none()
    members = []
    if workspace:
        projects = workspace.projects.filter(is_archived=False).order_by('priority', 'name')
        if manager_mode:
            members = workspace.members.filter(is_active=True).order_by('name')

    active = active_timer_for_user(request.user)
    return render(request, 'timetracking/report.html', {
        'logs': logs,
        'workspaces': accessible_workspaces,
        'workspace': workspace,
        'projects': projects,
        'project': project,
        'members': members,
        'selected_member': str(member_id or ''),
        'manager_mode': manager_mode,
        'month_value': format_jalali_month(jy, jm),
        'month_label': jalali_month_label(jy, jm),
        'total_seconds': total_seconds,
        'total_human': human_duration(total_seconds),
        'entry_count': completed_qs.count(),
        'by_member': by_member[:20],
        'by_project': by_project[:20],
        'chart_days': chart_days,
        'chart_values': chart_values,
        'active_timer': active,
    })
