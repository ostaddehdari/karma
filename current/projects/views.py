from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.utils import timezone
import json
from django.db.models import Q

from workspaces.models import Workspace
from workspaces.views import can_manage
from .models import Project, ProjectMember, Task, ChecklistItem, TaskList, Milestone
from .forms import ProjectForm, TaskForm, ChecklistForm, TaskListForm, QuickProjectForm, QuickTaskForm, MilestoneForm, ProjectImportForm
from .services import has_project_access, log, notify, project_progress_snapshot, can_review_project
from .permissions import can_edit_project, can_export_project


@login_required
def project_create(request, workspace_id):
    ws = get_object_or_404(Workspace, pk=workspace_id)
    if not can_manage(ws, request.user):
        return redirect('workspace_detail', pk=workspace_id)
    form = ProjectForm(request.POST or None, workspace=ws)
    if request.method == 'POST' and form.is_valid():
        p = form.save(commit=False)
        p.workspace = ws
        p.created_by = request.user
        p.manual_order = (ws.projects.order_by('-manual_order').values_list('manual_order', flat=True).first() or 0) + 10
        p.save()
        owner_member = ws.members.filter(user=request.user).first()
        if owner_member:
            ProjectMember.objects.update_or_create(
                project=p, workspace_member=owner_member,
                defaults={'role': 'manager', 'is_active': True},
            )
        if p.manager:
            ProjectMember.objects.update_or_create(
                project=p, workspace_member=p.manager,
                defaults={'role': 'manager', 'is_active': True},
            )
        TaskList.objects.create(project=p, title='کارهای اصلی', position=1)
        log(p, request.user, 'project_created', f'پروژه «{p.name}» ایجاد شد.')
        return redirect('project_detail', pk=p.pk)
    return render(request, 'generic/form.html', {
        'form': form, 'title': 'ایجاد پروژه', 'submit': 'ایجاد پروژه',
        'intro': 'برای هر پروژه اولویت، مدیر، تاریخ‌ها و وضعیت را مشخص کنید. دو چت «پیگیری» و «مستندات» خودکار ساخته می‌شوند.',
    })


@login_required
def project_quick_create(request, workspace_id):
    ws = get_object_or_404(Workspace, pk=workspace_id)
    if request.method != 'POST' or not can_manage(ws, request.user):
        return redirect('workspace_detail', pk=workspace_id)
    form = QuickProjectForm(request.POST, workspace=ws)
    if form.is_valid():
        p = form.save(commit=False)
        p.workspace = ws
        p.created_by = request.user
        p.status = 'planning'
        p.manual_order = (ws.projects.order_by('-manual_order').values_list('manual_order', flat=True).first() or 0) + 10
        p.save()
        owner_member = ws.members.filter(user=request.user).first()
        if owner_member:
            ProjectMember.objects.update_or_create(project=p, workspace_member=owner_member, defaults={'role': 'manager', 'is_active': True})
        if p.manager:
            ProjectMember.objects.update_or_create(project=p, workspace_member=p.manager, defaults={'role': 'manager', 'is_active': True})
        TaskList.objects.create(project=p, title='کارهای اصلی', position=1)
        log(p, request.user, 'project_created', f'پروژه «{p.name}» سریع ایجاد شد.')
        messages.success(request, f'پروژه «{p.name}» ساخته شد.')
        return redirect('project_detail', pk=p.pk)
    messages.error(request, 'اطلاعات پروژه کامل نیست؛ نام پروژه را بررسی کنید.')
    return redirect('workspace_detail', pk=workspace_id)


@login_required
def project_edit(request, pk):
    p = get_object_or_404(Project, pk=pk, is_archived=False)
    if not can_manage(p.workspace, request.user):
        return redirect('project_detail', pk=pk)
    form = ProjectForm(request.POST or None, instance=p, workspace=p.workspace)
    if request.method == 'POST' and form.is_valid():
        form.save()
        if p.manager:
            ProjectMember.objects.update_or_create(
                project=p, workspace_member=p.manager,
                defaults={'role': 'manager', 'is_active': True},
            )
        log(p, request.user, 'project_updated', f'مشخصات پروژه «{p.name}» ویرایش شد.')
        messages.success(request, 'پروژه به‌روزرسانی شد.')
        return redirect('project_detail', pk=pk)
    return render(request, 'generic/form.html', {
        'form': form, 'title': f'ویرایش {p.name}', 'submit': 'ذخیره تغییرات'
    })


