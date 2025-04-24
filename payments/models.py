from django.db import models
from places.models import Place, Booking  # Import Booking from places app
from django.contrib.auth import get_user_model

User = get_user_model()

class Payment(models.Model):
    PAYMENT_METHODS = [
        ('mpesa', 'M-Pesa'),
        ('card', 'Card'),
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    
    # Fields that match the serializer and frontend
    reference = models.CharField(max_length=100, unique=True)
    email = models.EmailField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Foreign keys
    place = models.ForeignKey(Place, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    booking = models.ForeignKey('places.Booking', on_delete=models.SET_NULL, null=True, blank=True)  # Updated to reference places.Booking
    
    def __str__(self):
        return f"{self.reference} - {self.email} - {self.payment_method} - {self.status}"