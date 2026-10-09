"""Central object-level RBAC policies for projects and workspaces."""
from functools import wraps

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect


def workspace_role(workspace, user):
    if not user.is_authenticated:
        return None
    if workspace.owner_id == user.id:
        return "owner"
    return workspace.members.filter(user=user, is_active=True).values_list("role", flat=True).first()


def project_role(project, user):
    role = workspace_role(project.workspace, user)
    if role in {"owner", "admin"}:
        return role
    return project.members.filter(
        workspace_member__user=user,
        workspace_member__is_active=True,
        is_active=True,
    ).values_list("role", flat=True).first()


def can_view_project(project, user):
    return project_role(project, user) in {"owner", "admin", "manager", "member", "viewer"}


def can_edit_project(project, user):
    return project_role(project, user) in {"owner", "admin", "manager", "member"}


def can_manage_project(project, user):
    return project_role(project, user) in {"owner", "admin", "manager"}


def can_export_project(project, user):
    return can_manage_project(project, user)


def deny(request, *, api=False, fallback="dashboard"):
    if api:
        return JsonResponse({"ok": False, "error": "permission_denied"}, status=403)
    messages.error(request, "اجازه انجام این عملیات را ندارید.")
    return redirect(fallback)

