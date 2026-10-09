import mimetypes
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib import messages
from django.db.models import Q, Max
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse, FileResponse, Http404

from projects.models import Project
from projects.services import has_project_access, log
from projects.permissions import can_edit_project
from .security import validate_upload
from workspaces.models import WorkspaceMember
from workspaces.views import can_manage
from .models import (
    Conversation, ConversationParticipant, Message, MessageAttachment,
    ProjectDocument, Letter, Note, NoteChecklistItem, Notification,
    Notebook, NoteSection, NoteAttachment,
)
from .forms import (
    MessageForm, LetterForm, NoteForm, NoteChecklistForm, ProjectDocumentForm,
    NotebookForm, NoteSectionForm, NoteAttachmentForm,
)


def media_type(file):
    c = (getattr(file, 'content_type', '') or mimetypes.guess_type(file.name)[0] or '')
    if c.startswith('image/'):
        return 'image'
    if c.startswith('video/'):
        return 'video'
    if c.startswith('audio/'):
        return 'audio'
    if c in [
        'application/pdf', 'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/plain',
    ]:
        return 'document'
    return 'other'


def can_access_conversation(conversation, user):
    if conversation.kind == 'private':
        return conversation.participants.filter(user=user).exists()
    return has_project_access(conversation.project, user)


def accessible_projects(user):
    return Project.objects.filter(
        Q(workspace__owner=user) |
        Q(workspace__members__user=user, workspace__members__role__in=['owner', 'admin'], workspace__members__is_active=True) |
        Q(members__workspace_member__user=user, members__is_active=True)
    ).filter(is_archived=False).distinct().order_by('workspace__name', 'name')


def ensure_notebook(user):
    notebook = user.notebooks.filter(is_archived=False).order_by('position', 'created_at').first()
    return notebook


@login_required
def chat_center(request):
    base_project_access = (
        Q(project__workspace__owner=request.user) |
        Q(project__workspace__members__user=request.user, project__workspace__members__role__in=['owner', 'admin'], project__workspace__members__is_active=True) |
        Q(project__members__workspace_member__user=request.user, project__members__is_active=True)
    )
    conversations = Conversation.objects.filter(
        Q(kind='private', participants__user=request.user) |
        (base_project_access & ~Q(kind='private'))
    ).select_related('project', 'project__workspace').annotate(
        last_message_at=Max('messages__created_at')
    ).distinct().order_by('-last_message_at', '-created_at')

    kind = request.GET.get('kind', '').strip()
    if kind in {'private', 'follow_up', 'documents', 'custom'}:
        conversations = conversations.filter(kind=kind)

    return render(request, 'communication/chat_center.html', {
        'conversations': conversations,
        'kind_filter': kind,
    })


@login_required
def conversation(request, pk):
    c = get_object_or_404(Conversation.objects.select_related('project', 'project__workspace'), pk=pk)
    if not can_access_conversation(c, request.user):
        return redirect('dashboard')
    form = MessageForm(request.POST or None, request.FILES or None)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if request.method == 'POST':
        if not can_edit_project(c.project, request.user):
            return JsonResponse({'ok': False, 'error': 'permission_denied'}, status=403) if is_ajax else redirect('conversation', pk=pk)
        if form.is_valid():
            m = form.save(commit=False)
            m.conversation = c
            m.sender = request.user
            m.save()
            attachments = []
            for f in form.cleaned_data.get('attachments', []):
                a = MessageAttachment.objects.create(
                    message=m, file=f, original_name=f.name, media_type=media_type(f),
                )
                attachments.append({'name': a.original_name, 'type': a.media_type, 'url': reverse('message_attachment_download', args=[a.pk])})
            log(c.project, request.user, 'message', f'پیامی در چت «{c.title}» ارسال شد.')
            if is_ajax:
                return JsonResponse({'ok': True, 'message_id': m.pk, 'attachments': attachments})
            return redirect('conversation', pk=pk)
        if is_ajax:
            return JsonResponse({'ok': False, 'errors': form.errors.get_json_data()}, status=400)

    sibling_conversations = c.project.conversations.filter(kind__in=['follow_up','documents','custom']).order_by('kind','title')
    private_conversations = c.project.conversations.filter(kind='private', participants__user=request.user).distinct().order_by('title')
    return render(request, 'communication/conversation.html', {
        'conversation': c,
        'messages_list': c.messages.select_related('sender', 'sender__profile').prefetch_related('attachments').all(),
        'form': form,
        'sibling_conversations': sibling_conversations,
        'private_conversations': private_conversations,
    })


