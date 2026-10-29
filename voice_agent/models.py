from django.db import models

class VoiceRecordingLog(models.Model):
    SAVE_TYPE_CHOICES = (
        ('submit_feedback', 'Submitted Feedback'),
        ('without_submit', 'Without Submit (Saved on Close)'),
    )

    CONVERSATION_TYPE_CHOICES = (
        ('voice_agent', 'Voice Agent'),
        ('chat_agent', 'Chat Agent'),
        ('chat_voice_agent', 'Chat + Voice Agent'),
    )

    call_id = models.CharField(max_length=100, blank=True, null=True)
    rating = models.CharField(max_length=100, default='Call Completed')
    transcript = models.TextField(blank=True, default='')
    audio_file = models.FileField(upload_to='voice_recordings/%Y/%m/%d/', blank=True, null=True)
    save_type = models.CharField(max_length=50, choices=SAVE_TYPE_CHOICES, default='without_submit')
    conversation_type = models.CharField(
        max_length=50,
        choices=CONVERSATION_TYPE_CHOICES,
        default='voice_agent'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    token_details = models.TextField(blank=True, null=True)
    total_tokens = models.IntegerField(default=0)
    total_input_tokens = models.IntegerField(default=0)
    total_output_tokens = models.IntegerField(default=0)
    total_cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0.0)
    total_cost_inr = models.DecimalField(max_digits=10, decimal_places=4, default=0.0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_conversation_type_display()} | {self.get_save_type_display()}] {self.rating} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"




