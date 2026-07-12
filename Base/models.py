from django.db import models
from django.utils import timezone


class Contact(models.Model):
    name    = models.CharField(max_length=50)
    email   = models.EmailField(max_length=50)
    number  = models.CharField(max_length=30)
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} — {self.email}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'


class VisitorLog(models.Model):
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    country     = models.CharField(max_length=100, blank=True)
    city        = models.CharField(max_length=100, blank=True)
    region      = models.CharField(max_length=100, blank=True)
    user_agent  = models.TextField(blank=True)
    browser     = models.CharField(max_length=100, blank=True)
    os          = models.CharField(max_length=100, blank=True)
    device      = models.CharField(max_length=50, blank=True)  # desktop/mobile/tablet
    page        = models.CharField(max_length=255, default='/')
    referrer    = models.CharField(max_length=500, blank=True)
    visited_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ip_address} — {self.country} ({self.visited_at.strftime('%Y-%m-%d %H:%M')})"

    class Meta:
        ordering = ['-visited_at']
        verbose_name = 'Visitor Log'
        verbose_name_plural = 'Visitor Logs'


class ResumeDownload(models.Model):
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    downloaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Download — {self.ip_address} ({self.downloaded_at.strftime('%Y-%m-%d %H:%M')})"

    class Meta:
        ordering = ['-downloaded_at']
        verbose_name = 'Resume Download'
        verbose_name_plural = 'Resume Downloads'


class SkillEndorsement(models.Model):
    skill_name = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    endorsed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.skill_name} — {self.ip_address}"

    class Meta:
        ordering = ['-endorsed_at']
        verbose_name = 'Skill Endorsement'
        verbose_name_plural = 'Skill Endorsements'


class ChatLog(models.Model):
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_message = models.TextField()
    bot_response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat — {self.ip_address} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Chat Log'
        verbose_name_plural = 'Chat Logs'
