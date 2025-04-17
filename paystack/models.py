# models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class PaystackPayment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='paystack_payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    status = models.CharField(max_length=20, default='pending')
    verified = models.BooleanField(default=False)
    place_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} - {self.status}"