@login_required
def project_detail(request, pk):
    p = get_object_or_404(Project, pk=pk, is_archived=False)
    if not has_project_access(p, request.user):
        return redirect('dashboard')
    project_tasks = list(
        p.tasks.select_related('assignee', 'task_list').prefetch_related('checklist').all().order_by('status', 'due_date')
    )
    progress_stats = project_progress_snapshot(p, project_tasks)
    allowed_conversations = p.conversations.filter(
        Q(kind__in=['follow_up', 'documents', 'custom']) |
        Q(kind='private', participants__user=request.user)
    ).distinct().order_by('kind', 'title')
    from timetracking.models import WorkLog
    from timetracking.forms import ManualWorkLogForm, TimerStartForm
    from timetracking.services import active_timer_for_user, month_summary, workspace_member_for_user
    time_base = WorkLog.objects.filter(project=p)
    project_time_month = month_summary(time_base)
    my_member = workspace_member_for_user(p.workspace, request.user)
    my_time_month = month_summary(time_base.filter(member=my_member)) if my_member else {'total_human': '۰ دقیقه', 'count': 0}
    recent_work_logs = WorkLog.objects.select_related('member', 'task').filter(project=p)[:6]
    active_timer = active_timer_for_user(request.user)

    return render(request, 'projects/detail.html', {
        'project': p,
        'tasks': project_tasks[:40],
        'task_lists': p.task_lists.prefetch_related('tasks').all().order_by('position', 'title'),
        'activities': p.activities.all()[:30],
        'members': p.members.select_related('workspace_member', 'workspace_member__user').filter(is_active=True),
        'milestones': p.milestones.all().order_by('position'),
        'project_conversations': allowed_conversations,
        'can_manage_project': can_manage(p.workspace, request.user),
        'can_review_project': can_review_project(p, request.user),
        'quick_task_form': QuickTaskForm(project=p),
        'progress_stats': progress_stats,
        'project_time_month': project_time_month,
        'my_time_month': my_time_month,
        'recent_work_logs': recent_work_logs,
        'active_timer': active_timer,
        'manual_worklog_form': ManualWorkLogForm(project=p),
        'timer_start_form': TimerStartForm(project=p),
    })


@login_required
def project_members(request, pk):
    p = get_object_or_404(Project, pk=pk, is_archived=False)
    if not can_manage(p.workspace, request.user):
        return redirect('project_detail', pk=pk)
    if request.method == 'POST':
        selected = set(request.POST.getlist('members'))
        for wm in p.workspace.members.filter(is_active=True):
            pm, _ = ProjectMember.objects.get_or_create(project=p, workspace_member=wm)
            should_be_active = str(wm.pk) in selected or wm.user_id == p.workspace.owner_id
            changed = pm.is_active != should_be_active
            pm.is_active = should_be_active
            if wm.user_id == p.workspace.owner_id:
                pm.role = 'manager'
            pm.save()
            if changed and pm.is_active and wm.user:
                notify(
                    wm.user, 'دسترسی پروژه',
                    f'دسترسی شما به پروژه «{p.name}» فعال شد.',
                    f'/projects/{p.pk}/',
                )
        log(p, request.user, 'access_updated', 'دسترسی اعضای پروژه به‌روزرسانی شد.')
        messages.success(request, 'دسترسی اعضای پروژه به‌روزرسانی شد.')
        return redirect('project_members', pk=pk)
    active = set(str(x) for x in p.members.filter(is_active=True).values_list('workspace_member_id', flat=True))
    return render(request, 'projects/members.html', {
        'project': p,
        'workspace_members': p.workspace.members.filter(is_active=True).order_by('name'),
        'active_ids': active,
    })


@login_required
def task_list_create(request, pk):
    p = get_object_or_404(Project, pk=pk, is_archived=False)
    if not can_edit_project(p, request.user):
        return redirect('dashboard')
    form = TaskListForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.project = p
        item.position = p.task_lists.count() + 1
        item.save()
        log(p, request.user, 'task_list_created', f'فهرست «{item.title}» ایجاد شد.')
        return redirect('project_detail', pk=pk)
    return render(request, 'generic/form.html', {
        'form': form, 'title': 'فهرست جدید', 'submit': 'ایجاد فهرست'
    })


