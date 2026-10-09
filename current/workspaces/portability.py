"""Import/export helpers for KARMA 1.2.

The portable JSON format intentionally focuses on project-management data. Binary
attachments are not embedded; media files stay in the source installation.
"""
from __future__ import annotations

from datetime import date, datetime
from django.db import transaction

from .models import Workspace, WorkspaceMember
from projects.models import Project, ProjectMember, TaskList, Task, ChecklistItem, Milestone
from accounts.utils import normalize_mobile

FORMAT_WORKSPACE = 'karma-workspace'
FORMAT_PROJECT = 'karma-project'
FORMAT_VERSION = '1.3.0'


def _date(value):
    return value.isoformat() if value else None


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def serialize_project(project: Project) -> dict:
    lists = list(project.task_lists.all().order_by('position', 'id'))
    return {
        'source_key': f'project-{project.pk}',
        'name': project.name,
        'code': project.code,
        'description': project.description,
        'priority': project.priority,
        'status': project.status,
        'start_date': _date(project.start_date),
        'due_date': _date(project.due_date),
        'manual_order': project.manual_order,
        'manager_phone': project.manager.phone if project.manager else '',
        'task_lists': [
            {'title': item.title, 'position': item.position}
            for item in lists
        ],
        'tasks': [
            {
                'title': task.title,
                'description': task.description,
                'task_list': task.task_list.title if task.task_list else '',
                'assignee_phone': task.assignee.phone if task.assignee else '',
                'status': task.status,
                'priority': task.priority,
                'due_date': _date(task.due_date),
                'progress': task.progress,
                'checklist': [
                    {'title': x.title, 'is_done': x.is_done, 'position': x.position}
                    for x in task.checklist.all().order_by('position', 'id')
                ],
            }
            for task in project.tasks.select_related('task_list', 'assignee').prefetch_related('checklist').all().order_by('id')
        ],
        'milestones': [
            {'title': m.title, 'due_date': _date(m.due_date), 'is_done': m.is_done, 'position': m.position}
            for m in project.milestones.all().order_by('position', 'id')
        ],
    }


def workspace_payload(workspace: Workspace) -> dict:
    return {
        'format': FORMAT_WORKSPACE,
        'version': FORMAT_VERSION,
        'exported_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'note': 'فایل‌های ضمیمه و رسانه‌ها در JSON جاسازی نمی‌شوند؛ این خروجی ساختار مدیریتی و داده‌های متنی را منتقل می‌کند.',
        'workspace': {
            'name': workspace.name,
            'description': workspace.description,
            'color': workspace.color,
        },
        'members': [
            {
                'name': m.name, 'phone': m.phone, 'role': m.role, 'is_active': m.is_active,
                'project_access': [
                    {'project_key': f'project-{pm.project_id}', 'role': pm.role, 'is_active': pm.is_active}
                    for pm in m.project_accesses.filter(project__is_archived=False).select_related('project').all()
                ],
            }
            for m in workspace.members.all().order_by('id')
        ],
        'projects': [
            serialize_project(p)
            for p in workspace.projects.filter(is_archived=False).order_by('priority', 'manual_order', 'id')
        ],
    }


def project_payload(project: Project) -> dict:
    return {
        'format': FORMAT_PROJECT,
        'version': FORMAT_VERSION,
        'exported_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'note': 'فایل‌های ضمیمه و رسانه‌ها در JSON جاسازی نمی‌شوند.',
        'project': serialize_project(project),
    }


def _safe_choice(value, choices, fallback):
    keys = {x[0] for x in choices}
    return value if value in keys else fallback


def _safe_int(value, fallback, minimum=None, maximum=None):
    try:
        v = int(value)
    except (TypeError, ValueError):
        return fallback
    if minimum is not None:
        v = max(minimum, v)
    if maximum is not None:
        v = min(maximum, v)
    return v


def _ensure_member(workspace, item):
    phone = normalize_mobile(item.get('phone'))
    name = str(item.get('name') or phone or 'همکار').strip()[:120]
    if not phone:
        return None
    role = _safe_choice(item.get('role'), WorkspaceMember.ROLE_CHOICES, WorkspaceMember.MEMBER)
    member, _ = WorkspaceMember.objects.get_or_create(
        workspace=workspace,
        phone=phone,
        defaults={'name': name, 'role': role, 'is_active': bool(item.get('is_active', True))},
    )
    try:
        from .services import attach_existing_user
        attach_existing_user(member)
    except Exception:
        pass
    return member


