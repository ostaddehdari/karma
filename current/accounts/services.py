from collections import defaultdict
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q

from .models import Profile
from .utils import DEFAULT_USER_PASSWORD, mobile_from_user, normalize_mobile


def _role_rank(role):
    return {'owner': 4, 'admin': 3, 'manager': 3, 'member': 2, 'viewer': 1}.get(role or '', 0)


def _choose_primary(users):
    return sorted(
        users,
        key=lambda u: (
            -int(bool(u.is_superuser)),
            -int(bool(u.is_staff)),
            -int(bool(u.is_active)),
            u.date_joined,
            u.pk,
        ),
    )[0]


def duplicate_mobile_groups():
    groups = defaultdict(list)
    for user in User.objects.select_related('profile').order_by('id'):
        mobile = mobile_from_user(user)
        if mobile:
            groups[mobile].append(user)
    return {mobile: users for mobile, users in groups.items() if len(users) > 1}


def _merge_project_memberships(source_wm, target_wm):
    from projects.models import ProjectMember, Project, Task

    Project.objects.filter(manager=source_wm).update(manager=target_wm)
    Task.objects.filter(assignee=source_wm).update(assignee=target_wm)

    for pm in list(ProjectMember.objects.filter(workspace_member=source_wm).order_by('id')):
        existing = ProjectMember.objects.filter(project=pm.project, workspace_member=target_wm).first()
        if existing:
            if _role_rank(pm.role) > _role_rank(existing.role):
                existing.role = pm.role
            existing.is_active = existing.is_active or pm.is_active
            existing.save(update_fields=['role', 'is_active'])
            pm.delete()
        else:
            pm.workspace_member = target_wm
            pm.save(update_fields=['workspace_member'])


def _merge_workspace_members_for_user(primary, duplicate, mobile):
    from workspaces.models import WorkspaceMember

    source_memberships = list(WorkspaceMember.objects.filter(user=duplicate).select_related('workspace').order_by('id'))
    for source in source_memberships:
        candidates = []
        for item in WorkspaceMember.objects.filter(workspace=source.workspace).exclude(pk=source.pk):
            item_mobile = normalize_mobile(item.phone)
            if item.user_id == primary.id or (mobile and item_mobile == mobile):
                candidates.append(item)
        target = sorted(candidates, key=lambda x: (-_role_rank(x.role), x.pk))[0] if candidates else None
        if target:
            _merge_project_memberships(source, target)
            if _role_rank(source.role) > _role_rank(target.role):
                target.role = source.role
            target.is_active = target.is_active or source.is_active
            target.user = primary
            if mobile:
                target.phone = mobile
            if not target.name:
                target.name = source.name
            target.save()
            source.delete()
        else:
            source.user = primary
            if mobile:
                # Only canonicalize if no same workspace/mobile row exists.
                clash = next(
                    (x for x in WorkspaceMember.objects.filter(workspace=source.workspace).exclude(pk=source.pk)
                     if normalize_mobile(x.phone) == mobile),
                    None,
                )
                if clash:
                    _merge_project_memberships(source, clash)
                    clash.user = primary
                    if _role_rank(source.role) > _role_rank(clash.role):
                        clash.role = source.role
                    clash.is_active = clash.is_active or source.is_active
                    clash.phone = mobile
                    clash.save()
                    source.delete()
                    continue
                source.phone = mobile
            source.save()


def _merge_conversation_participants(primary, duplicate):
    from communication.models import ConversationParticipant

    for part in list(ConversationParticipant.objects.filter(user=duplicate).order_by('id')):
        existing = ConversationParticipant.objects.filter(conversation=part.conversation, user=primary).first()
        if existing:
            part.delete()
        else:
            part.user = primary
            part.save(update_fields=['user'])


