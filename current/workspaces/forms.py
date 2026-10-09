from django import forms
from .models import Workspace, WorkspaceMember
from projects.models import Project
from accounts.utils import normalize_mobile
from communication.security import validate_upload


class WorkspaceForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = ['name', 'description', 'logo', 'color']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'color': forms.TextInput(attrs={'type': 'color'}),
        }
    def clean_logo(self):
        logo = self.cleaned_data.get('logo')
        return validate_upload(logo) if logo else logo


class MemberForm(forms.ModelForm):
    project_access = forms.ModelMultipleChoiceField(
        label='دسترسی به پروژه‌ها',
        queryset=Project.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text='عضویت در میزکار به‌تنهایی دسترسی به پروژه‌ها ایجاد نمی‌کند.',
    )

    class Meta:
        model = WorkspaceMember
        fields = ['name', 'phone', 'role']

    def __init__(self, *args, workspace=None, **kwargs):
        self.workspace = workspace
        super().__init__(*args, **kwargs)
        if workspace is not None:
            self.fields['project_access'].queryset = workspace.projects.all().order_by('priority', 'manual_order', 'name')
        else:
            self.fields['project_access'].queryset = Project.objects.none()

    def clean_phone(self):
        phone = normalize_mobile(self.cleaned_data.get('phone'))
        if not phone:
            raise forms.ValidationError('شماره موبایل معتبر وارد کنید.')
        if self.workspace is not None:
            for member in self.workspace.members.exclude(pk=getattr(self.instance, 'pk', None)):
                if normalize_mobile(member.phone) == phone:
                    raise forms.ValidationError('این شماره موبایل قبلاً در این میزکار ثبت شده است.')
        return phone


class WorkspaceImportForm(forms.Form):
    file = forms.FileField(
        label='فایل خروجی میزکار',
        help_text='فایل JSON ساخته‌شده توسط بخش خروجی میزکار کارما را انتخاب کنید.',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.json,application/json'}),
    )
