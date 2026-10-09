from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse, FileResponse, Http404
from django.urls import reverse
import json

from .models import Workspace, WorkspaceMember
from .forms import WorkspaceForm, MemberForm, WorkspaceImportForm
from .services import attach_existing_user


def can_manage(ws, user):
    return ws.owner_id == user.id or ws.members.filter(
        user=user, role__in=['owner', 'admin'], is_active=True
    ).exists()


def can_access_workspace(ws, user):
    return ws.owner_id == user.id or ws.members.filter(user=user, is_active=True).exists()


@login_required
def workspace_logo(request, pk):
    ws = get_object_or_404(Workspace, pk=pk, is_archived=False)
    if not can_access_workspace(ws, request.user) or not ws.logo:
        raise Http404
    response = FileResponse(ws.logo.open('rb'), as_attachment=False)
    response['Cache-Control'] = 'private, max-age=3600'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@login_required
def workspace_list(request):
    # Use one Q-based queryset. Combining a non-distinct queryset with a
    # distinct queryset using | raises a TypeError on Django 5.x.
    workspaces = Workspace.objects.filter(
        Q(owner=request.user) |
        Q(members__user=request.user, members__is_active=True),
        is_archived=False,
    ).distinct().order_by('-created_at')
    manageable_ids = set(Workspace.objects.filter(Q(owner=request.user) | Q(members__user=request.user, members__role__in=['owner','admin'], members__is_active=True)).values_list('id', flat=True))
    return render(request, 'workspaces/list.html', {'workspaces': workspaces, 'manageable_ids': manageable_ids})


@login_required
def workspace_create(request):
    form = WorkspaceForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        ws = form.save(commit=False)
        ws.owner = request.user
        ws.save()
        profile = getattr(request.user, 'profile', None)
        phone = getattr(profile, 'phone', '') or request.user.username
        display = getattr(profile, 'display_name', '') or request.user.first_name or request.user.username
        WorkspaceMember.objects.create(
            workspace=ws, user=request.user, name=display, phone=phone, role='owner'
        )
        return redirect('workspace_detail', pk=ws.pk)
    return render(request, 'generic/form.html', {
        'form': form, 'title': 'ساخت میزکار', 'submit': 'ایجاد میزکار'
    })


@login_required
def workspace_detail(request, pk):
    ws = get_object_or_404(Workspace, pk=pk)
    if not can_access_workspace(ws, request.user):
        return redirect('dashboard')

    qs = ws.projects.select_related('manager').filter(is_archived=False)
    if not can_manage(ws, request.user):
        qs = qs.filter(
            members__workspace_member__user=request.user,
            members__is_active=True,
        ).distinct()

    search = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    if search:
        qs = qs.filter(name__icontains=search)
    if status:
        qs = qs.filter(status=status)

    sort = request.GET.get('sort', 'priority')
    order = {
        'priority': ['priority', 'manual_order', 'name'],
        'progress': ['-progress_cache', 'priority', 'name'],
        'deadline': ['due_date', 'priority', 'name'],
        'recent': ['-updated_at'],
        'name': ['name'],
    }.get(sort, ['priority', 'manual_order', 'name'])
    qs = qs.order_by(*order)

    from timetracking.models import WorkLog
    from timetracking.services import month_summary
    from django.db.models import Sum
    from timetracking.utils import current_jalali_month, month_range, human_duration
    jy, jm = current_jalali_month()
    start, end = month_range(jy, jm)
    time_base = WorkLog.objects.filter(project__workspace=ws)
    my_time_base = time_base.filter(member__user=request.user)
    workspace_time_month = month_summary(time_base if can_manage(ws, request.user) else my_time_base, jy, jm)
    my_time_month = month_summary(my_time_base, jy, jm)
    member_time_rows = []
    if can_manage(ws, request.user):
        raw_rows = time_base.filter(started_at__gte=start, started_at__lt=end, ended_at__isnull=False).values('member_id','member__name').annotate(total=Sum('duration_seconds')).order_by('-total')[:8]
        member_time_rows = [{'member_id': r['member_id'], 'name': r['member__name'], 'seconds': r['total'] or 0, 'human': human_duration(r['total'] or 0)} for r in raw_rows]

    return render(request, 'workspaces/detail.html', {
        'workspace': ws,
        'projects': qs,
        'members': ws.members.filter(is_active=True).select_related('user'),
        'can_manage': can_manage(ws, request.user),
        'sort': sort,
        'search': search,
        'status_filter': status,
        'project_statuses': __import__('projects.models', fromlist=['Project']).Project.STATUS,
        'quick_project_form': __import__('projects.forms', fromlist=['QuickProjectForm']).QuickProjectForm(workspace=ws),
        'workspace_time_month': workspace_time_month,
        'my_time_month': my_time_month,
        'member_time_rows': member_time_rows,
    })


@login_required
def workspace_edit(request, pk):
    ws = get_object_or_404(Workspace, pk=pk)
    if not can_manage(ws, request.user):
        return redirect('workspace_detail', pk=pk)
    form = WorkspaceForm(request.POST or None, request.FILES or None, instance=ws)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'تنظیمات میزکار ذخیره شد.')
        return redirect('workspace_detail', pk=pk)
    return render(request, 'generic/form.html', {
        'form': form, 'title': 'ویرایش میزکار', 'submit': 'ذخیره تغییرات'
    })


