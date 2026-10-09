from django import template
from dashboard.jalali import format_jalali, to_fa_digits
from django.utils import timezone

register = template.Library()

@register.filter
def jalali_date(value):
    return format_jalali(value, with_time=False)

@register.filter
def jalali_datetime(value):
    return format_jalali(value, with_time=True)

@register.filter
def fa_num(value):
    if value is None:
        return ''
    return to_fa_digits(value)

@register.filter
def fa_filesize(value):
    try:
        size = int(value)
    except (TypeError, ValueError):
        return ''
    units = ['بایت', 'کیلوبایت', 'مگابایت', 'گیگابایت']
    idx = 0
    amount = float(size)
    while amount >= 1024 and idx < len(units)-1:
        amount /= 1024
        idx += 1
    text = f'{amount:.1f}' if idx else str(int(amount))
    return f'{to_fa_digits(text)} {units[idx]}'

@register.simple_tag
def jalali_today():
    return format_jalali(timezone.localdate())

@register.filter
def work_duration(value):
    try:
        from timetracking.utils import human_duration
        if hasattr(value, 'effective_seconds'):
            value = value.effective_seconds
        return human_duration(value)
    except Exception:
        return '—'

@register.filter
def fa_time(value):
    if not value:
        return '—'
    try:
        local = timezone.localtime(value)
        return to_fa_digits(local.strftime('%H:%M'))
    except Exception:
        return str(value)
