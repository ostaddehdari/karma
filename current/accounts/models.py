from django.db import models
from django.contrib.auth.models import User
from .utils import normalize_mobile


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    phone_normalized = models.CharField(max_length=20, unique=True, null=True, blank=True, db_index=True)
    avatar = models.ImageField(upload_to='avatars/%Y/%m/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        normalized = normalize_mobile(self.phone)
        if not normalized:
            candidate = normalize_mobile(self.user.username)
            normalized = candidate if len(candidate) == 11 and candidate.startswith('09') else ''
        self.phone_normalized = normalized or None
        if normalized:
            self.phone = normalized
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name or self.user.get_full_name() or self.user.username