@login_required
def task_create(request, pk):
    p = get_object_or_404(Project, pk=pk, is_archived=False)
    if not can_edit_project(p, request.user):
        return redirect('dashboard')
    form = TaskForm(request.POST or None, project=p)
    if request.method == 'POST' and form.is_valid():
        t = form.save(commit=False)
        t.project = p
        t.created_by = request.user
        t.save()
        if t.status == 'done':
            t.mark_done()
        else:
            t.sync_progress_from_checklist()
        p.refresh_progress()
        log(p, request.user, 'task_created', f'وظیفه «{t.title}» ایجاد شد.')
        if t.assignee and t.assignee.user:
            notify(
                t.assignee.user, 'وظیفه جدید',
                f'وظیفه «{t.title}» به شما واگذار شد.',
                f'/projects/tasks/{t.pk}/',
            )
        return redirect('project_detail', pk=pk)
    return render(request, 'generic/form.html', {
        'form': form, 'title': 'ایجاد وظیفه', 'submit': 'ایجاد'
    })


@login_required
def task_quick_create(request, pk):
    p = get_object_or_404(Project, pk=pk, is_archived=False)
    if request.method != 'POST' or not can_edit_project(p, request.user):
        return redirect('project_detail', pk=pk)
    form = QuickTaskForm(request.POST, project=p)
    if form.is_valid():
        t = form.save(commit=False)
        t.project = p
        t.created_by = request.user
        t.status = 'todo'
        t.progress = 0
        if not t.task_list:
            t.task_list = p.task_lists.order_by('position').first()
        t.save()
        p.refresh_progress()
        log(p, request.user, 'task_created', f'وظیفه «{t.title}» سریع ایجاد شد.')
        if t.assignee and t.assignee.user:
            notify(t.assignee.user, 'وظیفه جدید', f'وظیفه «{t.title}» به شما واگذار شد.', f'/projects/tasks/{t.pk}/')
        messages.success(request, f'وظیفه «{t.title}» اضافه شد.')
    else:
        messages.error(request, 'عنوان وظیفه را وارد کنید.')
    return redirect('project_detail', pk=pk)


@login_required
def task_detail(request, task_id):
    t = get_object_or_404(Task.objects.select_related('project', 'assignee', 'task_list').prefetch_related('checklist'), pk=task_id)
    if not has_project_access(t.project, request.user):
        return redirect('dashboard')
    form = ChecklistForm(request.POST or None)
    if request.method == 'POST' and not can_edit_project(t.project, request.user):
        return redirect('project_detail', pk=t.project_id)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.task = t
        item.position = t.checklist.count() + 1
        item.save()
        # افزودن آیتم جدید باید همان لحظه درصد وظیفه و پروژه را واقعی کند.
        t = Task.objects.prefetch_related('checklist').get(pk=t.pk)
        t.sync_progress_from_checklist()
        t.project.refresh_progress()
        log(t.project, request.user, 'checklist_created', f'آیتم چک‌لیست برای «{t.title}» اضافه شد.')
        return redirect('task_detail', task_id=t.pk)
    from timetracking.models import WorkLog
    from timetracking.forms import ManualWorkLogForm, TimerStartForm
    from timetracking.services import active_timer_for_user, month_summary, workspace_member_for_user
    member = workspace_member_for_user(t.project.workspace, request.user)
    task_time_base = WorkLog.objects.filter(task=t)
    task_time_month = month_summary(task_time_base)
    my_task_time_month = month_summary(task_time_base.filter(member=member)) if member else {'total_human': '۰ دقیقه', 'count': 0}
    recent_work_logs = WorkLog.objects.select_related('member').filter(task=t)[:8]
    return render(request, 'projects/task_detail.html', {
        'task': t, 'form': form,
        'task_effective_progress': t.effective_progress,
        'checklist_progress': t.checklist_progress,
        'can_review_project': can_review_project(t.project, request.user),
        'task_time_month': task_time_month,
        'my_task_time_month': my_task_time_month,
        'recent_work_logs': recent_work_logs,
        'active_timer': active_timer_for_user(request.user),
        'manual_worklog_form': ManualWorkLogForm(project=t.project, task=t),
        'timer_start_form': TimerStartForm(project=t.project, task=t),
    })


