from django.contrib import admin
from .models import Flight, FlightBooking

# Register your models here.
admin.site.register(FlightBooking)
admin.site.register(Flight)
