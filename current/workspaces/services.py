from accounts.models import Profile
from accounts.utils import normalize_mobile
from .models import WorkspaceMember


def attach_existing_user(member):
    mobile = normalize_mobile(member.phone)
    if not mobile:
        return member
    profile = Profile.objects.select_related('user').filter(phone_normalized=mobile).first()
    if not profile:
        # Compatibility during/after data upgrade.
        profile = next((p for p in Profile.objects.select_related('user').all() if normalize_mobile(p.phone) == mobile), None)
    if not profile:
        return member
    changed = []
    if member.user_id != profile.user_id:
        member.user = profile.user
        changed.append('user')
    if member.phone != mobile:
        member.phone = mobile
        changed.append('phone')
    if changed:
        member.save(update_fields=changed)
    return member