@login_required
def member_add(request, pk):
    ws = get_object_or_404(Workspace, pk=pk)
    if not can_manage(ws, request.user):
        return redirect('workspace_detail', pk=pk)

    form = MemberForm(request.POST or None, workspace=ws)
    if request.method == 'POST' and form.is_valid():
        member = form.save(commit=False)
        member.workspace = ws
        try:
            member.save()
        except IntegrityError:
            form.add_error('phone', 'این شماره قبلاً در میزکار وجود دارد.')
        else:
            attach_existing_user(member)
            from projects.models import ProjectMember
            for project in form.cleaned_data['project_access']:
                ProjectMember.objects.update_or_create(
                    project=project,
                    workspace_member=member,
                    defaults={'is_active': True, 'role': 'member'},
                )
            messages.success(request, 'همکار اضافه شد و دسترسی پروژه‌ها اعمال شد.')
            return redirect('workspace_detail', pk=pk)

    return render(request, 'generic/form.html', {
        'form': form,
        'title': 'افزودن همکار',
        'submit': 'افزودن همکار',
        'intro': 'فقط نام و شماره موبایل برای ثبت همکار کافی است. دسترسی پروژه‌ای را نیز می‌توانید همین‌جا انتخاب کنید.',
    })


@login_required
def workspace_delete(request, pk):
    ws = get_object_or_404(Workspace, pk=pk)
    if not can_manage(ws, request.user):
        return redirect('workspace_detail', pk=pk)
    if request.method == 'POST':
        ws.is_archived = True
        ws.save(update_fields=['is_archived'])
        messages.success(request, f'میزکار «{ws.name}» بایگانی شد. داده‌ها حذف فیزیکی نشدند.')
        return redirect('workspace_list')
    return render(request, 'generic/confirm_delete.html', {
        'title': 'حذف میزکار',
        'object_name': ws.name,
        'warning': 'برای امنیت داده‌ها، میزکار بایگانی می‌شود و اطلاعات آن در دیتابیس باقی می‌ماند.',
        'cancel_url': reverse('workspace_detail', args=[ws.pk]),
    })


@login_required
def member_edit(request, pk, member_id):
    ws = get_object_or_404(Workspace, pk=pk)
    member = get_object_or_404(WorkspaceMember, pk=member_id, workspace=ws)
    if not can_manage(ws, request.user):
        return redirect('workspace_detail', pk=pk)
    form = MemberForm(request.POST or None, instance=member, workspace=ws)
    if request.method == 'POST' and form.is_valid():
        member = form.save()
        from projects.models import ProjectMember
        selected = set(form.cleaned_data['project_access'].values_list('pk', flat=True))
        for project in ws.projects.filter(is_archived=False):
            pm, _ = ProjectMember.objects.get_or_create(project=project, workspace_member=member)
            if project.pk in selected:
                pm.is_active = True
                if pm.role == 'viewer':
                    pm.role = 'member'
            else:
                pm.is_active = member.user_id == ws.owner_id
            pm.save()
        messages.success(request, 'اطلاعات و دسترسی‌های همکار به‌روزرسانی شد.')
        return redirect('workspace_detail', pk=pk)
    if not request.method == 'POST':
        current = member.project_accesses.filter(is_active=True).values_list('project_id', flat=True)
        form.fields['project_access'].initial = list(current)
    return render(request, 'generic/form.html', {'form': form, 'title': f'ویرایش {member.name}', 'submit': 'ذخیره تغییرات'})


@login_required
def member_delete(request, pk, member_id):
    ws = get_object_or_404(Workspace, pk=pk)
    member = get_object_or_404(WorkspaceMember, pk=member_id, workspace=ws)
    if not can_manage(ws, request.user) or member.user_id == ws.owner_id:
        return redirect('workspace_detail', pk=pk)
    if request.method == 'POST':
        member.is_active = False
        member.save(update_fields=['is_active'])
        member.project_accesses.update(is_active=False)
        messages.success(request, f'همکار «{member.name}» از میزکار غیرفعال شد.')
    return redirect('workspace_detail', pk=pk)


@login_required
def workspace_export(request, pk):
    ws = get_object_or_404(Workspace, pk=pk)
    if not can_access_workspace(ws, request.user):
        return redirect('dashboard')
    from .portability import workspace_payload
    payload = workspace_payload(ws)
    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8')
    response = HttpResponse(raw, content_type='application/json; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="karma-workspace-{ws.pk}.json"'
    return response


@login_required
def workspace_import(request):
    form = WorkspaceImportForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        try:
            payload = json.loads(form.cleaned_data['file'].read().decode('utf-8-sig'))
            from .portability import import_workspace_payload
            ws = import_workspace_payload(payload, request.user)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            form.add_error('file', str(exc) or 'فایل قابل خواندن نیست.')
        else:
            messages.success(request, f'میزکار «{ws.name}» با موفقیت Import شد.')
            return redirect('workspace_detail', pk=ws.pk)
    return render(request, 'generic/form.html', {
        'form': form, 'title': 'Import میزکار', 'submit': 'وارد کردن میزکار',
        'intro': 'ساختار میزکار، اعضا، پروژه‌ها، فهرست‌ها، وظایف، چک‌لیست‌ها و نقاط عطف از فایل JSON بازیابی می‌شوند. فایل‌های رسانه‌ای در JSON جاسازی نمی‌شوند.',
    })