@login_required
def private_start(request, project_id, member_id):
    p = get_object_or_404(Project, pk=project_id)
    if not has_project_access(p, request.user):
        return redirect('dashboard')
    target = get_object_or_404(WorkspaceMember, pk=member_id, workspace=p.workspace, is_active=True)
    if not target.user or target.user_id == request.user.id:
        return redirect('project_detail', pk=p.pk)
    if not p.members.filter(workspace_member=target, is_active=True).exists():
        return redirect('project_detail', pk=p.pk)

    low, high = sorted([request.user.id, target.user_id])
    token = f'project-{p.pk}-private-{low}-{high}'
    c, _ = Conversation.objects.get_or_create(
        token=token,
        defaults={'project': p, 'kind': 'private', 'title': f'گفتگوی خصوصی · {target.name}', 'created_by': request.user},
    )
    ConversationParticipant.objects.get_or_create(conversation=c, user=request.user)
    ConversationParticipant.objects.get_or_create(conversation=c, user=target.user)
    return redirect('conversation', pk=c.pk)


@login_required
def voice_upload(request, pk):
    c = get_object_or_404(Conversation, pk=pk)
    if request.method != 'POST' or not can_access_conversation(c, request.user) or not can_edit_project(c.project, request.user):
        return JsonResponse({'ok': False}, status=403)
    f = request.FILES.get('voice')
    if not f:
        return JsonResponse({'ok': False, 'error': 'فایل صوتی دریافت نشد.'}, status=400)
    try:
        validate_upload(f)
    except Exception as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)
    m = Message.objects.create(conversation=c, sender=request.user, text='')
    a = MessageAttachment.objects.create(message=m, file=f, original_name=f.name, media_type='audio', is_voice_recording=True)
    log(c.project, request.user, 'voice_message', f'پیام صوتی در چت «{c.title}» ارسال شد.')
    return JsonResponse({'ok': True, 'message_id': m.pk, 'url': reverse('message_attachment_download', args=[a.pk])})


@login_required
def documents(request, project_id):
    p = get_object_or_404(Project, pk=project_id)
    if not has_project_access(p, request.user):
        return redirect('dashboard')
    docs = p.documents.order_by('-created_at')
    type_filter = request.GET.get('type', '').strip()
    if type_filter in {'text', 'image', 'video', 'audio', 'document', 'other'}:
        docs = docs.filter(media_type=type_filter)
    return render(request, 'communication/documents.html', {'project': p, 'documents': docs, 'type_filter': type_filter})


@login_required
def document_create(request, project_id):
    p = get_object_or_404(Project, pk=project_id)
    if not can_edit_project(p, request.user):
        return redirect('dashboard')
    form = ProjectDocumentForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        d = form.save(commit=False)
        d.project = p
        d.uploaded_by = request.user
        d.media_type = media_type(d.file) if d.file else 'text'
        d.save()
        log(p, request.user, 'document', f'مستند «{d.title}» به پروژه اضافه شد.')
        return redirect('documents', project_id=p.pk)
    return render(request, 'generic/form.html', {'form': form, 'title': 'مستند جدید', 'submit': 'ثبت مستند'})


