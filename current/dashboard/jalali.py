from datetime import date, datetime

FA_DIGITS = '۰۱۲۳۴۵۶۷۸۹'
EN_DIGITS = '0123456789'


def to_fa_digits(value):
    text = str(value)
    return text.translate(str.maketrans(EN_DIGITS, FA_DIGITS))


def to_en_digits(value):
    text = str(value)
    return text.translate(str.maketrans(FA_DIGITS + '٠١٢٣٤٥٦٧٨٩', EN_DIGITS + EN_DIGITS))


def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy + 1 if gm > 2 else gy
    days = 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 - 80 + gd + g_d_m[gm - 1]
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


def jalali_to_gregorian(jy, jm, jd):
    if jy > 979:
        gy = 1600
        jy -= 979
    else:
        gy = 621
    days = 365 * jy + (jy // 33) * 8 + ((jy % 33) + 3) // 4 + 78 + jd
    if jm < 7:
        days += (jm - 1) * 31
    else:
        days += (jm - 7) * 30 + 186
    gy += 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        gy += 100 * ((days - 1) // 36524)
        days = (days - 1) % 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    leap = gy % 4 == 0 and (gy % 100 != 0 or gy % 400 == 0)
    month_days = [0, 31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 1
    while gm <= 12 and gd > month_days[gm]:
        gd -= month_days[gm]
        gm += 1
    return gy, gm, gd


def format_jalali(value, with_time=False, fa_digits=True):
    if not value:
        return '—'
    if isinstance(value, datetime):
        d = value.date()
        time_part = f' {value:%H:%M}' if with_time else ''
    elif isinstance(value, date):
        d = value
        time_part = ''
    else:
        return str(value)
    jy, jm, jd = gregorian_to_jalali(d.year, d.month, d.day)
    out = f'{jy:04d}/{jm:02d}/{jd:02d}{time_part}'
    return to_fa_digits(out) if fa_digits else out


def parse_jalali_date(value):
    if isinstance(value, date):
        return value
    raw = to_en_digits(value or '').strip().replace('-', '/').replace('.', '/')
    if not raw:
        return None
    parts = raw.split('/')
    if len(parts) != 3:
        raise ValueError('فرمت تاریخ باید مانند ۱۴۰۵/۰۵/۲۰ باشد.')
    y, m, d = map(int, parts)
    # Values in modern Jalali range are treated as Jalali; Gregorian remains accepted.
    if y < 1700:
        gy, gm, gd = jalali_to_gregorian(y, m, d)
        return date(gy, gm, gd)
    return date(y, m, d)
