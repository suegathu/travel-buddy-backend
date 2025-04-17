from rest_framework import serializers
from .models import PaystackPayment

class PaystackPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaystackPayment
        fields = '__all__'
