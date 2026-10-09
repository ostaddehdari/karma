from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import RegisterForm, AdminUserCreateForm, AdminUserEditForm
from .models import Profile
from .services import duplicate_mobile_groups, merge_all_duplicate_users
from .utils import DEFAULT_USER_PASSWORD, mobile_from_user


def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'accounts/landing.html')


def register(request):
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('dashboard')
    return render(request, 'accounts/register.html', {'form': form})


def _is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


admin_required = user_passes_test(_is_admin, login_url='login')


@admin_required
def user_management(request):
    q = (request.GET.get('q') or '').strip()
    users = User.objects.select_related('profile').order_by('-is_superuser', '-is_staff', 'id')
    if q:
        users = users.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(profile__display_name__icontains=q) |
            Q(profile__phone__icontains=q) |
            Q(profile__phone_normalized__icontains=q)
        )
    paginator = Paginator(users, 50)
    page = paginator.get_page(request.GET.get('page'))
    duplicates = duplicate_mobile_groups()
    duplicate_ids = {u.pk for group in duplicates.values() for u in group}
    return render(request, 'accounts/user_management.html', {
        'page': page,
        'q': q,
        'duplicate_ids': duplicate_ids,
        'duplicate_groups_count': len(duplicates),
        'default_password': DEFAULT_USER_PASSWORD,
    })


@admin_required
def user_create_admin(request):
    form = AdminUserCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(request, f'کاربر «{user.profile.display_name}» ایجاد شد. رمز اولیه: {form.cleaned_data.get("password") or DEFAULT_USER_PASSWORD}')
        return redirect('user_management')
    return render(request, 'accounts/user_form_admin.html', {
        'form': form,
        'title': 'افزودن کاربر جدید',
        'submit_label': 'ایجاد کاربر',
        'default_password': DEFAULT_USER_PASSWORD,
    })


@admin_required
def user_edit_admin(request, user_id):
    target = get_object_or_404(User.objects.select_related('profile'), pk=user_id)
    form = AdminUserEditForm(request.POST or None, user_obj=target)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'اطلاعات کاربر با موفقیت ویرایش شد.')
        return redirect('user_management')
    return render(request, 'accounts/user_form_admin.html', {
        'form': form,
        'title': f'ویرایش کاربر #{target.pk}',
        'submit_label': 'ذخیره تغییرات',
        'target_user': target,
        'default_password': DEFAULT_USER_PASSWORD,
    })


@admin_required
@require_POST
def user_reset_password(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    target.set_password(DEFAULT_USER_PASSWORD)
    target.save(update_fields=['password'])
    messages.success(request, f'رمز کاربر #{target.pk} روی {DEFAULT_USER_PASSWORD} تنظیم شد.')
    return redirect('user_management')


@admin_required
@require_POST
def users_reset_all_passwords(request):
    count = 0
    for target in User.objects.all():
        target.set_password(DEFAULT_USER_PASSWORD)
        target.save(update_fields=['password'])
        count += 1
    messages.warning(request, f'رمز {count} کاربر روی {DEFAULT_USER_PASSWORD} تنظیم شد. توصیه می‌شود رمز مدیر اصلی را فوراً تغییر دهید.')
    return redirect('user_management')


@admin_required
@require_POST
def users_merge_duplicates(request):
    result = merge_all_duplicate_users(reset_passwords=False)
    messages.success(
        request,
        f"ادغام کاربران تکراری انجام شد: {result['groups']} گروه و {result['merged_users']} حساب تکراری ادغام شد."
    )
    return redirect('user_management')


@admin_required
@require_POST
def user_toggle_active(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target.pk == request.user.pk:
        messages.error(request, 'نمی‌توانید حساب فعلی خودتان را غیرفعال کنید.')
        return redirect('user_management')
    target.is_active = not target.is_active
    target.save(update_fields=['is_active'])
    messages.success(request, 'وضعیت حساب تغییر کرد.')
    return redirect('user_management')
