from django.conf import settings
from django.db import models
from django.utils import timezone

from projects.models import Project, Task
from workspaces.models import WorkspaceMember


class WorkLog(models.Model):
    MANUAL = 'manual'
    TIMER = 'timer'
    ENTRY_TYPES = [(MANUAL, 'ثبت دستی'), (TIMER, 'تایمر')]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='work_logs')
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name='work_logs')
    member = models.ForeignKey(WorkspaceMember, on_delete=models.PROTECT, related_name='work_logs')
    entry_type = models.CharField(max_length=12, choices=ENTRY_TYPES, default=MANUAL)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    note = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_work_logs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-started_at', '-id']
        indexes = [
            models.Index(fields=['project', 'started_at'], name='worklog_proj_started_idx'),
            models.Index(fields=['member', 'started_at'], name='worklog_member_started_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['member'], condition=models.Q(ended_at__isnull=True),
                name='one_active_timer_per_member',
            ),
            models.CheckConstraint(
                condition=models.Q(ended_at__isnull=True) | models.Q(ended_at__gte=models.F('started_at')),
                name='worklog_end_after_start',
            ),
        ]

    @property
    def is_running(self):
        return self.ended_at is None

    @property
    def effective_seconds(self):
        if self.ended_at:
            return max(0, int((self.ended_at - self.started_at).total_seconds()))
        return max(0, int((timezone.now() - self.started_at).total_seconds()))

    @property
    def effective_minutes(self):
        return round(self.effective_seconds / 60)

    def stop(self, ended_at=None):
        if self.ended_at:
            return self
        ended_at = ended_at or timezone.now()
        if ended_at < self.started_at:
            ended_at = self.started_at
        self.ended_at = ended_at
        self.duration_seconds = max(0, int((ended_at - self.started_at).total_seconds()))
        self.save(update_fields=['ended_at', 'duration_seconds', 'updated_at'])
        return self

    def __str__(self):
        return f'{self.member.name} - {self.project.name}'