@login_required
def checklist_toggle(request, item_id):
    item = get_object_or_404(ChecklistItem, pk=item_id)
    if not can_edit_project(item.task.project, request.user):
        return redirect('dashboard')
    if request.method == 'POST':
        # تیک‌زدن برای اعضای پروژه مجاز است؛ برداشتن تیکِ انجام‌شده فقط برای کارفرما/مدیر پروژه.
        if item.is_done and not can_review_project(item.task.project, request.user):
            messages.error(request, 'فقط کارفرما یا مسئول پروژه می‌تواند یک مورد تأییدشده را بازگشایی کند.')
            return redirect('task_detail', task_id=item.task_id)
        item.is_done = not item.is_done
        item.save(update_fields=['is_done'])
        task = Task.objects.prefetch_related('checklist').get(pk=item.task_id)
        if not item.is_done and task.status == 'done':
            task.reopen('review')
            task = Task.objects.prefetch_related('checklist').get(pk=task.pk)
            messages.warning(request, 'به‌دلیل وجود ایراد، وظیفه از حالت تکمیل‌شده خارج و وارد بازبینی شد.')
        task.sync_progress_from_checklist()
        task.project.refresh_progress()
        state = 'تکمیل شد' if item.is_done else 'توسط مدیر بازگشایی شد'
        log(task.project, request.user, 'checklist_toggled', f'چک‌لیست «{item.title}» {state}.')
    return redirect('task_detail', task_id=item.task_id)


@login_required
def board(request, pk):
    p = get_object_or_404(Project, pk=pk, is_archived=False)
    if not has_project_access(p, request.user):
        return redirect('dashboard')
    columns = [
        (key, label, p.tasks.filter(status=key).select_related('assignee').prefetch_related('checklist').order_by('due_date', 'priority'))
        for key, label in Task.STATUS
    ]
    return render(request, 'projects/board.html', {'project': p, 'columns': columns})


