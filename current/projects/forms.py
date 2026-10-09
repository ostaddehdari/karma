from django import forms
from .models import Project, Task, ChecklistItem, Milestone, TaskList
from dashboard.jalali import parse_jalali_date, format_jalali


class JalaliDateField(forms.DateField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('required', False)
        kwargs.setdefault('widget', forms.TextInput(attrs={
            'class': 'form-control jalali-input',
            'placeholder': 'مثلاً ۱۴۰۵/۰۵/۲۰',
            'inputmode': 'numeric',
            'autocomplete': 'off',
        }))
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if not value:
            return None
        try:
            return parse_jalali_date(value)
        except (ValueError, TypeError):
            raise forms.ValidationError('تاریخ را به‌صورت شمسی، مانند ۱۴۰۵/۰۵/۲۰ وارد کنید.')

    def prepare_value(self, value):
        if hasattr(value, 'year'):
            return format_jalali(value)
        return value


class ProjectForm(forms.ModelForm):
    start_date = JalaliDateField(label='تاریخ شروع')
    due_date = JalaliDateField(label='موعد پایان')

    class Meta:
        model = Project
        fields = ['name', 'code', 'description', 'priority', 'status', 'manager', 'start_date', 'due_date']
        labels = {
            'name': 'نام پروژه', 'code': 'کد پروژه', 'description': 'توضیحات',
            'priority': 'اولویت', 'status': 'وضعیت', 'manager': 'مدیر پروژه',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'توضیح کوتاه درباره پروژه...'}),
        }

    def __init__(self, *args, workspace=None, **kwargs):
        super().__init__(*args, **kwargs)
        if workspace:
            self.fields['manager'].queryset = workspace.members.filter(is_active=True).order_by('name')
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'form-control' if not isinstance(field.widget, forms.Select) else 'form-select')

    def clean(self):
        data = super().clean()
        start, due = data.get('start_date'), data.get('due_date')
        if start and due and due < start:
            self.add_error('due_date', 'موعد پایان نمی‌تواند قبل از تاریخ شروع باشد.')
        return data


class QuickProjectForm(forms.ModelForm):
    due_date = JalaliDateField(label='موعد', required=False)

    class Meta:
        model = Project
        fields = ['name', 'priority', 'manager', 'due_date']
        labels = {'name': 'نام پروژه', 'priority': 'اولویت', 'manager': 'مدیر'}
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام پروژه را بنویسید...', 'autofocus': True}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'manager': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, workspace=None, **kwargs):
        super().__init__(*args, **kwargs)
        if workspace:
            self.fields['manager'].queryset = workspace.members.filter(is_active=True).order_by('name')
        self.fields['manager'].required = False


class TaskForm(forms.ModelForm):
    due_date = JalaliDateField(label='موعد انجام')

    class Meta:
        model = Task
        fields = ['title', 'description', 'task_list', 'assignee', 'status', 'priority', 'due_date', 'progress']
        labels = {
            'title': 'عنوان وظیفه', 'description': 'توضیحات', 'task_list': 'فهرست',
            'assignee': 'مسئول', 'status': 'وضعیت', 'priority': 'اولویت', 'progress': 'درصد پیشرفت',
        }
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'چه کاری باید انجام شود؟'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'جزئیات اختیاری...'}),
            'progress': forms.NumberInput(attrs={'min': 0, 'max': 100}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project:
            self.fields['assignee'].queryset = project.workspace.members.filter(
                project_accesses__project=project,
                project_accesses__is_active=True,
                is_active=True,
            ).distinct().order_by('name')
            self.fields['task_list'].queryset = project.task_lists.all().order_by('position', 'title')
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'form-control' if not isinstance(field.widget, forms.Select) else 'form-select')

    def clean_progress(self):
        progress = self.cleaned_data['progress']
        if not 0 <= progress <= 100:
            raise forms.ValidationError('درصد پیشرفت باید بین ۰ تا ۱۰۰ باشد.')
        return progress


class QuickTaskForm(forms.ModelForm):
    due_date = JalaliDateField(label='موعد', required=False)

    class Meta:
        model = Task
        fields = ['title', 'assignee', 'priority', 'due_date', 'task_list']
        labels = {'title': 'عنوان وظیفه', 'assignee': 'مسئول', 'priority': 'اولویت', 'task_list': 'فهرست'}
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'وظیفه را بنویسید...', 'autofocus': True}),
            'assignee': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'task_list': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project:
            self.fields['assignee'].queryset = project.workspace.members.filter(
                project_accesses__project=project, project_accesses__is_active=True, is_active=True
            ).distinct().order_by('name')
            self.fields['task_list'].queryset = project.task_lists.all().order_by('position', 'title')
        self.fields['assignee'].required = False
        self.fields['task_list'].required = False


class TaskListForm(forms.ModelForm):
    class Meta:
        model = TaskList
        fields = ['title']
        labels = {'title': 'نام فهرست'}
        widgets = {'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثلاً کارهای این هفته'})}


class ChecklistForm(forms.ModelForm):
    class Meta:
        model = ChecklistItem
        fields = ['title']
        labels = {'title': 'آیتم چک‌لیست'}
        widgets = {'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'آیتم جدید...'})}


class MilestoneForm(forms.ModelForm):
    due_date = JalaliDateField(label='موعد', required=False)
    class Meta:
        model = Milestone
        fields = ['title', 'due_date', 'is_done']
        labels = {'title': 'عنوان نقطه عطف', 'is_done': 'تکمیل شده'}
        widgets = {'is_done': forms.CheckboxInput(attrs={'class': 'form-check-input'})}


class ProjectImportForm(forms.Form):
    file = forms.FileField(
        label='فایل خروجی پروژه',
        help_text='فایل JSON ساخته‌شده توسط خروجی پروژه کارما را انتخاب کنید.',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.json,application/json'}),
    )
