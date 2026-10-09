from django.db import models
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone
from workspaces.models import Workspace, WorkspaceMember


class Project(models.Model):
    URGENT = 1; VERY_HIGH = 2; HIGH = 3; NORMAL = 4; LOW = 5
    PRIORITIES = [(URGENT, 'فوری'), (VERY_HIGH, 'خیلی بالا'), (HIGH, 'بالا'), (NORMAL, 'عادی'), (LOW, 'پایین')]
    STATUS = [('planning', 'برنامه‌ریزی'), ('active', 'در حال اجرا'), ('waiting', 'در انتظار'), ('paused', 'متوقف'), ('done', 'تکمیل‌شده'), ('cancelled', 'لغوشده')]

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=180)
    code = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    priority = models.PositiveSmallIntegerField(choices=PRIORITIES, default=NORMAL)
    manual_order = models.PositiveIntegerField(default=1000)
    status = models.CharField(max_length=16, choices=STATUS, default='planning')
    manager = models.ForeignKey(WorkspaceMember, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_projects')
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    progress_cache = models.PositiveSmallIntegerField(default=0)
    progress_updated_at = models.DateTimeField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_projects')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def priority_order(self):
        return self.priority

    def refresh_progress(self):
        """
        پیشرفت واقعی پروژه = میانگین پیشرفت مؤثر همه وظایف.

        پیشرفت مؤثر هر وظیفه:
        - وضعیت «انجام‌شده» => ۱۰۰٪
        - اگر چک‌لیست دارد => نسبت آیتم‌های تیک‌خورده
        - در غیر این صورت => درصد دستی همان وظیفه

        این روش باعث می‌شود هم تیک‌زدن چک‌لیست و هم دکمه «تکمیل شد»
        بلافاصله روی پیشرفت پروژه اثر بگذارند.
        """
        rows = list(
            self.tasks.annotate(
                _checklist_total=Count('checklist'),
                _checklist_done=Count('checklist', filter=Q(checklist__is_done=True)),
            ).values('status', 'progress', '_checklist_total', '_checklist_done')
        )

        if self.status == 'done':
            value = 100
        elif not rows:
            value = 0
        else:
            values = []
            for row in rows:
                if row['status'] == 'done':
                    effective = 100
                elif row['_checklist_total']:
                    effective = round(row['_checklist_done'] * 100 / row['_checklist_total'])
                else:
                    effective = max(0, min(100, row['progress'] or 0))
                values.append(effective)
            value = round(sum(values) / len(values))

        self.progress_cache = value
        self.progress_updated_at = timezone.now()
        self.save(update_fields=['progress_cache', 'progress_updated_at'])
        return value

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=['workspace', 'is_archived', 'status'], name='project_ws_archive_status_idx'),
            models.Index(fields=['workspace', 'priority', 'manual_order'], name='project_ws_priority_order_idx'),
        ]


class ProjectMember(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='members')
    workspace_member = models.ForeignKey(WorkspaceMember, on_delete=models.CASCADE, related_name='project_accesses')
    role = models.CharField(max_length=20, choices=[('manager', 'مدیر پروژه'), ('member', 'عضو'), ('viewer', 'مشاهده‌گر')], default='member')
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [('project', 'workspace_member')]


class TaskList(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='task_lists')
    title = models.CharField(max_length=150)
    position = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title


class Task(models.Model):
    STATUS = [('todo', 'برای انجام'), ('doing', 'در حال انجام'), ('review', 'بازبینی'), ('done', 'انجام‌شده'), ('blocked', 'مسدود')]
    PRIORITY = [(1, 'فوری'), (2, 'بالا'), (3, 'عادی'), (4, 'پایین')]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    task_list = models.ForeignKey(TaskList, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    title = models.CharField(max_length=220)
    description = models.TextField(blank=True)
    assignee = models.ForeignKey(WorkspaceMember, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    status = models.CharField(max_length=16, choices=STATUS, default='todo')
    priority = models.PositiveSmallIntegerField(choices=PRIORITY, default=3)
    due_date = models.DateField(null=True, blank=True)
    progress = models.PositiveSmallIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_tasks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def _checklist_values(self):
        items = list(self.checklist.all())
        total = len(items)
        done = sum(1 for item in items if item.is_done)
        return total, done

    @property
    def checklist_progress(self):
        total, done = self._checklist_values()
        if not total:
            return None
        return round(done * 100 / total)

    @property
    def effective_progress(self):
        if self.status == 'done':
            return 100
        checklist_progress = self.checklist_progress
        if checklist_progress is not None:
            return checklist_progress
        return max(0, min(100, self.progress or 0))

    @property
    def checklist_done_count(self):
        return self._checklist_values()[1]

    @property
    def checklist_total_count(self):
        return self._checklist_values()[0]

    def sync_progress_from_checklist(self, save=True):
        """اگر چک‌لیست وجود دارد، درصد وظیفه را از آن محاسبه کن."""
        if self.status == 'done':
            value = 100
        else:
            checklist_progress = self.checklist_progress
            value = checklist_progress if checklist_progress is not None else max(0, min(100, self.progress or 0))
        changed = self.progress != value
        self.progress = value
        if self.status != 'done' and self.completed_at is not None:
            self.completed_at = None
            changed = True
        if save and changed:
            self.save(update_fields=['progress', 'completed_at', 'updated_at'])
        return value

    def mark_done(self):
        """تکمیل صریح وظیفه؛ چک‌لیست نیز کامل می‌شود تا داده‌ها متناقض نباشند."""
        self.checklist.filter(is_done=False).update(is_done=True)
        self.status = 'done'
        self.progress = 100
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'progress', 'completed_at', 'updated_at'])

    def reopen(self, status='doing'):
        self.status = status if status in {'todo', 'doing', 'review', 'blocked'} else 'doing'
        self.completed_at = None
        if not self.checklist.exists() and self.progress == 100:
            self.progress = 0
        self.save(update_fields=['status', 'progress', 'completed_at', 'updated_at'])
        self.sync_progress_from_checklist()

    def __str__(self):
        return self.title

    class Meta:
        indexes = [
            models.Index(fields=['project', 'status', 'due_date'], name='task_project_status_due_idx'),
            models.Index(fields=['project', 'task_list', 'priority'], name='task_project_list_priority_idx'),
            models.Index(fields=['assignee', 'status'], name='task_assignee_status_idx'),
        ]
        constraints = [models.CheckConstraint(condition=models.Q(progress__gte=0, progress__lte=100), name='task_progress_0_100')]


class ChecklistItem(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='checklist')
    title = models.CharField(max_length=220)
    is_done = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)


class Milestone(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=180)
    due_date = models.DateField(null=True, blank=True)
    is_done = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)


class ActivityEvent(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='activities')
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    verb = models.CharField(max_length=100)
    description = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['project', '-created_at'], name='activity_project_created_idx')]
