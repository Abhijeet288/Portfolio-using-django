from django.contrib import admin
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta

from Base.models import Contact, VisitorLog, ResumeDownload, SkillEndorsement, ChatLog


# ─── Contact ───────────────────────────────────
@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display  = ('name', 'email', 'number', 'short_content', 'created_at')
    list_filter   = ('created_at',)
    search_fields = ('name', 'email', 'content')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    def short_content(self, obj):
        return obj.content[:60] + '…' if len(obj.content) > 60 else obj.content
    short_content.short_description = 'Message'


# ─── Visitor Log ───────────────────────────────
@admin.register(VisitorLog)
class VisitorLogAdmin(admin.ModelAdmin):
    list_display  = ('flag_country', 'city', 'browser', 'os', 'device_icon', 'visited_at')
    list_filter   = ('country', 'browser', 'os', 'device')
    search_fields = ('ip_address', 'country', 'city')
    readonly_fields = ('visited_at',)
    ordering = ('-visited_at',)

    def flag_country(self, obj):
        return f"{obj.country or '—'}"
    flag_country.short_description = 'Country'

    def device_icon(self, obj):
        icons = {'Mobile': '📱', 'Tablet': '📲', 'Desktop': '🖥️'}
        return f"{icons.get(obj.device, '❓')} {obj.device}"
    device_icon.short_description = 'Device'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        today = timezone.now().date()
        last_30 = today - timedelta(days=30)

        extra_context['total_visitors'] = VisitorLog.objects.count()
        extra_context['today_visitors'] = VisitorLog.objects.filter(visited_at__date=today).count()
        extra_context['month_visitors'] = VisitorLog.objects.filter(visited_at__date__gte=last_30).count()
        extra_context['top_country'] = (
            VisitorLog.objects.values('country')
            .annotate(c=Count('id'))
            .order_by('-c').first()
        )
        return super().changelist_view(request, extra_context=extra_context)


# ─── Resume Download ────────────────────────────
@admin.register(ResumeDownload)
class ResumeDownloadAdmin(admin.ModelAdmin):
    list_display  = ('ip_address', 'downloaded_at')
    readonly_fields = ('downloaded_at',)
    ordering = ('-downloaded_at',)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['total_downloads'] = ResumeDownload.objects.count()
        return super().changelist_view(request, extra_context=extra_context)


# ─── Skill Endorsement ──────────────────────────
@admin.register(SkillEndorsement)
class SkillEndorsementAdmin(admin.ModelAdmin):
    list_display  = ('skill_name', 'ip_address', 'endorsed_at')
    list_filter   = ('skill_name',)
    readonly_fields = ('endorsed_at',)
    ordering = ('-endorsed_at',)


# ─── Chat Log ───────────────────────────────────
@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display  = ('ip_address', 'short_question', 'created_at')
    search_fields = ('user_message', 'bot_response')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    def short_question(self, obj):
        return obj.user_message[:80] + '…' if len(obj.user_message) > 80 else obj.user_message
    short_question.short_description = 'Question'