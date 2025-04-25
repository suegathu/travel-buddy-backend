from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Place(models.Model):
    PLACE_TYPES = [
        ('restaurant', 'Restaurant'),
        ('hotel', 'Hotel'),
        ('attraction', 'Attraction'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    image_url = models.URLField(blank=True)
    place_type = models.CharField(max_length=20, choices=PLACE_TYPES)
    cuisine = models.CharField(max_length=100, blank=True, null=True)  # For restaurants
    rating = models.FloatField(default=4.0)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        default=1 
    )
    
    def __str__(self):
        return self.name

class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_METHODS = [
        ('mpesa', 'M-Pesa'),
        ('visa', 'Visa/PayPal'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    booking_date = models.DateField()
    check_in = models.DateField(blank=True, null=True)  # For hotels
    check_out = models.DateField(blank=True, null=True)  # For hotels
    guests = models.PositiveIntegerField(default=1)
    room_type = models.CharField(max_length=50, blank=True, null=True)  # For hotels
    meal_choices = models.TextField(blank=True, null=True)  # For restaurants
    visit_time = models.TimeField(blank=True, null=True)  # For attractions
    total_price = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    payment_confirmed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.place.name} - {self.user.username}"