from django.contrib import admin
from .models import Feedback

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'rating', 'submitted_at')
    list_filter = ('rating', 'submitted_at')
    search_fields = ('user__email', 'comments')
    readonly_fields = ('submitted_at',)
    ordering = ('-submitted_at',)
