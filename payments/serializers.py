from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    place_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    booking_id = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = ['id', 'reference', 'email', 'amount', 'payment_method', 'status', 
                  'timestamp', 'place', 'place_name', 'user', 'user_email', 'booking', 'booking_id']
        read_only_fields = ['id', 'timestamp']
    
    def get_place_name(self, obj):
        return obj.place.name if obj.place else None
    
    def get_user_email(self, obj):
        return obj.user.email if obj.user else obj.email
        
    def get_booking_id(self, obj):
        return obj.booking.id if obj.booking else None