from django.contrib import admin
from .models import KahootSession


@admin.register(KahootSession)
class KahootSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'created_at', 'questions_count', 'participants_count', 'is_active']
    list_filter = ['is_active', 'timer_enabled', 'created_at']
    search_fields = ['session_id']
    readonly_fields = ['session_id', 'created_at', 'started_at', 'ended_at']
    
    def participants_count(self, obj):
        return len(obj.participants)
    participants_count.short_description = 'Participants'



