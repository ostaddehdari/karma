from django.core.management.base import BaseCommand
from accounts.services import duplicate_mobile_groups, merge_all_duplicate_users
from accounts.utils import DEFAULT_USER_PASSWORD


class Command(BaseCommand):
    help = 'ادغام حساب‌های تکراری بر اساس موبایل نرمال‌شده و در صورت درخواست تنظیم رمز پیش‌فرض.'

    def add_arguments(self, parser):
        parser.add_argument('--reset-all-passwords', action='store_true', help='رمز همه کاربران باقی‌مانده را بازنشانی می‌کند.')
        parser.add_argument('--password', default=DEFAULT_USER_PASSWORD, help='رمز مورد استفاده برای بازنشانی.')
        parser.add_argument('--dry-run', action='store_true', help='فقط گروه‌های تکراری را نمایش می‌دهد.')

    def handle(self, *args, **options):
        groups = duplicate_mobile_groups()
        if options['dry_run']:
            if not groups:
                self.stdout.write(self.style.SUCCESS('کاربر تکراری بر اساس موبایل پیدا نشد.'))
                return
            for mobile, users in groups.items():
                self.stdout.write(f"{mobile}: " + ', '.join(f'#{u.pk} {u.username}' for u in users))
            self.stdout.write(f'تعداد گروه‌های تکراری: {len(groups)}')
            return

        result = merge_all_duplicate_users(
            reset_passwords=options['reset_all_passwords'],
            password=options['password'],
        )
        self.stdout.write(self.style.SUCCESS(
            f"ادغام انجام شد: {result['groups']} گروه، {result['merged_users']} حساب حذف/ادغام، "
            f"{result['remaining_users']} کاربر باقی ماند."
        ))
        if options['reset_all_passwords']:
            self.stdout.write(self.style.WARNING('رمز همه کاربران روی مقدار درخواستی تنظیم شد.'))
