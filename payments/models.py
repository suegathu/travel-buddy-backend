from django.db import models
from places.models import Place

class Payment(models.Model):
    PAYMENT_METHODS = [
        ('mpesa', 'M-Pesa'),
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
        ('visa', 'Visa'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    user_email = models.EmailField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    place = models.ForeignKey(Place, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user_email} - {self.method} - {self.status}"
