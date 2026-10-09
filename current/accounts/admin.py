from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User

from .models import Profile
from .services import merge_all_duplicate_users
from .utils import DEFAULT_USER_PASSWORD


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0
    fields = ('display_name', 'phone', 'phone_normalized', 'avatar')
    readonly_fields = ('phone_normalized',)


@admin.action(description='تنظیم رمز کاربران انتخاب‌شده روی 123456')
def reset_selected_passwords(modeladmin, request, queryset):
    count = 0
    for user in queryset:
        user.set_password(DEFAULT_USER_PASSWORD)
        user.save(update_fields=['password'])
        count += 1
    modeladmin.message_user(request, f'رمز {count} کاربر بازنشانی شد.', messages.WARNING)


@admin.action(description='ادغام همه کاربران تکراری بر اساس موبایل')
def merge_duplicates_action(modeladmin, request, queryset):
    result = merge_all_duplicate_users(reset_passwords=False)
    modeladmin.message_user(
        request,
        f"{result['merged_users']} حساب تکراری در {result['groups']} گروه ادغام شد.",
        messages.SUCCESS,
    )


class KarmaUserAdmin(DjangoUserAdmin):
    inlines = [ProfileInline]
    actions = [reset_selected_passwords, merge_duplicates_action]
    list_display = ('id', 'username', 'display_name', 'normalized_phone', 'is_active', 'is_staff', 'is_superuser', 'last_login')
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    search_fields = ('username', 'first_name', 'last_name', 'profile__display_name', 'profile__phone', 'profile__phone_normalized')

    @admin.display(description='نام')
    def display_name(self, obj):
        return getattr(getattr(obj, 'profile', None), 'display_name', '') or obj.get_full_name()

    @admin.display(description='موبایل واحد')
    def normalized_phone(self, obj):
        return getattr(getattr(obj, 'profile', None), 'phone_normalized', '')


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, KarmaUserAdmin)
admin.site.register(Profile)
