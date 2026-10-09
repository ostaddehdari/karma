from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Q
from projects.models import Project, Task
from workspaces.models import Workspace
from communication.models import ProjectDocument, Letter


def accessible_projects(user):
    return Project.objects.filter(
        Q(workspace__owner=user) |
        Q(workspace__members__user=user, workspace__members__role__in=['owner', 'admin'], workspace__members__is_active=True) |
        Q(members__workspace_member__user=user, members__is_active=True)
    ).filter(is_archived=False).distinct()


@login_required
def dashboard(request):
    projects = accessible_projects(request.user).select_related('workspace', 'manager')
    tasks = Task.objects.filter(
        assignee__user=request.user, project__is_archived=False
    ).exclude(status='done').select_related('project').order_by('due_date')[:12]
    workspaces = Workspace.objects.filter(
        Q(owner=request.user) |
        Q(members__user=request.user, members__is_active=True)
    ).filter(is_archived=False).distinct()
    stats = {
        'projects': projects.count(),
        'active': projects.filter(status='active').count(),
        'tasks': tasks.count(),
        'notifications': request.user.notifications.filter(is_read=False).count(),
    }
    chart = {
        'planning': projects.filter(status='planning').count(),
        'active': projects.filter(status='active').count(),
        'waiting': projects.filter(status='waiting').count(),
        'done': projects.filter(status='done').count(),
    }
    return render(request, 'dashboard/index.html', {
        'projects': projects.order_by('priority', '-updated_at')[:8],
        'tasks': tasks,
        'workspaces': workspaces,
        'stats': stats,
        'chart': chart,
    })


@login_required
def search(request):
    q = request.GET.get('q', '').strip()
    projects = accessible_projects(request.user)
    context = {'q': q, 'projects': [], 'tasks': [], 'documents': [], 'letters': []}
    if q:
        context['projects'] = projects.filter(Q(name__icontains=q) | Q(code__icontains=q))[:20]
        context['tasks'] = Task.objects.filter(project__in=projects).filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        ).select_related('project')[:20]
        context['documents'] = ProjectDocument.objects.filter(project__in=projects).filter(
            Q(title__icontains=q) | Q(text_content__icontains=q)
        ).select_related('project')[:20]
        context['letters'] = Letter.objects.filter(project__in=projects).filter(
            Q(subject__icontains=q) | Q(body__icontains=q) | Q(number__icontains=q)
        ).select_related('project')[:20]
    return render(request, 'dashboard/search.html', context)