@login_required
def letters(request, project_id):
    p = get_object_or_404(Project, pk=project_id)
    if not has_project_access(p, request.user):
        return redirect('dashboard')
    return render(request, 'communication/letters.html', {'project': p, 'letters': p.letters.order_by('-created_at')})


@login_required
def letter_create(request, project_id):
    p = get_object_or_404(Project, pk=project_id)
    if not can_edit_project(p, request.user):
        return redirect('dashboard')
    form = LetterForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        x = form.save(commit=False)
        x.project = p
        x.created_by = request.user
        x.save()
        x.number = f'{p.code or "PRJ"}-{x.created_at.year}-{x.pk:05d}'
        x.save(update_fields=['number'])
        log(p, request.user, 'letter', f'نامه «{x.subject}» ثبت شد.')
        return redirect('letters', project_id=p.pk)
    return render(request, 'generic/form.html', {'form': form, 'title': 'ثبت نامه', 'submit': 'ثبت نامه'})


@login_required
def notes(request):
    default_book = ensure_notebook(request.user)
    notebook_id = request.GET.get('book')
    notebook = request.user.notebooks.filter(pk=notebook_id, is_archived=False).first() if notebook_id else default_book
    if not notebook:
        notebook = default_book
    section_id = request.GET.get('section')
    section = notebook.sections.filter(pk=section_id).first() if section_id else notebook.sections.first()
    notes_qs = request.user.notes.filter(notebook=notebook, is_archived=False).select_related('section','project').order_by('-is_pinned','-updated_at')
    if section:
        notes_qs = notes_qs.filter(section=section)
    return render(request, 'communication/notes.html', {
        'notebooks': request.user.notebooks.filter(is_archived=False),
        'notebook': notebook,
        'sections': notebook.sections.all(),
        'section': section,
        'notes': notes_qs,
        'notebook_form': NotebookForm(),
        'section_form': NoteSectionForm(),
    })


@login_required
def notebook_create(request):
    if request.method == 'POST':
        form = NotebookForm(request.POST)
        if form.is_valid():
            book = form.save(commit=False)
            book.user = request.user
            book.position = request.user.notebooks.count() + 1
            book.save()
            section = NoteSection.objects.create(notebook=book, title='یادداشت‌ها', position=1)
            return redirect(f'{reverse("notes")}?book={book.pk}&section={section.pk}')
    return redirect('notes')


@login_required
def section_create(request, notebook_id):
    book = get_object_or_404(Notebook, pk=notebook_id, user=request.user)
    if request.method == 'POST':
        form = NoteSectionForm(request.POST)
        if form.is_valid():
            section = form.save(commit=False)
            section.notebook = book
            section.position = book.sections.count() + 1
            section.save()
            return redirect(f'{reverse("notes")}?book={book.pk}&section={section.pk}')
    return redirect('notes')


@login_required
def note_create(request):
    default_book = ensure_notebook(request.user)
    notebook = request.user.notebooks.filter(pk=request.GET.get('book')).first() or default_book
    section = notebook.sections.filter(pk=request.GET.get('section')).first() or notebook.sections.first()
    form = NoteForm(request.POST or None)
    form.fields['project'].queryset = accessible_projects(request.user)
    if request.method == 'POST' and form.is_valid():
        n = form.save(commit=False)
        n.user = request.user
        n.notebook = notebook
        n.section = section
        n.save()
        return redirect('note_detail', pk=n.pk)
    return render(request, 'communication/note_edit.html', {
        'form': form, 'title': 'صفحه جدید', 'notebook': notebook, 'section': section,
        'notebooks': request.user.notebooks.filter(is_archived=False), 'sections': notebook.sections.all(),
    })


