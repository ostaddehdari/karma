from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from workspaces.models import Workspace, WorkspaceMember
from .models import Project, ProjectMember, Task


class ProjectRBACIntegrationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', password='x')
        self.viewer = User.objects.create_user('viewer', password='x')
        self.member_user = User.objects.create_user('member', password='x')
        self.ws = Workspace.objects.create(name='Secure workspace', owner=self.owner)
        self.owner_member = WorkspaceMember.objects.create(workspace=self.ws, user=self.owner, name='Owner', phone='09120000001', role='owner')
        self.viewer_member = WorkspaceMember.objects.create(workspace=self.ws, user=self.viewer, name='Viewer', phone='09120000002', role='member')
        self.member = WorkspaceMember.objects.create(workspace=self.ws, user=self.member_user, name='Member', phone='09120000003', role='member')
        self.project = Project.objects.create(workspace=self.ws, name='P', created_by=self.owner)
        ProjectMember.objects.create(project=self.project, workspace_member=self.viewer_member, role='viewer')
        ProjectMember.objects.create(project=self.project, workspace_member=self.member, role='member')
        self.task = Task.objects.create(project=self.project, title='T', created_by=self.owner)

    def test_viewer_can_read_but_cannot_change_status(self):
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(reverse('project_detail', args=[self.project.pk])).status_code, 200)
        response = self.client.post(reverse('task_status', args=[self.task.pk]), {'status': 'done'})
        self.assertEqual(response.status_code, 403)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'todo')

    def test_viewer_cannot_delete_task(self):
        self.client.force_login(self.viewer)
        self.client.post(reverse('task_delete', args=[self.task.pk]))
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())

    def test_member_can_change_task(self):
        self.client.force_login(self.member_user)
        response = self.client.post(reverse('task_status', args=[self.task.pk]), {'status': 'doing'})
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'doing')

    def test_project_get_does_not_write_progress(self):
        self.assertIsNone(self.project.progress_updated_at)
        self.client.force_login(self.owner)
        self.client.get(reverse('project_detail', args=[self.project.pk]))
        self.project.refresh_from_db()
        self.assertIsNone(self.project.progress_updated_at)

    def test_inactive_workspace_member_loses_access(self):
        self.viewer_member.is_active = False
        self.viewer_member.save(update_fields=['is_active'])
        self.client.force_login(self.viewer)
        response = self.client.get(reverse('project_detail', args=[self.project.pk]))
        self.assertEqual(response.status_code, 302)

