from django.core.management.base import BaseCommand
from django.utils import timezone
from projects.models import Project


class Command(BaseCommand):
    help = 'بازمحاسبه پیشرفت وظایف و پروژه‌ها بر اساس چک‌لیست‌ها و وضعیت تکمیل'

    def handle(self, *args, **options):
        projects = Project.objects.prefetch_related('tasks__checklist').all()
        task_count = 0
        project_count = 0
        for project in projects:
            for task in project.tasks.all():
                if task.status == 'done':
                    if task.completed_at is None:
                        task.completed_at = task.updated_at or timezone.now()
                    task.progress = 100
                    task.save(update_fields=['progress', 'completed_at'])
                else:
                    task.sync_progress_from_checklist()
                task_count += 1
            project.refresh_progress()
            project_count += 1
        self.stdout.write(self.style.SUCCESS(
            f'پیشرفت {task_count} وظیفه و {project_count} پروژه بازمحاسبه شد.'
        ))
