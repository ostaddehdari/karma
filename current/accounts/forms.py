from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Profile
from .utils import DEFAULT_USER_PASSWORD, normalize_mobile


def _mobile_label_clean(value):
    normalized = normalize_mobile(value)
    if not normalized:
        raise ValidationError('شماره موبایل معتبر وارد کنید.')
    if normalized.startswith('09') and len(normalized) != 11:
        raise ValidationError('شماره موبایل ایران باید ۱۱ رقم و با ۰۹ شروع شود.')
    return normalized


class RegisterForm(forms.Form):
    name = forms.CharField(label='نام و نام خانوادگی', max_length=120)
    phone = forms.CharField(label='شماره موبایل', max_length=20)
    password = forms.CharField(
        label='رمز عبور', widget=forms.PasswordInput, required=False,
        help_text=f'اگر خالی باشد رمز پیش‌فرض {DEFAULT_USER_PASSWORD} تنظیم می‌شود.'
    )

    def clean_phone(self):
        p = _mobile_label_clean(self.cleaned_data['phone'])
        if User.objects.filter(username=p).exists() or Profile.objects.filter(phone_normalized=p).exists():
            raise forms.ValidationError('این شماره قبلاً ثبت شده است.')
        return p

    def save(self):
        password = self.cleaned_data.get('password') or DEFAULT_USER_PASSWORD
        u = User.objects.create_user(username=self.cleaned_data['phone'], password=password)
        u.first_name = self.cleaned_data['name']
        u.save(update_fields=['first_name'])
        u.profile.display_name = self.cleaned_data['name']
        u.profile.phone = self.cleaned_data['phone']
        u.profile.save()
        return u


class AdminUserCreateForm(forms.Form):
    name = forms.CharField(label='نام و نام خانوادگی', max_length=120)
    phone = forms.CharField(label='شماره موبایل', max_length=20)
    password = forms.CharField(
        label='رمز اولیه', required=False, initial=DEFAULT_USER_PASSWORD,
        widget=forms.TextInput(attrs={'autocomplete': 'new-password'}),
        help_text=f'رمز پیش‌فرض: {DEFAULT_USER_PASSWORD}'
    )
    is_active = forms.BooleanField(label='کاربر فعال باشد', required=False, initial=True)
    is_staff = forms.BooleanField(label='دسترسی مدیریت داشته باشد', required=False)

    def clean_phone(self):
        p = _mobile_label_clean(self.cleaned_data['phone'])
        if Profile.objects.filter(phone_normalized=p).exists() or User.objects.filter(username=p).exists():
            raise forms.ValidationError('کاربری با این شماره موبایل وجود دارد.')
        return p

    def save(self):
        name = self.cleaned_data['name'].strip()
        phone = self.cleaned_data['phone']
        password = self.cleaned_data.get('password') or DEFAULT_USER_PASSWORD
        user = User.objects.create_user(username=phone, password=password)
        user.first_name = name
        user.is_active = self.cleaned_data.get('is_active', True)
        user.is_staff = self.cleaned_data.get('is_staff', False)
        user.save()
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.display_name = name
        profile.phone = phone
        profile.save()
        return user


class AdminUserEditForm(forms.Form):
    name = forms.CharField(label='نام و نام خانوادگی', max_length=120)
    phone = forms.CharField(label='شماره موبایل', max_length=20)
    new_password = forms.CharField(
        label='رمز جدید', required=False,
        widget=forms.TextInput(attrs={'autocomplete': 'new-password'}),
        help_text=f'برای عدم تغییر خالی بگذارید. رمز پیش‌فرض پیشنهادی {DEFAULT_USER_PASSWORD} است.'
    )
    is_active = forms.BooleanField(label='فعال', required=False)
    is_staff = forms.BooleanField(label='مدیر سیستم', required=False)

    def __init__(self, *args, user_obj=None, **kwargs):
        self.user_obj = user_obj
        initial = kwargs.setdefault('initial', {})
        if user_obj:
            profile = getattr(user_obj, 'profile', None)
            initial.setdefault('name', getattr(profile, 'display_name', '') or user_obj.first_name)
            initial.setdefault('phone', getattr(profile, 'phone', '') or user_obj.username)
            initial.setdefault('is_active', user_obj.is_active)
            initial.setdefault('is_staff', user_obj.is_staff)
        super().__init__(*args, **kwargs)

    def clean_phone(self):
        p = _mobile_label_clean(self.cleaned_data['phone'])
        qs = Profile.objects.filter(phone_normalized=p)
        if self.user_obj:
            qs = qs.exclude(user=self.user_obj)
        if qs.exists():
            raise forms.ValidationError('این شماره موبایل متعلق به کاربر دیگری است.')
        uq = User.objects.filter(username=p)
        if self.user_obj:
            uq = uq.exclude(pk=self.user_obj.pk)
        if uq.exists():
            raise forms.ValidationError('این شناسه موبایل متعلق به کاربر دیگری است.')
        return p

    def save(self):
        user = self.user_obj
        name = self.cleaned_data['name'].strip()
        phone = self.cleaned_data['phone']
        user.username = phone
        user.first_name = name
        user.is_active = self.cleaned_data.get('is_active', False)
        user.is_staff = self.cleaned_data.get('is_staff', False) or user.is_superuser
        password = self.cleaned_data.get('new_password')
        if password:
            user.set_password(password)
        user.save()
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.display_name = name
        profile.phone = phone
        profile.save()
        return user
