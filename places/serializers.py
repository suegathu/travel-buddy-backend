from rest_framework import serializers
from .models import Place, Booking
from decimal import Decimal
from decimal import InvalidOperation

class PlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Place
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at']

class BookingSerializer(serializers.ModelSerializer):
    place_name = serializers.CharField(source='place.name', read_only=True)
    location = serializers.CharField(source='place.location', read_only=True)  
    place_type = serializers.CharField(source='place.place_type', read_only=True)

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ['user', 'status', 'payment_confirmed']

    def validate(self, data):
        place = data.get('place')
        if place:
            # Validation based on place type
            if place.place_type == 'hotel':
                if not data.get('check_in') or not data.get('check_out'):
                    raise serializers.ValidationError("Check-in and Check-out are required for hotel bookings.")
            elif place.place_type == 'restaurant':
                if not data.get('meal_choices'):
                    raise serializers.ValidationError("Meal choices are required for restaurant bookings.")
            elif place.place_type == 'attraction':
                if not data.get('visit_time'):
                    raise serializers.ValidationError("Visit time is required for attraction bookings.")

        # Validation for total_price to ensure it is a valid number
        total_price = data.get('total_price')
        if total_price:
            try:
                # Convert total_price to a decimal to ensure it's stored correctly
                data['total_price'] = Decimal(str(total_price))
            except (ValueError, InvalidOperation):
                raise serializers.ValidationError("Total price must be a valid number.")
        
        # If all validations pass, return the cleaned data
        return data

    def create(self, validated_data):
        # Attach user from the request context (authenticated user)
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
    
class BookingDetailSerializer(serializers.ModelSerializer):
    place_type = serializers.CharField(source='place.place_type', read_only=True)
    place_name = serializers.CharField(source='place.name', read_only=True)
    place_image = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'booking_date', 'check_in', 'check_out',
            'guests', 'room_type', 'meal_choices',
            'visit_time', 'total_price', 'status',
            'payment_method', 'payment_confirmed',
            'place_type', 'place_name', 'place_image'
        ]

    def get_place_image(self, obj):
        return obj.place.image_url or None


class AdminBookingSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    place_name = serializers.CharField(source='place.name', read_only=True)
    place_type = serializers.CharField(source='place.place_type', read_only=True)  # Add place type for admin view

    class Meta:
        model = Booking
        fields = [
            'id', 'user_name', 'user_email', 'place_name', 'place_type',  # Added place_type here
            'booking_date', 'check_in', 'check_out', 'guests', 'room_type',
            'meal_choices', 'visit_time', 'total_price', 'status',
            'payment_method', 'payment_confirmed'
        ]
        read_only_fields = ['user_name', 'user_email', 'place_name', 'place_type']  # Mark place_type as read-only
