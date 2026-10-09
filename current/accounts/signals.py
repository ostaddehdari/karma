from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile
from .utils import normalize_mobile


@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        from communication.models import Notebook, NoteSection
        notebook = Notebook.objects.create(user=instance, title='دفترچه من', color='#6759E7')
        NoteSection.objects.create(notebook=notebook, title='یادداشت‌ها', position=1)


@receiver(post_save, sender=Profile)
def link_pending_members(sender, instance, **kwargs):
    mobile = normalize_mobile(instance.phone)
    if not mobile:
        return
    from workspaces.models import WorkspaceMember
    # Existing data can contain +98/0098/Persian-digit variants, so compare
    # normalized values rather than only exact strings.
    for member in WorkspaceMember.objects.filter(user__isnull=True):
        if normalize_mobile(member.phone) == mobile:
            member.user = instance.user
            member.phone = mobile
            member.save(update_fields=['user', 'phone'])
