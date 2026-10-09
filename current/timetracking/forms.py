from datetime import datetime
from django import forms
from django.utils import timezone

from dashboard.jalali import parse_jalali_date, format_jalali
from .models import WorkLog
from projects.models import Task


class JalaliWorkDateField(forms.DateField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label', 'تاریخ شمسی')
        kwargs.setdefault('widget', forms.TextInput(attrs={
            'class': 'form-control jalali-input',
            'placeholder': 'مثلاً ۱۴۰۵/۰۶/۰۲',
            'autocomplete': 'off',
            'inputmode': 'numeric',
            'data-jalali-picker': '1',
        }))
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if not value:
            return None
        try:
            return parse_jalali_date(value)
        except (ValueError, TypeError):
            raise forms.ValidationError('تاریخ را به‌صورت شمسی مانند ۱۴۰۵/۰۶/۰۲ انتخاب کنید.')

    def prepare_value(self, value):
        if hasattr(value, 'year'):
            return format_jalali(value)
        return value


class ManualWorkLogForm(forms.Form):
    work_date = JalaliWorkDateField()
    start_time = forms.TimeField(
        label='از ساعت',
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time', 'step': '60'}),
    )
    end_time = forms.TimeField(
        label='تا ساعت',
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time', 'step': '60'}),
    )
    task = forms.ModelChoiceField(
        label='وظیفه / بخش', required=False, queryset=Task.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    note = forms.CharField(
        label='شرح کار', required=False, max_length=500,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'در این بازه روی چه کاری کار کردید؟'}),
    )

    def __init__(self, *args, project=None, task=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.fields['task'].queryset = Task.objects.none()
        if project:
            self.fields['task'].queryset = project.tasks.order_by('status', 'title')
        if task:
            self.fields['task'].initial = task
            self.fields['task'].widget = forms.HiddenInput()
        self.fields['work_date'].initial = timezone.localdate()

    def clean(self):
        data = super().clean()
        d = data.get('work_date')
        start = data.get('start_time')
        end = data.get('end_time')
        if d and start and end:
            tz = timezone.get_current_timezone()
            started_at = timezone.make_aware(datetime.combine(d, start), tz)
            ended_at = timezone.make_aware(datetime.combine(d, end), tz)
            if ended_at <= started_at:
                self.add_error('end_time', 'ساعت پایان باید بعد از ساعت شروع باشد.')
            else:
                data['started_at'] = started_at
                data['ended_at'] = ended_at
        task = data.get('task')
        if task and self.project and task.project_id != self.project.id:
            self.add_error('task', 'وظیفه انتخاب‌شده متعلق به این پروژه نیست.')
        return data


class TimerStartForm(forms.Form):
    task = forms.ModelChoiceField(
        label='وظیفه / بخش', required=False, queryset=Task.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    note = forms.CharField(
        label='شرح کوتاه', required=False, max_length=500,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثلاً اصلاح صفحه ورود'}),
    )

    def __init__(self, *args, project=None, task=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['task'].queryset = Task.objects.none()
        if project:
            self.fields['task'].queryset = project.tasks.exclude(status='done').order_by('priority', 'title')
        if task:
            self.fields['task'].initial = task
            self.fields['task'].widget = forms.HiddenInput()