def import_project_dict(workspace: Workspace, data: dict, user, *, name_suffix='') -> Project:
    if not isinstance(data, dict):
        raise ValueError('ساختار پروژه معتبر نیست.')
    name = str(data.get('name') or '').strip()
    if not name:
        raise ValueError('نام پروژه در فایل Import وجود ندارد.')
    if name_suffix:
        name = f'{name}{name_suffix}'
    manager = None
    manager_phone = normalize_mobile(data.get('manager_phone'))
    if manager_phone:
        manager = workspace.members.filter(phone=manager_phone, is_active=True).first()

    project = Project.objects.create(
        workspace=workspace,
        name=name[:180],
        code=str(data.get('code') or '')[:50],
        description=str(data.get('description') or ''),
        priority=_safe_int(data.get('priority'), Project.NORMAL, 1, 5),
        status=_safe_choice(data.get('status'), Project.STATUS, 'planning'),
        manager=manager,
        start_date=_parse_date(data.get('start_date')),
        due_date=_parse_date(data.get('due_date')),
        manual_order=_safe_int(data.get('manual_order'), 1000, 0),
        created_by=user,
    )

    owner_member = workspace.members.filter(user=user, is_active=True).first()
    if owner_member:
        ProjectMember.objects.update_or_create(project=project, workspace_member=owner_member, defaults={'role': 'manager', 'is_active': True})
    if manager:
        ProjectMember.objects.update_or_create(project=project, workspace_member=manager, defaults={'role': 'manager', 'is_active': True})

    list_map = {}
    for idx, item in enumerate(data.get('task_lists') or [], start=1):
        title = str(item.get('title') or '').strip()
        if not title:
            continue
        obj = TaskList.objects.create(project=project, title=title[:150], position=_safe_int(item.get('position'), idx, 0))
        list_map[title] = obj
    if not list_map:
        obj = TaskList.objects.create(project=project, title='کارهای اصلی', position=1)
        list_map[obj.title] = obj

    for item in data.get('tasks') or []:
        title = str(item.get('title') or '').strip()
        if not title:
            continue
        assignee = None
        phone = normalize_mobile(item.get('assignee_phone'))
        if phone:
            assignee = workspace.members.filter(phone=phone, is_active=True).first()
            if assignee:
                ProjectMember.objects.update_or_create(project=project, workspace_member=assignee, defaults={'role': 'member', 'is_active': True})
        task_list = list_map.get(str(item.get('task_list') or '').strip()) or next(iter(list_map.values()))
        task = Task.objects.create(
            project=project,
            task_list=task_list,
            title=title[:220],
            description=str(item.get('description') or ''),
            assignee=assignee,
            status=_safe_choice(item.get('status'), Task.STATUS, 'todo'),
            priority=_safe_int(item.get('priority'), 3, 1, 4),
            due_date=_parse_date(item.get('due_date')),
            progress=_safe_int(item.get('progress'), 0, 0, 100),
            created_by=user,
        )
        for idx, c in enumerate(item.get('checklist') or [], start=1):
            ctitle = str(c.get('title') or '').strip()
            if ctitle:
                ChecklistItem.objects.create(task=task, title=ctitle[:220], is_done=bool(c.get('is_done')), position=_safe_int(c.get('position'), idx, 0))

    for idx, item in enumerate(data.get('milestones') or [], start=1):
        title = str(item.get('title') or '').strip()
        if title:
            Milestone.objects.create(
                project=project,
                title=title[:180],
                due_date=_parse_date(item.get('due_date')),
                is_done=bool(item.get('is_done')),
                position=_safe_int(item.get('position'), idx, 0),
            )
    project.refresh_progress()
    return project


@transaction.atomic
def import_workspace_payload(payload: dict, user) -> Workspace:
    if payload.get('format') != FORMAT_WORKSPACE:
        raise ValueError('این فایل، خروجی میزکار کارما نیست.')
    meta = payload.get('workspace') or {}
    name = str(meta.get('name') or '').strip()
    if not name:
        raise ValueError('نام میزکار در فایل وجود ندارد.')
    workspace = Workspace.objects.create(
        name=f'{name} (واردشده)'[:140],
        description=str(meta.get('description') or ''),
        color=str(meta.get('color') or '#5B5BD6')[:12],
        owner=user,
    )
    profile = getattr(user, 'profile', None)
    owner_phone = normalize_mobile(getattr(profile, 'phone', '') or user.username)
    owner_name = getattr(profile, 'display_name', '') or user.first_name or user.username
    WorkspaceMember.objects.create(workspace=workspace, user=user, name=owner_name[:120], phone=owner_phone[:20], role='owner')

    member_map = {}
    for item in payload.get('members') or []:
        phone = normalize_mobile(item.get('phone'))
        if phone and phone != owner_phone:
            member = _ensure_member(workspace, item)
            if member:
                member_map[phone] = member
    owner_member = workspace.members.filter(user=user).first()
    if owner_member:
        member_map[owner_phone] = owner_member

    project_map = {}
    for project_data in payload.get('projects') or []:
        imported = import_project_dict(workspace, project_data, user)
        source_key = str(project_data.get('source_key') or '')
        if source_key:
            project_map[source_key] = imported

    # Restore workspace-member project access after all projects exist.
    for item in payload.get('members') or []:
        phone = normalize_mobile(item.get('phone'))
        member = member_map.get(phone) or workspace.members.filter(phone=phone).first()
        if not member:
            continue
        for access in item.get('project_access') or []:
            project = project_map.get(str(access.get('project_key') or ''))
            if not project:
                continue
            role = _safe_choice(access.get('role'), ProjectMember._meta.get_field('role').choices, 'member')
            ProjectMember.objects.update_or_create(
                project=project, workspace_member=member,
                defaults={'role': role, 'is_active': bool(access.get('is_active', True))},
            )
    return workspace


@transaction.atomic
def import_project_payload(payload: dict, workspace: Workspace, user) -> Project:
    if payload.get('format') != FORMAT_PROJECT:
        raise ValueError('این فایل، خروجی پروژه کارما نیست.')
    return import_project_dict(workspace, payload.get('project') or {}, user, name_suffix=' (واردشده)')
