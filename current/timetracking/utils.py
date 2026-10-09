from datetime import date, datetime, time, timedelta
from django.utils import timezone
from dashboard.jalali import jalali_to_gregorian, gregorian_to_jalali, to_en_digits, to_fa_digits

JALALI_MONTHS = [
    'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
    'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
]


def current_jalali_month():
    today = timezone.localdate()
    jy, jm, _ = gregorian_to_jalali(today.year, today.month, today.day)
    return jy, jm


def parse_jalali_month(value):
    raw = to_en_digits(value or '').strip().replace('-', '/').replace('.', '/')
    if not raw:
        return current_jalali_month()
    parts = raw.split('/')
    if len(parts) != 2:
        raise ValueError('ماه را مانند ۱۴۰۵/۰۶ وارد کنید.')
    jy, jm = map(int, parts)
    if not 1 <= jm <= 12 or jy < 1200 or jy > 1700:
        raise ValueError('ماه شمسی معتبر نیست.')
    return jy, jm


def format_jalali_month(jy, jm, fa_digits=True):
    text = f'{jy:04d}/{jm:02d}'
    return to_fa_digits(text) if fa_digits else text


def jalali_month_label(jy, jm):
    return f'{JALALI_MONTHS[jm-1]} {to_fa_digits(jy)}'


def month_range(jy, jm):
    gy, gm, gd = jalali_to_gregorian(jy, jm, 1)
    if jm == 12:
        ny, nm = jy + 1, 1
    else:
        ny, nm = jy, jm + 1
    ngy, ngm, ngd = jalali_to_gregorian(ny, nm, 1)
    start = timezone.make_aware(datetime.combine(date(gy, gm, gd), time.min), timezone.get_current_timezone())
    end = timezone.make_aware(datetime.combine(date(ngy, ngm, ngd), time.min), timezone.get_current_timezone())
    return start, end


def human_duration(seconds):
    seconds = max(0, int(seconds or 0))
    if 0 < seconds < 60:
        return 'کمتر از یک دقیقه'
    minutes = round(seconds / 60)
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f'{to_fa_digits(hours)} ساعت و {to_fa_digits(mins)} دقیقه'
    if hours:
        return f'{to_fa_digits(hours)} ساعت'
    return f'{to_fa_digits(mins)} دقیقه'


def jalali_month_days(jy, jm):
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    start, end = month_range(jy, jm)
    return (end.date() - start.date()).days
