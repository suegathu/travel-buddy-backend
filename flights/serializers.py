from rest_framework import serializers
from .models import Flight, FlightBooking

class FlightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flight
        fields = '__all__'

class FlightBookingSerializer(serializers.ModelSerializer):
    flight = FlightSerializer()
    class Meta:
        model = FlightBooking
        fields = '__all__'

        