@login_required
def note_detail(request, pk):
    note = get_object_or_404(Note.objects.select_related('notebook','section','project'), pk=pk, user=request.user)
    action = request.POST.get('action') if request.method == 'POST' else ''
    edit_form = NoteForm(request.POST if action == 'save' else None, instance=note)
    edit_form.fields['project'].queryset = accessible_projects(request.user)
    checklist_form = NoteChecklistForm()
    if request.method == 'POST' and action == 'save' and edit_form.is_valid():
        edit_form.save()
        messages.success(request, 'یادداشت ذخیره شد.')
        return redirect('note_detail', pk=pk)
    if request.method == 'POST' and action == 'checklist':
        checklist_form = NoteChecklistForm(request.POST)
        if checklist_form.is_valid():
            item = checklist_form.save(commit=False)
            item.note = note
            item.position = note.checklist.count() + 1
            item.save()
            return redirect('note_detail', pk=pk)
    return render(request, 'communication/note_detail.html', {
        'note': note,
        'form': edit_form,
        'checklist_form': checklist_form,
        'attachment_form': NoteAttachmentForm(),
        'notebooks': request.user.notebooks.filter(is_archived=False),
        'sections': note.notebook.sections.all(),
        'pages': request.user.notes.filter(notebook=note.notebook, section=note.section, is_archived=False).order_by('-is_pinned','-updated_at'),
    })


