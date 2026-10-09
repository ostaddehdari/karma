from django.db import models
from django.contrib.auth.models import User
from projects.models import Project
from .security import safe_upload_name


class Conversation(models.Model):
    TYPES=[('follow_up','پیگیری'),('documents','مستندات'),('custom','گروه'),('private','خصوصی')]
    project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='conversations')
    kind=models.CharField(max_length=20,choices=TYPES)
    title=models.CharField(max_length=160)
    token=models.CharField(max_length=64,unique=True,null=True,blank=True)
    created_by=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together=[('project','kind','title')]


class ConversationParticipant(models.Model):
    conversation=models.ForeignKey(Conversation,on_delete=models.CASCADE,related_name='participants')
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='conversation_participations')
    class Meta:
        unique_together=[('conversation','user')]


class Message(models.Model):
    conversation=models.ForeignKey(Conversation,on_delete=models.CASCADE,related_name='messages')
    sender=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True)
    text=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    edited_at=models.DateTimeField(null=True,blank=True)
    reply_to=models.ForeignKey('self',on_delete=models.SET_NULL,null=True,blank=True)
    class Meta:
        ordering=['created_at']
        indexes=[models.Index(fields=['conversation','created_at'],name='message_conv_created_idx')]


class MessageAttachment(models.Model):
    message=models.ForeignKey(Message,on_delete=models.CASCADE,related_name='attachments')
    file=models.FileField(upload_to=safe_upload_name)
    original_name=models.CharField(max_length=255,blank=True)
    media_type=models.CharField(max_length=20,choices=[('image','تصویر'),('video','ویدئو'),('audio','صوت'),('document','سند'),('other','فایل')],default='other')
    is_voice_recording=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)


class ProjectDocument(models.Model):
    project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='documents')
    title=models.CharField(max_length=255)
    file=models.FileField(upload_to=safe_upload_name,blank=True,null=True)
    text_content=models.TextField(blank=True)
    media_type=models.CharField(max_length=20,choices=[('text','متن'),('image','تصویر'),('video','ویدئو'),('audio','صوت'),('document','سند'),('other','فایل')],default='document')
    uploaded_by=models.ForeignKey(User,on_delete=models.SET_NULL,null=True)
    source_message=models.ForeignKey(Message,on_delete=models.SET_NULL,null=True,blank=True,related_name='mirrored_documents')
    created_at=models.DateTimeField(auto_now_add=True)


class Letter(models.Model):
    project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='letters')
    kind=models.CharField(max_length=16,choices=[('internal','داخلی'),('incoming','وارده'),('outgoing','صادره')],default='internal')
    number=models.CharField(max_length=64,blank=True)
    subject=models.CharField(max_length=220)
    body=models.TextField()
    sender_name=models.CharField(max_length=160,blank=True)
    recipient_name=models.CharField(max_length=160,blank=True)
    attachment=models.FileField(upload_to=safe_upload_name,blank=True,null=True)
    created_by=models.ForeignKey(User,on_delete=models.PROTECT,related_name='created_letters')
    created_at=models.DateTimeField(auto_now_add=True)


class Notebook(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='notebooks')
    title=models.CharField(max_length=160)
    color=models.CharField(max_length=12,default='#6759E7')
    icon=models.CharField(max_length=40,default='fa-book')
    position=models.PositiveIntegerField(default=0)
    is_archived=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=['position','created_at']
    def __str__(self):
        return self.title


class NoteSection(models.Model):
    notebook=models.ForeignKey(Notebook,on_delete=models.CASCADE,related_name='sections')
    title=models.CharField(max_length=160)
    position=models.PositiveIntegerField(default=0)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['position','created_at']
    def __str__(self):
        return self.title


class Note(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='notes')
    notebook=models.ForeignKey(Notebook,on_delete=models.SET_NULL,null=True,blank=True,related_name='notes')
    section=models.ForeignKey(NoteSection,on_delete=models.SET_NULL,null=True,blank=True,related_name='notes')
    project=models.ForeignKey(Project,on_delete=models.SET_NULL,null=True,blank=True,related_name='private_notes')
    title=models.CharField(max_length=180)
    body=models.TextField(blank=True)
    color=models.CharField(max_length=12,default='#FFFFFF')
    is_pinned=models.BooleanField(default=False)
    is_archived=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)


class NoteAttachment(models.Model):
    note=models.ForeignKey(Note,on_delete=models.CASCADE,related_name='attachments')
    file=models.FileField(upload_to=safe_upload_name)
    original_name=models.CharField(max_length=255,blank=True)
    media_type=models.CharField(max_length=20,choices=[('image','تصویر'),('video','ویدئو'),('audio','صوت'),('document','سند'),('other','فایل')],default='other')
    caption=models.CharField(max_length=255,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)


class NoteChecklistItem(models.Model):
    note=models.ForeignKey(Note,on_delete=models.CASCADE,related_name='checklist')
    title=models.CharField(max_length=220)
    is_done=models.BooleanField(default=False)
    position=models.PositiveIntegerField(default=0)


class Notification(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='notifications')
    title=models.CharField(max_length=180)
    body=models.CharField(max_length=500,blank=True)
    url=models.CharField(max_length=500,blank=True)
    is_read=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['-created_at']
        indexes=[models.Index(fields=['user','is_read','-created_at'],name='notif_user_read_created_idx')]
