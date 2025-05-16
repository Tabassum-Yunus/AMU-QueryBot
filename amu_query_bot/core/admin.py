# from django.contrib import admin
# from .models import ChatMessage

# @admin.register(ChatMessage)
# class ChatMessageAdmin(admin.ModelAdmin):
#     list_display = ('user', 'message', 'response', 'timestamp')
#     list_filter = ('user', 'timestamp')
#     search_fields = ('user__email', 'message', 'response')
#     readonly_fields = ('timestamp',)
#     ordering = ('-timestamp',)