import mimetypes
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.webm', '.mp3', '.wav', '.ogg', '.m4a', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt', '.zip'}
MAGIC = {
    '.jpg': (b'\xff\xd8\xff',), '.jpeg': (b'\xff\xd8\xff',), '.png': (b'\x89PNG\r\n\x1a\n',),
    '.gif': (b'GIF87a', b'GIF89a'), '.pdf': (b'%PDF-',), '.zip': (b'PK\x03\x04', b'PK\x05\x06'),
}


def validate_upload(upload):
    ext = Path(upload.name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError('نوع این فایل مجاز نیست.')
    if upload.size > settings.KARMA_MAX_UPLOAD_MB * 1024 * 1024:
        raise ValidationError(f'حداکثر حجم هر فایل {settings.KARMA_MAX_UPLOAD_MB} مگابایت است.')
    header = upload.read(16)
    upload.seek(0)
    if ext in MAGIC and not any(header.startswith(signature) for signature in MAGIC[ext]):
        raise ValidationError('محتوای فایل با پسوند آن مطابقت ندارد.')
    if ext in {'.jpg', '.jpeg', '.png', '.gif', '.webp'}:
        try:
            image = Image.open(upload)
            image.verify()
        except (UnidentifiedImageError, OSError, ValueError):
            raise ValidationError('فایل تصویر معتبر نیست.')
        finally:
            upload.seek(0)
    return upload


def safe_upload_name(instance, filename):
    ext = Path(filename).suffix.lower()
    return f'private/{instance.__class__.__name__.lower()}/{uuid4().hex}{ext}'
