from django.contrib import admin
from .models import WorkLog


@admin.register(WorkLog)
class WorkLogAdmin(admin.ModelAdmin):
    list_display = ('member', 'project', 'task', 'entry_type', 'started_at', 'ended_at', 'duration_seconds')
    list_filter = ('entry_type', 'project')
    search_fields = ('member__name', 'project__name', 'task__title', 'note')
