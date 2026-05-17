from django.db import models
import uuid


class ChatKnowledge(models.Model):
    """Saved Q&A pairs — chatbot learns from superadmin answers"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.TextField()           # original question
    keywords  = models.TextField()          # comma-separated keywords for matching
    answer    = models.TextField()          # the answer
    hits      = models.IntegerField(default=0)  # how many times used
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.question[:80]

    class Meta:
        ordering = ['-hits', '-created_at']


class ChatSession(models.Model):
    """A user chat session"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_key = models.CharField(max_length=100)
    user_name   = models.CharField(max_length=100, default='Guest')
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.user_name} – {self.created_at.strftime('%d %b %H:%M')}"


class ChatMessage(models.Model):
    """Individual messages in a chat"""
    SENDER_CHOICES = [('user', 'User'), ('bot', 'Bot'), ('admin', 'Admin')]
    STATUS_CHOICES = [('answered', 'Answered'), ('pending', 'Pending Superadmin')]

    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session   = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    sender    = models.CharField(max_length=10, choices=SENDER_CHOICES)
    message   = models.TextField()
    status    = models.CharField(max_length=20, choices=STATUS_CHOICES, default='answered')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.sender}] {self.message[:60]}"

    class Meta:
        ordering = ['created_at']


class PendingQuestion(models.Model):
    """Questions chatbot couldn't answer — waiting for superadmin"""
    STATUS_CHOICES = [('pending', 'Pending'), ('answered', 'Answered')]

    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session   = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='pending')
    question  = models.TextField()
    answer    = models.TextField(blank=True, null=True)
    status    = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    save_to_knowledge = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.status}] {self.question[:80]}"

    class Meta:
        ordering = ['-created_at']
