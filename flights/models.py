from django.db import models
from django.contrib.auth import get_user_model
import uuid
from django.utils import timezone
from django.conf import settings

User = get_user_model()

class Flight(models.Model):
    flight_number = models.CharField(primary_key=True, max_length=10, unique=True)
    airline = models.CharField(max_length=100)
    origin = models.CharField(max_length=100)  
    destination = models.CharField(max_length=100)  
    departure_time = models.DateTimeField(default=timezone.now)  
    arrival_time = models.DateTimeField(default=timezone.now)
    available_seats = models.IntegerField(default=100)  
    price = models.DecimalField(max_digits=10, decimal_places=2, default=200.00)  

    def __str__(self):
        return f"{self.flight_number} - {self.airline}"

class FlightBooking(models.Model):
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('pending', 'Pending'),
        ('checked_in', 'Checked In'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE)
    seat_number = models.CharField(max_length=10)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)  # ✅ Remove default=timezone.now

    def __str__(self):
        return f"Booking {self.id} - {self.user.username} ({self.status})"