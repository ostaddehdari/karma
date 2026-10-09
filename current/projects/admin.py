from django.contrib import admin
from .models import Project,ProjectMember,TaskList,Task,ChecklistItem,Milestone,ActivityEvent
for m in [Project,ProjectMember,TaskList,Task,ChecklistItem,Milestone,ActivityEvent]: admin.site.register(m)