@login_required
def note_attachment_upload(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    if request.method == 'POST':
        form = NoteAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            for f in form.cleaned_data['files']:
                NoteAttachment.objects.create(note=note, file=f, original_name=f.name, media_type=media_type(f))
            messages.success(request, 'پیوست به یادداشت اضافه شد.')
    return redirect('note_detail', pk=pk)


@login_required
def note_check_toggle(request, item_id):
    item = get_object_or_404(NoteChecklistItem, pk=item_id, note__user=request.user)
    if request.method == 'POST':
        item.is_done = not item.is_done
        item.save(update_fields=['is_done'])
    return redirect('note_detail', pk=item.note_id)


@login_required
def notification_center(request):
    qs = request.user.notifications.all()
    if request.GET.get('unread'):
        qs = qs.filter(is_read=False)
    return render(request, 'communication/notifications.html', {'notifications': qs})


@login_required
def notification_read(request, pk):
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    if request.method != 'POST':
        return redirect('notification_center')
    n.is_read = True
    n.save(update_fields=['is_read'])
    return redirect(n.url or 'notification_center')


def _can_manage_project_content(project, user):
    return can_edit_project(project, user)


def _private_file_response(field, download_name):
    if not field:
        raise Http404
    response = FileResponse(field.open('rb'), as_attachment=False, filename=download_name)
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response


@login_required
def message_attachment_download(request, attachment_id):
    item = get_object_or_404(MessageAttachment.objects.select_related('message__conversation__project'), pk=attachment_id)
    if not can_access_conversation(item.message.conversation, request.user):
        raise Http404
    return _private_file_response(item.file, item.original_name or 'attachment')


@login_required
def document_download(request, document_id):
    item = get_object_or_404(ProjectDocument.objects.select_related('project'), pk=document_id)
    if not has_project_access(item.project, request.user):
        raise Http404
    return _private_file_response(item.file, item.file.name.rsplit('/', 1)[-1])


@login_required
def letter_download(request, letter_id):
    item = get_object_or_404(Letter.objects.select_related('project'), pk=letter_id)
    if not has_project_access(item.project, request.user):
        raise Http404
    return _private_file_response(item.attachment, item.attachment.name.rsplit('/', 1)[-1])


@login_required
def note_attachment_download(request, attachment_id):
    item = get_object_or_404(NoteAttachment.objects.select_related('note'), pk=attachment_id, note__user=request.user)
    return _private_file_response(item.file, item.original_name or 'attachment')


@login_required
def message_edit(request, message_id):
    m = get_object_or_404(Message.objects.select_related('conversation__project'), pk=message_id)
    if not can_access_conversation(m.conversation, request.user) or m.sender_id != request.user.id:
        return redirect('conversation', pk=m.conversation_id)
    if request.method == 'POST':
        text = (request.POST.get('text') or '').strip()
        if text or m.attachments.exists():
            from django.utils import timezone
            m.text = text
            m.edited_at = timezone.now()
            m.save(update_fields=['text', 'edited_at'])
            messages.success(request, 'پیام ویرایش شد.')
        return redirect('conversation', pk=m.conversation_id)
    return render(request, 'communication/message_edit.html', {'message': m})


@login_required
def message_delete(request, message_id):
    m = get_object_or_404(Message.objects.select_related('conversation__project', 'conversation__project__workspace'), pk=message_id)
    c = m.conversation
    allowed = m.sender_id == request.user.id or can_manage(c.project.workspace, request.user)
    if not allowed or not can_access_conversation(c, request.user):
        return redirect('conversation', pk=c.pk)
    if request.method == 'POST':
        for a in list(m.attachments.all()):
            if a.file:
                a.file.delete(save=False)
        m.delete()
        messages.success(request, 'پیام حذف شد.')
    return redirect('conversation', pk=c.pk)


@login_required
def document_edit(request, document_id):
    d = get_object_or_404(ProjectDocument.objects.select_related('project'), pk=document_id)
    if not _can_manage_project_content(d.project, request.user):
        return redirect('dashboard')
    old_file = d.file.name if d.file else ''
    form = ProjectDocumentForm(request.POST or None, request.FILES or None, instance=d)
    if request.method == 'POST' and form.is_valid():
        d = form.save(commit=False)
        if request.FILES.get('file'):
            d.media_type = media_type(request.FILES['file'])
        elif not d.file and d.text_content:
            d.media_type = 'text'
        d.save()
        if old_file and request.FILES.get('file') and old_file != d.file.name:
            from django.core.files.storage import default_storage
            if default_storage.exists(old_file):
                default_storage.delete(old_file)
        log(d.project, request.user, 'document_updated', f'مستند «{d.title}» ویرایش شد.')
        messages.success(request, 'مستند ویرایش شد.')
        return redirect('documents', project_id=d.project_id)
    return render(request, 'generic/form.html', {'form': form, 'title': f'ویرایش مستند: {d.title}', 'submit': 'ذخیره تغییرات'})


@login_required
def document_delete(request, document_id):
    d = get_object_or_404(ProjectDocument.objects.select_related('project'), pk=document_id)
    p = d.project
    if not _can_manage_project_content(p, request.user):
        return redirect('dashboard')
    if request.method == 'POST':
        title = d.title
        if d.file:
            d.file.delete(save=False)
        d.delete()
        log(p, request.user, 'document_deleted', f'مستند «{title}» حذف شد.')
        messages.success(request, 'مستند حذف شد.')
    return redirect('documents', project_id=p.pk)


@login_required
def letter_edit(request, letter_id):
    letter = get_object_or_404(Letter.objects.select_related('project'), pk=letter_id)
    if not _can_manage_project_content(letter.project, request.user):
        return redirect('dashboard')
    old_file = letter.attachment.name if letter.attachment else ''
    form = LetterForm(request.POST or None, request.FILES or None, instance=letter)
    if request.method == 'POST' and form.is_valid():
        letter = form.save()
        if old_file and request.FILES.get('attachment') and old_file != letter.attachment.name:
            from django.core.files.storage import default_storage
            if default_storage.exists(old_file):
                default_storage.delete(old_file)
        log(letter.project, request.user, 'letter_updated', f'نامه «{letter.subject}» ویرایش شد.')
        messages.success(request, 'نامه ویرایش شد.')
        return redirect('letters', project_id=letter.project_id)
    return render(request, 'generic/form.html', {'form': form, 'title': f'ویرایش نامه {letter.number}', 'submit': 'ذخیره تغییرات'})


@login_required
def letter_delete(request, letter_id):
    letter = get_object_or_404(Letter.objects.select_related('project'), pk=letter_id)
    p = letter.project
    if not _can_manage_project_content(p, request.user):
        return redirect('dashboard')
    if request.method == 'POST':
        subject = letter.subject
        if letter.attachment:
            letter.attachment.delete(save=False)
        letter.delete()
        log(p, request.user, 'letter_deleted', f'نامه «{subject}» حذف شد.')
        messages.success(request, 'نامه حذف شد.')
    return redirect('letters', project_id=p.pk)


@login_required
def notebook_edit(request, notebook_id):
    book = get_object_or_404(Notebook, pk=notebook_id, user=request.user, is_archived=False)
    form = NotebookForm(request.POST or None, instance=book)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'دفترچه ویرایش شد.')
        return redirect(f'{reverse("notes")}?book={book.pk}')
    return render(request, 'generic/form.html', {'form': form, 'title': f'ویرایش دفترچه: {book.title}', 'submit': 'ذخیره'})


