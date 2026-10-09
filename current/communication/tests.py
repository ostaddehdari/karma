from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from projects.models import Project, ProjectMember
from workspaces.models import Workspace, WorkspaceMember
from .models import Conversation, Message, MessageAttachment


class PrivateFileSecurityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner2', password='x')
        self.viewer = User.objects.create_user('viewer2', password='x')
        self.outsider = User.objects.create_user('outsider', password='x')
        self.ws = Workspace.objects.create(name='W', owner=self.owner)
        owner_member = WorkspaceMember.objects.create(workspace=self.ws, user=self.owner, name='O', phone='09121000001', role='owner')
        viewer_member = WorkspaceMember.objects.create(workspace=self.ws, user=self.viewer, name='V', phone='09121000002', role='member')
        self.project = Project.objects.create(workspace=self.ws, name='P', created_by=self.owner)
        ProjectMember.objects.create(project=self.project, workspace_member=owner_member, role='manager')
        ProjectMember.objects.create(project=self.project, workspace_member=viewer_member, role='viewer')
        self.conversation = Conversation.objects.create(project=self.project, kind='follow_up', title='Chat', created_by=self.owner)
        message = Message.objects.create(conversation=self.conversation, sender=self.owner, text='x')
        self.attachment = MessageAttachment.objects.create(
            message=message, original_name='a.pdf', media_type='document',
            file=SimpleUploadedFile('a.pdf', b'%PDF-1.4 safe'),
        )

    def test_authorized_user_can_download_private_file(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse('message_attachment_download', args=[self.attachment.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'private, no-store')

    def test_outsider_gets_404_for_private_file(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse('message_attachment_download', args=[self.attachment.pk]))
        self.assertEqual(response.status_code, 404)

    def test_viewer_cannot_post_message(self):
        self.client.force_login(self.viewer)
        response = self.client.post(reverse('conversation', args=[self.conversation.pk]), {'text': 'forbidden'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.conversation.messages.filter(text='forbidden').exists())

    def test_fake_pdf_is_rejected(self):
        self.client.force_login(self.owner)
        fake = SimpleUploadedFile('evil.pdf', b'<script>alert(1)</script>', content_type='application/pdf')
        self.client.post(reverse('conversation', args=[self.conversation.pk]), {'text': '', 'attachments': fake})
        self.assertFalse(self.conversation.messages.exclude(text='x').exists())
