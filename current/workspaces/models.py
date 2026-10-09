from django.db import models
from django.contrib.auth.models import User
class Workspace(models.Model):
    name=models.CharField(max_length=140)
    owner=models.ForeignKey(User,on_delete=models.CASCADE,related_name='owned_workspaces')
    description=models.TextField(blank=True)
    logo=models.ImageField(upload_to='workspace_logos/%Y/%m/',blank=True,null=True)
    color=models.CharField(max_length=12,default='#5B5BD6')
    created_at=models.DateTimeField(auto_now_add=True)
    is_archived=models.BooleanField(default=False)
    def __str__(self): return self.name
class WorkspaceMember(models.Model):
    OWNER='owner'; ADMIN='admin'; MEMBER='member'; VIEWER='viewer'
    ROLE_CHOICES=[(OWNER,'مالک'),(ADMIN,'مدیر'),(MEMBER,'عضو'),(VIEWER,'مشاهده‌گر')]
    workspace=models.ForeignKey(Workspace,on_delete=models.CASCADE,related_name='members')
    user=models.ForeignKey(User,on_delete=models.SET_NULL,related_name='workspace_memberships',null=True,blank=True)
    name=models.CharField(max_length=120)
    phone=models.CharField(max_length=20)
    role=models.CharField(max_length=16,choices=ROLE_CHOICES,default=MEMBER)
    is_active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: unique_together=[('workspace','phone')]
    def __str__(self): return f'{self.name} - {self.workspace}'