@login_required
def notebook_delete(request, notebook_id):
    book = get_object_or_404(Notebook, pk=notebook_id, user=request.user, is_archived=False)
    if request.method == 'POST':
        book.is_archived = True
        book.save(update_fields=['is_archived'])
        book.notes.update(is_archived=True)
        messages.success(request, 'دفترچه و صفحه‌های آن بایگانی شدند.')
    return redirect('notes')


@login_required
def section_edit(request, section_id):
    section = get_object_or_404(NoteSection.objects.select_related('notebook'), pk=section_id, notebook__user=request.user)
    form = NoteSectionForm(request.POST or None, instance=section)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'نام بخش ویرایش شد.')
        return redirect(f'{reverse("notes")}?book={section.notebook_id}&section={section.pk}')
    return render(request, 'generic/form.html', {'form': form, 'title': f'ویرایش بخش: {section.title}', 'submit': 'ذخیره'})


@login_required
def section_delete(request, section_id):
    section = get_object_or_404(NoteSection.objects.select_related('notebook'), pk=section_id, notebook__user=request.user)
    book = section.notebook
    if request.method == 'POST':
        replacement = book.sections.exclude(pk=section.pk).first()
        if not replacement:
            replacement = NoteSection.objects.create(notebook=book, title='یادداشت‌ها', position=1)
        section.notes.update(section=replacement)
        section.delete()
        messages.success(request, 'بخش حذف شد و صفحه‌های آن به بخش دیگری منتقل شدند.')
        return redirect(f'{reverse("notes")}?book={book.pk}&section={replacement.pk}')
    return redirect('notes')


@login_required
def note_delete(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    book_id = note.notebook_id
    section_id = note.section_id
    if request.method == 'POST':
        note.is_archived = True
        note.save(update_fields=['is_archived'])
        messages.success(request, 'صفحه یادداشت بایگانی شد.')
    url = reverse('notes')
    if book_id:
        url += f'?book={book_id}'
        if section_id:
            url += f'&section={section_id}'
    return redirect(url)


@login_required
def note_attachment_delete(request, attachment_id):
    a = get_object_or_404(NoteAttachment.objects.select_related('note'), pk=attachment_id, note__user=request.user)
    note_id = a.note_id
    if request.method == 'POST':
        if a.file:
            a.file.delete(save=False)
        a.delete()
        messages.success(request, 'پیوست حذف شد.')
    return redirect('note_detail', pk=note_id)


@login_required
def note_check_edit(request, item_id):
    item = get_object_or_404(NoteChecklistItem, pk=item_id, note__user=request.user)
    form = NoteChecklistForm(request.POST or None, instance=item)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('note_detail', pk=item.note_id)
    return render(request, 'generic/form.html', {'form': form, 'title': 'ویرایش چک‌لیست یادداشت', 'submit': 'ذخیره'})


@login_required
def note_check_delete(request, item_id):
    item = get_object_or_404(NoteChecklistItem, pk=item_id, note__user=request.user)
    note_id = item.note_id
    if request.method == 'POST':
        item.delete()
    return redirect('note_detail', pk=note_id)
