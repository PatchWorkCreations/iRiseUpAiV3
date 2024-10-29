from django.db import models
from django.contrib.auth.models import User

class SquareCustomer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    customer_id = models.CharField(max_length=255, unique=True)
    card_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.customer_id}"


class Transaction(models.Model):
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('error', 'Error'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Store in dollars, for example
    subscription_type = models.CharField(max_length=50)  # Example: '1-week', '4-week', etc.
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    error_logs = models.TextField(blank=True, null=True)
    recurring = models.BooleanField(default=False)
    next_billing_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.subscription_type} - {self.status}"
    

class UserAccess(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    expiration_date = models.DateField(blank=True, null=True)
    selected_plan = models.CharField(max_length=50)  # '1-week', '4-week', etc.

    def __str__(self):
        return f"{self.user.username} - {self.selected_plan}"

