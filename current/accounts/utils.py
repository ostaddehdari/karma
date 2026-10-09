import re

DEFAULT_USER_PASSWORD = '123456'

_PERSIAN_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')


def normalize_mobile(value):
    """Normalize Iranian mobile numbers to 09xxxxxxxxx when possible.

    Accepts Persian/Arabic digits and common +98 / 0098 / 98 formats.
    Returns an empty string for empty values. Non-Iranian-looking digit strings
    are returned stripped so the caller can still keep the original identity.
    """
    if value is None:
        return ''
    raw = str(value).translate(_PERSIAN_DIGITS).strip()
    digits = re.sub(r'\D+', '', raw)
    if not digits:
        return ''
    if digits.startswith('0098'):
        digits = digits[4:]
        if digits.startswith('0'):
            digits = digits[1:]
        digits = '0' + digits
    elif digits.startswith('98') and len(digits) >= 12:
        digits = digits[2:]
        if digits.startswith('0'):
            digits = digits[1:]
        digits = '0' + digits
    elif len(digits) == 10 and digits.startswith('9'):
        digits = '0' + digits
    return digits


def mobile_from_user(user):
    try:
        profile = user.profile
    except Exception:
        profile = None
    candidates = [getattr(profile, 'phone', ''), getattr(user, 'username', '')]
    for item in candidates:
        normalized = normalize_mobile(item)
        if normalized:
            return normalized
    return ''
