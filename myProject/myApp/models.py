from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

# Renamed BotService to BotService to reflect AI service offerings
class BotService(models.Model):
    title = models.CharField(max_length=250)
    description = models.TextField(default="Default description")
    category = models.CharField(max_length=100, null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['order']

# Renamed AIUserAccess to AIUserAccess for AI bot access tracking
class AIUserAccess(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bot_service = models.ForeignKey(BotService, on_delete=models.CASCADE, null=True, blank=True)
    progress = models.FloatField(default=0.0)
    expiration_date = models.DateTimeField(null=True, blank=True)
    renewal_date = models.DateTimeField(null=True, blank=True)
    renewal_task_id = models.CharField(max_length=255, null=True, blank=True)
    selected_plan = models.CharField(max_length=20, null=True, blank=True)
    is_saved = models.BooleanField(default=False, null=True, blank=True)
    is_favorite = models.BooleanField(default=False, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.bot_service.title if self.bot_service else 'No Service'}"

    def has_expired(self):
        return self.expiration_date is not None and timezone.now() > self.expiration_date

    def set_renewal_date(self, plan_duration):
        if plan_duration:
            self.renewal_date = timezone.now() + timedelta(weeks=plan_duration)
            self.save()

# Renamed BotTransaction to BotBotTransaction to specify bot-related BotTransactions
class BotBotTransaction(models.Model):
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('pending', 'Pending'),
        ('error', 'Error'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', db_index=True)
    BotTransaction_date = models.DateTimeField(default=timezone.now, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    subscription_type = models.CharField(max_length=100)
    error_logs = models.TextField(blank=True, null=True)
    recurring = models.BooleanField(default=False)
    next_billing_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.subscription_type} - {self.status}"

# Example for payment storage, renamed to BotUserPaymentInfo
class BotUserPaymentInfo(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    customer_id = models.CharField(max_length=255, unique=True)
    card_id = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"{self.user.username} - {self.customer_id}"
