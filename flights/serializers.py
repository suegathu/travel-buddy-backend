from rest_framework import serializers
from .models import Flight, FlightBooking

class FlightSerializer(serializers.ModelSerializer):
    seat_reservations = serializers.SerializerMethodField()
    
    class Meta:
        model = Flight
        fields = [
            'flight_number', 'airline', 'origin', 'destination', 
            'departure_time', 'arrival_time', 'available_seats', 'price',
            'seat_reservations'
        ]
    
    def get_seat_reservations(self, obj):
        """Return a mapping of reserved seat numbers to user info"""
        reservations = {}
        bookings = obj.flightbooking_set.all()
        
        for booking in bookings:
            if booking.seat_number:
                user_name = "Unknown"
                if booking.user:
                    user_name = booking.user.get_full_name() or booking.user.username
                
                reservations[booking.seat_number] = {
                    'user': user_name,
                    'status': booking.status,
                    'booking_id': booking.id
                }
        
        return reservations

class FlightBookingSerializer(serializers.ModelSerializer):
    # Add these fields to the serializer but also include price directly
    flight_number = serializers.SerializerMethodField()
    airline = serializers.SerializerMethodField()  # Renamed for frontend compatibility
    origin = serializers.SerializerMethodField()  # Renamed for frontend compatibility
    destination = serializers.SerializerMethodField()  # Renamed for frontend compatibility
    departure_time = serializers.SerializerMethodField()
    arrival_time = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()  # Renamed from flight_price to price for frontend
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = FlightBooking
        fields = [
            'id', 'user', 'flight', 'seat_number', 'status', 'qr_code', 'created_at',
            'flight_number', 'airline', 'origin', 'destination',
            'departure_time', 'arrival_time', 'price', 'user_name'
        ]
    
    def get_flight_number(self, obj):
        return obj.flight.flight_number if obj.flight else None
    
    def get_airline(self, obj):  # Renamed from get_flight_airline
        return obj.flight.airline if obj.flight else None
    
    def get_origin(self, obj):  # Renamed from get_flight_origin
        return obj.flight.origin if obj.flight else None
    
    def get_destination(self, obj):  # Renamed from get_flight_destination
        return obj.flight.destination if obj.flight else None
    
    def get_departure_time(self, obj):
        return obj.flight.departure_time if obj.flight and obj.flight.departure_time else None
    
    def get_arrival_time(self, obj):
        return obj.flight.arrival_time if obj.flight and obj.flight.arrival_time else None
    
    def get_price(self, obj):  # Renamed from get_flight_price
        # Convert Decimal to float to ensure proper JSON serialization
        return str(obj.flight.price) if obj.flight and obj.flight.price else '0.00'
    
    def get_user_name(self, obj):
        if not obj.user:
            return None
        return obj.user.get_full_name() or obj.user.username