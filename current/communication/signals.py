from django.db.models.signals import post_save
from django.dispatch import receiver
from projects.models import Project
from .models import Conversation, Message, MessageAttachment, ProjectDocument, Notification


@receiver(post_save, sender=Project)
def create_default_conversations(sender, instance, created, **kwargs):
    if created:
        Conversation.objects.get_or_create(
            project=instance,
            kind='follow_up',
            title='پیگیری',
            defaults={'created_by': instance.created_by},
        )
        Conversation.objects.get_or_create(
            project=instance,
            kind='documents',
            title='مستندات',
            defaults={'created_by': instance.created_by},
        )


@receiver(post_save, sender=MessageAttachment)
def mirror_document_chat(sender, instance, created, **kwargs):
    if created and instance.message.conversation.kind == 'documents':
        ProjectDocument.objects.get_or_create(
            project=instance.message.conversation.project,
            source_message=instance.message,
            file=instance.file,
            defaults={
                'title': instance.original_name or instance.file.name.split('/')[-1],
                'media_type': instance.media_type,
                'uploaded_by': instance.message.sender,
            },
        )


@receiver(post_save, sender=Message)
def notify_chat_message(sender, instance, created, **kwargs):
    if not created or not instance.sender_id:
        return
    conversation = instance.conversation
    url = f'/communication/chats/{conversation.pk}/'
    if conversation.kind == 'private':
        user_ids = conversation.participants.exclude(user_id=instance.sender_id).values_list('user_id', flat=True)
    else:
        user_ids = conversation.project.members.filter(
            is_active=True,
            workspace_member__user__isnull=False,
        ).exclude(workspace_member__user_id=instance.sender_id).values_list('workspace_member__user_id', flat=True)
    existing = set()
    for user_id in user_ids:
        if user_id in existing:
            continue
        existing.add(user_id)
        Notification.objects.create(
            user_id=user_id,
            title=f'پیام جدید · {conversation.project.name}',
            body=f'پیام جدید در «{conversation.title}»',
            url=url,
        )