def merge_user_pair(primary, duplicate, mobile):
    """Move all known KARMA relations from duplicate to primary, then delete duplicate."""
    from workspaces.models import Workspace
    from projects.models import Project, Task, ActivityEvent
    from communication.models import (
        Conversation, Message, ProjectDocument, Letter, Notebook, Note, Notification,
    )

    if primary.pk == duplicate.pk:
        return

    _merge_workspace_members_for_user(primary, duplicate, mobile)
    _merge_conversation_participants(primary, duplicate)

    Workspace.objects.filter(owner=duplicate).update(owner=primary)
    Project.objects.filter(created_by=duplicate).update(created_by=primary)
    Task.objects.filter(created_by=duplicate).update(created_by=primary)
    ActivityEvent.objects.filter(actor=duplicate).update(actor=primary)
    Conversation.objects.filter(created_by=duplicate).update(created_by=primary)
    Message.objects.filter(sender=duplicate).update(sender=primary)
    ProjectDocument.objects.filter(uploaded_by=duplicate).update(uploaded_by=primary)
    Letter.objects.filter(created_by=duplicate).update(created_by=primary)
    Notebook.objects.filter(user=duplicate).update(user=primary)
    Note.objects.filter(user=duplicate).update(user=primary)
    Notification.objects.filter(user=duplicate).update(user=primary)

    # Preserve Django groups and direct permissions.
    primary.groups.add(*duplicate.groups.all())
    primary.user_permissions.add(*duplicate.user_permissions.all())

    try:
        from django.contrib.admin.models import LogEntry
        LogEntry.objects.filter(user=duplicate).update(user=primary)
    except Exception:
        pass

    primary_profile, _ = Profile.objects.get_or_create(user=primary)
    duplicate_profile = Profile.objects.filter(user=duplicate).first()
    if duplicate_profile:
        if not primary_profile.display_name and duplicate_profile.display_name:
            primary_profile.display_name = duplicate_profile.display_name
        if not primary_profile.avatar and duplicate_profile.avatar:
            primary_profile.avatar = duplicate_profile.avatar
        duplicate_profile.delete()

    if not primary.first_name and duplicate.first_name:
        primary.first_name = duplicate.first_name
    if not primary.last_name and duplicate.last_name:
        primary.last_name = duplicate.last_name
    if not primary.email and duplicate.email:
        primary.email = duplicate.email
    primary.is_active = primary.is_active or duplicate.is_active
    primary.is_staff = primary.is_staff or duplicate.is_staff
    primary.is_superuser = primary.is_superuser or duplicate.is_superuser
    primary.save()

    duplicate.delete()

    primary_profile, _ = Profile.objects.get_or_create(user=primary)
    if not primary_profile.display_name:
        primary_profile.display_name = primary.get_full_name().strip() or primary.first_name or primary.username
        # Do not canonicalize the mobile here: another duplicate in the same group
        # may still temporarily own the canonical phone/username. Normalization is
        # performed once the whole group has been merged.
        primary_profile.save(update_fields=['display_name', 'updated_at'])


def normalize_workspace_member_phones():
    from workspaces.models import WorkspaceMember
    from projects.models import ProjectMember, Project, Task

    merged = 0
    for workspace_id in WorkspaceMember.objects.values_list('workspace_id', flat=True).distinct():
        groups = defaultdict(list)
        rows = list(WorkspaceMember.objects.filter(workspace_id=workspace_id).order_by('id'))
        for row in rows:
            normalized = normalize_mobile(row.phone)
            if normalized:
                groups[normalized].append(row)
        for mobile, members in groups.items():
            if len(members) == 1:
                member = members[0]
                if member.phone != mobile:
                    member.phone = mobile
                    member.save(update_fields=['phone'])
                continue
            target = sorted(members, key=lambda x: (-_role_rank(x.role), -int(bool(x.user_id)), x.pk))[0]
            for source in members:
                if source.pk == target.pk:
                    continue
                _merge_project_memberships(source, target)
                if not target.user_id and source.user_id:
                    target.user_id = source.user_id
                if _role_rank(source.role) > _role_rank(target.role):
                    target.role = source.role
                target.is_active = target.is_active or source.is_active
                if not target.name:
                    target.name = source.name
                source.delete()
                merged += 1
            target.phone = mobile
            target.save()
    return merged


@transaction.atomic
def merge_all_duplicate_users(reset_passwords=False, password=DEFAULT_USER_PASSWORD):
    groups = duplicate_mobile_groups()
    merged_users = 0
    group_count = 0
    for mobile, users in list(groups.items()):
        # Refresh users because previous merges can change/deletes records.
        fresh_users = list(User.objects.filter(pk__in=[u.pk for u in users]).select_related('profile'))
        if len(fresh_users) < 2:
            continue
        primary = _choose_primary(fresh_users)
        for duplicate in fresh_users:
            if duplicate.pk == primary.pk:
                continue
            merge_user_pair(primary, duplicate, mobile)
            merged_users += 1
        group_count += 1

    normalize_workspace_member_phones()

    # Normalize every remaining profile and fill missing profiles.
    for user in User.objects.all().select_related('profile').order_by('id'):
        profile, _ = Profile.objects.get_or_create(user=user)
        mobile = mobile_from_user(user)
        if mobile:
            profile.phone = mobile
            profile.phone_normalized = mobile
        if not profile.display_name:
            profile.display_name = user.get_full_name().strip() or user.first_name or user.username
        profile.save()
        if mobile and not User.objects.filter(username=mobile).exclude(pk=user.pk).exists() and user.username != mobile:
            user.username = mobile
            user.save(update_fields=['username'])

    if reset_passwords:
        for user in User.objects.all():
            user.set_password(password)
            user.save(update_fields=['password'])

    return {'groups': group_count, 'merged_users': merged_users, 'remaining_users': User.objects.count()}
