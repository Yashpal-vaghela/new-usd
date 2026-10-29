import os
from django.contrib import admin
from django.utils.html import format_html, mark_safe
from .models import VoiceRecordingLog

@admin.register(VoiceRecordingLog)
class VoiceRecordingLogAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'conversation_type',
        'submission_badge',
        'rating',
        'audio_player_widget',
        'created_at'
    )
    list_filter = ('conversation_type', 'save_type', 'created_at')
    search_fields = ('transcript', 'rating', 'call_id')
    readonly_fields = ('created_at', 'call_id', 'audio_preview', 'formatted_transcript')
    fields = (
        'conversation_type',
        'save_type',
        'rating',
        'call_id',
        'audio_preview',
        'audio_file',
        'formatted_transcript',
        'created_at'
    )
    ordering = ('-id',)

    @admin.display(description="Submission Status")
    def submission_badge(self, obj):
        if obj.save_type == 'submit_feedback':
            return mark_safe('<span style="color:#15803d; font-weight:bold; background:#dcfce7; padding:2px 8px; border-radius:4px;">&#10004; Submitted</span>')
        return mark_safe('<span style="color:#64748b; background:#f1f5f9; padding:2px 8px; border-radius:4px;">Without Submit</span>')

    @admin.display(description="Audio Recording")
    def audio_player_widget(self, obj):
        if not obj.audio_file:
            return mark_safe('<span style="color:#94a3b8; font-size:12px;">No Audio (Chat)</span>')
        
        try:
            file_exists = bool(obj.audio_file.name and os.path.exists(obj.audio_file.path))
        except Exception:
            file_exists = False

        if file_exists:
            try:
                size_kb = round(os.path.getsize(obj.audio_file.path) / 1024, 1)
                size_str = f"{size_kb} KB"
            except Exception:
                size_str = ""
            url = obj.audio_file.url
            return mark_safe(f'''
                <div style="display:flex; align-items:center; gap:8px;">
                    <audio controls preload="none" style="height:30px; width:210px; outline:none; vertical-align:middle;">
                        <source src="{url}" type="audio/webm">
                        <source src="{url}" type="audio/mp4">
                        <source src="{url}" type="audio/wav">
                        Your browser does not support audio.
                    </audio>
                    <a href="{url}" download title="Download Recording ({size_str})" style="display:inline-flex; align-items:center; justify-content:center; width:28px; height:28px; background:#f1f5f9; border:1px solid #cbd5e1; border-radius:4px; text-decoration:none; font-size:14px;">&#128190;</a>
                </div>
            ''')
        else:
            filename = os.path.basename(obj.audio_file.name) if obj.audio_file.name else "Unknown"
            return mark_safe(f'''
                <span style="display:inline-flex; align-items:center; gap:4px; padding:3px 8px; border-radius:4px; font-size:11px; font-weight:600; background:#fef2f2; color:#b91c1c; border:1px solid #fecaca;" title="File missing on disk: {obj.audio_file.name}">
                    &#9888; File Missing ({filename})
                </span>
            ''')

    @admin.display(description="Audio Playback Preview")
    def audio_preview(self, obj):
        if not obj.audio_file:
            return mark_safe('<span style="color:#64748b;">No audio file attached to this log.</span>')
        
        try:
            file_exists = bool(obj.audio_file.name and os.path.exists(obj.audio_file.path))
        except Exception:
            file_exists = False

        if file_exists:
            size_kb = round(os.path.getsize(obj.audio_file.path) / 1024, 1)
            url = obj.audio_file.url
            return mark_safe(f'''
                <div style="padding:12px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; max-width:420px;">
                    <audio controls style="width:100%; margin-bottom:8px;">
                        <source src="{url}">
                    </audio>
                    <div style="font-size:12px; color:#475569; line-height:1.6;">
                        <div><b>Status:</b> <span style="color:#15803d; font-weight:bold;">&#10004; Available on Disk</span></div>
                        <div><b>File:</b> <code>{obj.audio_file.name}</code></div>
                        <div><b>Size:</b> {size_kb} KB</div>
                        <div><b>Full Path:</b> <code style="font-size:11px;">{obj.audio_file.path}</code></div>
                    </div>
                </div>
            ''')
        else:
            path_str = obj.audio_file.path if hasattr(obj.audio_file, 'path') else 'Unknown'
            return mark_safe(f'''
                <div style="padding:12px; background:#fef2f2; border:1px solid #fecaca; border-radius:6px; max-width:460px;">
                    <div style="color:#b91c1c; font-weight:bold; font-size:13px; margin-bottom:6px;">&#9888; Audio File Missing on Server Disk</div>
                    <div style="font-size:12px; color:#7f1d1d; line-height:1.6;">
                        <div><b>Database reference:</b> <code>{obj.audio_file.name}</code></div>
                        <div><b>Expected path:</b> <code style="font-size:11px;">{path_str}</code></div>
                        <div style="margin-top:6px; padding:6px 8px; background:#fff; border-radius:4px; border:1px dashed #fca5a5; font-size:11px; color:#991b1b;">
                            This historical recording file was deleted or cleared from the local <code>media/</code> folder during a past folder cleanup or git reset, so the web server cannot serve it.
                        </div>
                    </div>
                </div>
            ''')

    @admin.display(description="Conversation Transcript")
    def formatted_transcript(self, obj):
        if not obj.transcript or not obj.transcript.strip():
            return mark_safe('<span style="color:#94a3b8; font-style:italic;">No transcript available.</span>')
        return mark_safe(f'<pre style="white-space:pre-wrap; background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:12px; font-size:12px; line-height:1.6; max-height:400px; overflow-y:auto;">{obj.transcript}</pre>')