@login_required
def task_status(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    if request.method != 'POST' or not can_edit_project(task.project, request.user):
        return JsonResponse({'ok': False}, status=403)
    status = request.POST.get('status')
    valid = {x[0] for x in Task.STATUS}
    if status not in valid:
        return JsonResponse({'ok': False, 'error': 'invalid status'}, status=400)
    old = task.status
    if old == 'done' and status != 'done' and not can_review_project(task.project, request.user):
        return JsonResponse({'ok': False, 'error': 'فقط کارفرما یا مسئول پروژه می‌تواند کار تکمیل‌شده را بازگشایی کند.'}, status=403)
    if status == 'done':
        task.mark_done()
    else:
        task.status = status
        task.completed_at = None
        if old == 'done' and not task.checklist.exists():
            task.progress = 0
        task.save(update_fields=['status', 'progress', 'completed_at', 'updated_at'])
        task = Task.objects.prefetch_related('checklist').get(pk=task.pk)
        task.sync_progress_from_checklist()
    task.project.refresh_progress()
    if old != status:
        log(task.project, request.user, 'task_status', f'وضعیت «{task.title}» به {task.get_status_display()} تغییر کرد.')
        if task.assignee and task.assignee.user and task.assignee.user_id != request.user.id:
            notify(
                task.assignee.user, 'تغییر وضعیت وظیفه',
                f'وضعیت «{task.title}» به {task.get_status_display()} تغییر کرد.',
                f'/projects/tasks/{task.pk}/',
            )
    return JsonResponse({'ok': True, 'progress': task.project.progress_cache})


@login_required
def project_delete(request, pk):
    p = get_object_or_404(Project, pk=pk, is_archived=False)
    if not can_manage(p.workspace, request.user):
        return redirect('project_detail', pk=pk)
    if request.method == 'POST':
        p.is_archived = True
        p.save(update_fields=['is_archived'])
        messages.success(request, f'پروژه «{p.name}» بایگانی شد و داده‌های آن در دیتابیس حفظ شدند.')
        return redirect('workspace_detail', pk=p.workspace_id)
    return render(request, 'generic/confirm_delete.html', {
        'title': 'حذف پروژه', 'object_name': p.name,
        'warning': 'این عملیات پروژه را بایگانی می‌کند؛ وظایف، گفتگوها و مستندات آن حذف فیزیکی نمی‌شوند.',
        'cancel_url': reverse('project_detail', args=[p.pk]),
    })


@login_required
def project_export(request, pk):
    p = get_object_or_404(Project, pk=pk, is_archived=False)
    if not can_export_project(p, request.user):
        return redirect('dashboard')
    from workspaces.portability import project_payload
    raw = json.dumps(project_payload(p), ensure_ascii=False, indent=2).encode('utf-8')
    response = HttpResponse(raw, content_type='application/json; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="karma-project-{p.pk}.json"'
    return response


@login_required
def project_import(request, workspace_id):
    ws = get_object_or_404(Workspace, pk=workspace_id, is_archived=False)
    if not can_manage(ws, request.user):
        return redirect('workspace_detail', pk=workspace_id)
    form = ProjectImportForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        try:
            payload = json.loads(form.cleaned_data['file'].read().decode('utf-8-sig'))
            from workspaces.portability import import_project_payload
            project = import_project_payload(payload, ws, request.user)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            form.add_error('file', str(exc) or 'فایل پروژه قابل خواندن نیست.')
        else:
            log(project, request.user, 'project_imported', f'پروژه «{project.name}» از فایل Import شد.')
            messages.success(request, f'پروژه «{project.name}» با موفقیت Import شد.')
            return redirect('project_detail', pk=project.pk)
    return render(request, 'generic/form.html', {
        'form': form, 'title': f'Import پروژه در {ws.name}', 'submit': 'وارد کردن پروژه',
        'intro': 'فهرست‌ها، وظایف، چک‌لیست‌ها و نقاط عطف پروژه بازیابی می‌شوند. رسانه‌ها داخل فایل JSON جاسازی نمی‌شوند.',
    })


@login_required
def task_edit(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    if not can_edit_project(task.project, request.user):
        return redirect('dashboard')
    form = TaskForm(request.POST or None, instance=task, project=task.project)
    if request.method == 'POST' and form.is_valid():
        task = form.save()
        task = Task.objects.prefetch_related('checklist').get(pk=task.pk)
        if task.status == 'done':
            task.mark_done()
        elif task.checklist.exists():
            task.sync_progress_from_checklist()
        else:
            task.completed_at = None
            task.save(update_fields=['completed_at'])
        task.project.refresh_progress()
        log(task.project, request.user, 'task_updated', f'وظیفه «{task.title}» ویرایش شد.')
        messages.success(request, 'وظیفه ویرایش شد.')
        return redirect('task_detail', task_id=task.pk)
    return render(request, 'generic/form.html', {'form': form, 'title': f'ویرایش وظیفه: {task.title}', 'submit': 'ذخیره تغییرات'})


@login_required
def task_delete(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    project = task.project
    if not can_edit_project(project, request.user):
        return redirect('dashboard')
    if request.method == 'POST':
        title = task.title
        task.delete()
        project.refresh_progress()
        log(project, request.user, 'task_deleted', f'وظیفه «{title}» حذف شد.')
        messages.success(request, 'وظیفه حذف شد.')
        return redirect('project_detail', pk=project.pk)
    return render(request, 'generic/confirm_delete.html', {
        'title': 'حذف وظیفه', 'object_name': task.title,
        'warning': 'چک‌لیست‌های داخل این وظیفه نیز حذف می‌شوند.',
        'cancel_url': reverse('task_detail', args=[task.pk]),
    })


@login_required
def task_list_edit(request, list_id):
    item = get_object_or_404(TaskList, pk=list_id)
    if not can_edit_project(item.project, request.user):
        return redirect('dashboard')
    form = TaskListForm(request.POST or None, instance=item)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'نام فهرست ویرایش شد.')
        return redirect('project_detail', pk=item.project_id)
    return render(request, 'generic/form.html', {'form': form, 'title': 'ویرایش فهرست', 'submit': 'ذخیره'})


@login_required
def task_list_delete(request, list_id):
    item = get_object_or_404(TaskList, pk=list_id)
    project = item.project
    if not can_edit_project(project, request.user):
        return redirect('dashboard')
    if request.method == 'POST':
        title = item.title
        item.delete()  # Task.task_list uses SET_NULL; tasks are preserved.
        log(project, request.user, 'task_list_deleted', f'فهرست «{title}» حذف شد؛ وظایف آن حفظ شدند.')
        messages.success(request, 'فهرست حذف شد و وظایف آن بدون فهرست باقی ماندند.')
        return redirect('project_detail', pk=project.pk)
    return render(request, 'generic/confirm_delete.html', {
        'title': 'حذف فهرست', 'object_name': item.title,
        'warning': 'خود وظایف حذف نمی‌شوند و فقط اتصال آن‌ها به این فهرست برداشته می‌شود.',
        'cancel_url': reverse('project_detail', args=[project.pk]),
    })


@login_required
def checklist_edit(request, item_id):
    item = get_object_or_404(ChecklistItem, pk=item_id)
    if not can_edit_project(item.task.project, request.user):
        return redirect('dashboard')
    form = ChecklistForm(request.POST or None, instance=item)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('task_detail', task_id=item.task_id)
    return render(request, 'generic/form.html', {'form': form, 'title': 'ویرایش آیتم چک‌لیست', 'submit': 'ذخیره'})


@login_required
def checklist_delete(request, item_id):
    item = get_object_or_404(ChecklistItem, pk=item_id)
    task = item.task
    if not can_edit_project(task.project, request.user):
        return redirect('dashboard')
    if request.method == 'POST':
        item.delete()
        task = Task.objects.prefetch_related('checklist').get(pk=task.pk)
        task.sync_progress_from_checklist()
        task.project.refresh_progress()
    return redirect('task_detail', task_id=task.pk)


@login_required
def task_complete_toggle(request, task_id):
    task = get_object_or_404(Task.objects.prefetch_related('checklist'), pk=task_id)
    if request.method != 'POST' or not can_edit_project(task.project, request.user):
        return redirect('dashboard')

    if task.status == 'done':
        if not can_review_project(task.project, request.user):
            messages.error(request, 'فقط کارفرما یا مسئول پروژه می‌تواند وظیفه تکمیل‌شده را بازگشایی کند.')
            return redirect('task_detail', task_id=task.pk)
        reason = (request.POST.get('reason') or '').strip()
        task.reopen('review')
        suffix = f' علت: {reason}' if reason else ''
        log(task.project, request.user, 'task_reopened', f'وظیفه «{task.title}» به‌دلیل نیاز به اصلاح دوباره باز شد.{suffix}')
        messages.warning(request, f'وظیفه «{task.title}» برای اصلاح به بازبینی برگشت.')
    else:
        task.mark_done()
        log(task.project, request.user, 'task_completed', f'وظیفه «{task.title}» تکمیل شد.')
        messages.success(request, f'وظیفه «{task.title}» تکمیل شد و پیشرفت پروژه به‌روز شد.')

    task.project.refresh_progress()
    if request.POST.get('return_to') == 'project':
        return redirect('project_detail', pk=task.project_id)
    return redirect('task_detail', task_id=task.pk)


@login_required
def milestone_create(request, pk):
    p = get_object_or_404(Project, pk=pk, is_archived=False)
    if not can_edit_project(p, request.user):
        return redirect('dashboard')
    form = MilestoneForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        m = form.save(commit=False)
        m.project = p
        m.position = p.milestones.count() + 1
        m.save()
        log(p, request.user, 'milestone_created', f'نقطه عطف «{m.title}» اضافه شد.')
        return redirect('project_detail', pk=p.pk)
    return render(request, 'generic/form.html', {'form': form, 'title': 'نقطه عطف جدید', 'submit': 'افزودن'})


@login_required
def milestone_edit(request, milestone_id):
    m = get_object_or_404(Milestone, pk=milestone_id)
    if not can_edit_project(m.project, request.user):
        return redirect('dashboard')
    form = MilestoneForm(request.POST or None, instance=m)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('project_detail', pk=m.project_id)
    return render(request, 'generic/form.html', {'form': form, 'title': 'ویرایش نقطه عطف', 'submit': 'ذخیره'})


@login_required
def milestone_toggle(request, milestone_id):
    m = get_object_or_404(Milestone, pk=milestone_id)
    if request.method != 'POST' or not can_edit_project(m.project, request.user):
        return redirect('dashboard')
    m.is_done = not m.is_done
    m.save(update_fields=['is_done'])
    state = 'تکمیل شد' if m.is_done else 'باز شد'
    log(m.project, request.user, 'milestone_toggled', f'نقطه عطف «{m.title}» {state}.')
    return redirect('project_detail', pk=m.project_id)


@login_required
def milestone_delete(request, milestone_id):
    m = get_object_or_404(Milestone, pk=milestone_id)
    project_id = m.project_id
    if not can_edit_project(m.project, request.user):
        return redirect('dashboard')
    if request.method == 'POST':
        m.delete()
    return redirect('project_detail', pk=project_id)
