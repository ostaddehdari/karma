from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import Profile
from workspaces.models import Workspace,WorkspaceMember
from projects.models import Project,ProjectMember,TaskList,Task,Milestone,ActivityEvent
from communication.models import Conversation,Message,Letter,Note,Notification
class Command(BaseCommand):
    help='Create demo data for KARMA'
    def handle(self,*args,**opts):
        u,created=User.objects.get_or_create(username='09170000000',defaults={'first_name':'مدیر کارما','is_staff':True,'is_superuser':True})
        if created: u.set_password('123456'); u.save()
        u.profile.display_name='مدیر کارما'; u.profile.phone='09170000000'; u.profile.save()
        ws,_=Workspace.objects.get_or_create(name='میزکار نمونه کارما',owner=u,defaults={'description':'میزکار نمایشی برای شروع سریع','color':'#6357E6'})
        wm,_=WorkspaceMember.objects.get_or_create(workspace=ws,phone='09170000000',defaults={'user':u,'name':'مدیر کارما','role':'owner'})
        p,_=Project.objects.get_or_create(workspace=ws,name='راه‌اندازی نسخه اول کارما',defaults={'code':'KARMA-001','description':'پروژه نمونه برای مشاهده امکانات اصلی','priority':1,'status':'active','manager':wm,'created_by':u,'progress_cache':35})
        ProjectMember.objects.get_or_create(project=p,workspace_member=wm,defaults={'role':'manager'})
        tl,_=TaskList.objects.get_or_create(project=p,title='کارهای اصلی',defaults={'position':1})
        if not p.tasks.exists():
            Task.objects.create(project=p,task_list=tl,title='طراحی داشبورد',assignee=wm,status='done',priority=2,progress=100,created_by=u)
            Task.objects.create(project=p,task_list=tl,title='تکمیل چت مستندات',assignee=wm,status='doing',priority=1,progress=60,created_by=u)
            Task.objects.create(project=p,task_list=tl,title='تست دسترسی اعضا',assignee=wm,status='todo',priority=3,progress=0,created_by=u)
        Milestone.objects.get_or_create(project=p,title='نسخه MVP',defaults={'position':1})
        c=Conversation.objects.filter(project=p,kind='follow_up').first()
        if c and not c.messages.exists(): Message.objects.create(conversation=c,sender=u,text='به پروژه نمونه کارما خوش آمدید. این کانال برای پیگیری کارهاست.')
        Letter.objects.get_or_create(project=p,subject='شروع رسمی پروژه',defaults={'kind':'internal','body':'شروع رسمی پروژه نسخه اول کارما','sender_name':'مدیریت','recipient_name':'تیم پروژه','created_by':u,'number':'KARMA-001-00001'})
        Note.objects.get_or_create(user=u,title='کارهای اولیه',defaults={'body':'اعضای میزکار را اضافه کن\nپروژه‌ها را اولویت‌بندی کن','project':p,'is_pinned':True})
        Notification.objects.get_or_create(user=u,title='خوش آمدید',defaults={'body':'نسخه نمایشی کارما آماده است.','url':'/dashboard/'})
        ActivityEvent.objects.get_or_create(project=p,actor=u,verb='seed',description='پروژه نمونه آماده شد.')
        p.refresh_progress()
        self.stdout.write(self.style.SUCCESS('Demo ready: login 09170000000 / 123456'))
