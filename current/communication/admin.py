from django.contrib import admin
from .models import (
    Conversation, ConversationParticipant, Message, MessageAttachment,
    ProjectDocument, Letter, Notebook, NoteSection, Note, NoteAttachment,
    NoteChecklistItem, Notification,
)
for model in [
    Conversation, ConversationParticipant, Message, MessageAttachment,
    ProjectDocument, Letter, Notebook, NoteSection, Note, NoteAttachment,
    NoteChecklistItem, Notification,
]:
    admin.site.register(model)
