from django import forms
from django.conf import settings
from .models import (
    Message, Letter, Note, NoteChecklistItem, ProjectDocument,
    Notebook, NoteSection,
)
from .security import validate_upload


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput(attrs={
            'accept': 'image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.zip,.rar,.txt',
            'class': 'chat-file-input',
        }))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(d, initial) for d in data]
        return [single_clean(data, initial)] if data else []


class MessageForm(forms.ModelForm):
    attachments = MultipleFileField(required=False, label='پیوست‌ها')
    class Meta:
        model = Message
        fields = ['text']
        labels = {'text': 'پیام'}
        widgets = {'text': forms.Textarea(attrs={
            'rows': 1, 'placeholder': 'پیام...', 'aria-label': 'متن پیام',
            'class': 'telegram-textarea', 'autocomplete': 'off'
        })}

    def clean_attachments(self):
        files = self.cleaned_data.get('attachments', [])
        max_bytes = settings.KARMA_MAX_UPLOAD_MB * 1024 * 1024
        for f in files:
            validate_upload(f)
        if len(files) > settings.KARMA_MAX_FILES_PER_UPLOAD:
            raise forms.ValidationError('تعداد فایل‌های انتخابی بیش از حد مجاز است.')
        if sum(f.size for f in files) > settings.KARMA_MAX_TOTAL_UPLOAD_MB * 1024 * 1024:
            raise forms.ValidationError('حجم مجموع فایل‌ها بیش از حد مجاز است.')
        return files

    def clean(self):
        data = super().clean()
        if not (data.get('text') or data.get('attachments')):
            raise forms.ValidationError('متن یا حداقل یک فایل ارسال کنید.')
        return data


class LetterForm(forms.ModelForm):
    class Meta:
        model = Letter
        fields = ['kind', 'subject', 'body', 'sender_name', 'recipient_name', 'attachment']
        labels = {'kind':'نوع نامه','subject':'موضوع','body':'متن نامه','sender_name':'فرستنده','recipient_name':'گیرنده','attachment':'پیوست'}
        widgets = {'body': forms.Textarea(attrs={'rows': 7})}
    def clean_attachment(self):
        f = self.cleaned_data.get('attachment')
        return validate_upload(f) if f else f


class NotebookForm(forms.ModelForm):
    class Meta:
        model = Notebook
        fields = ['title', 'color']
        labels = {'title': 'نام دفترچه', 'color': 'رنگ دفترچه'}
        widgets = {
            'title': forms.TextInput(attrs={'class':'form-control','placeholder':'مثلاً برنامه‌ریزی شخصی'}),
            'color': forms.TextInput(attrs={'type':'color','class':'form-control form-control-color'}),
        }


class NoteSectionForm(forms.ModelForm):
    class Meta:
        model = NoteSection
        fields = ['title']
        labels = {'title':'نام بخش'}
        widgets = {'title': forms.TextInput(attrs={'class':'form-control','placeholder':'مثلاً جلسات، ایده‌ها، پیگیری‌ها'})}


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['title', 'body', 'project', 'color', 'is_pinned']
        labels = {'title':'عنوان صفحه','body':'متن یادداشت','project':'پروژه مرتبط','color':'رنگ صفحه','is_pinned':'سنجاق شود'}
        widgets = {
            'title': forms.TextInput(attrs={'class':'form-control note-title-input','placeholder':'عنوان صفحه'}),
            'body': forms.Textarea(attrs={'rows': 14, 'class':'form-control note-body-editor','placeholder':'از اینجا شروع به نوشتن کنید...'}),
            'project': forms.Select(attrs={'class':'form-select'}),
            'color': forms.TextInput(attrs={'type': 'color','class':'form-control form-control-color'}),
        }


class NoteChecklistForm(forms.ModelForm):
    class Meta:
        model = NoteChecklistItem
        fields = ['title']
        labels = {'title':'مورد جدید'}
        widgets = {'title': forms.TextInput(attrs={'class':'form-control','placeholder':'یک مورد به چک‌لیست اضافه کنید...'})}


class NoteAttachmentForm(forms.Form):
    files = MultipleFileField(required=True, label='فایل‌ها')

    def clean_files(self):
        files = self.cleaned_data.get('files', [])
        max_bytes = settings.KARMA_MAX_UPLOAD_MB * 1024 * 1024
        for f in files:
            validate_upload(f)
        if len(files) > settings.KARMA_MAX_FILES_PER_UPLOAD:
            raise forms.ValidationError('تعداد فایل‌ها بیش از حد مجاز است.')
        return files


class ProjectDocumentForm(forms.ModelForm):
    class Meta:
        model = ProjectDocument
        fields = ['title', 'text_content', 'file']
        labels = {'title':'عنوان مستند','text_content':'متن مستند','file':'فایل'}
        widgets = {'text_content': forms.Textarea(attrs={'rows': 5, 'placeholder': 'در صورت مستند متنی، متن را اینجا بنویسید...'})}

    def clean_file(self):
        f = self.cleaned_data.get('file')
        return validate_upload(f) if f else f

    def clean(self):
        data = super().clean()
        if not data.get('file') and not data.get('text_content'):
            raise forms.ValidationError('فایل یا متن مستند را وارد کنید.')
        return data
