from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Payment
from .serializers import PaymentSerializer
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.generics import ListAPIView
from django.core.mail import send_mail
from django.conf import settings
import uuid
from places.models import Place

class MpesaPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        transaction_id = str(uuid.uuid4())
        place_id = data.get('place_id')  # Assume place_id is passed from frontend

        # Fetch the place instance (if it exists)
        place = Place.objects.filter(id=place_id).first() if place_id else None

        payment = Payment.objects.create(
            user_email=request.user.email,
            amount=data['amount'],
            method='mpesa',
            transaction_id=transaction_id,
            status='success',
            place=place,  # Associate the place with the payment
        )

        # Send confirmation email
        send_payment_confirmation_email(
            to_email=request.user.email,
            booking_info={
                'id': payment.id,
                'place': place.name if place else 'N/A',  # Use the place's name if available
                'amount': payment.amount,
                'method': payment.method,
            }
        )

        return Response({'message': 'M-Pesa payment successful', 'transaction_id': transaction_id}, status=200)


class StripePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        transaction_id = str(uuid.uuid4())

        payment = Payment.objects.create(
            user_email=request.user.email,
            amount=data['amount'],
            method=data['method'],
            transaction_id=transaction_id,
            status='success',
            place_id=data.get('place_id')  # optional
        )

        # Send confirmation email
        send_payment_confirmation_email(
            to_email=request.user.email,
            booking_info={
                'id': payment.id,
                'place': payment.place.name if payment.place else 'N/A',
                'amount': payment.amount,
                'method': payment.method,
            }
        )

        return Response({'message': f"{data['method']} payment successful", 'transaction_id': transaction_id}, status=200)


class PaymentListView(ListAPIView):
    queryset = Payment.objects.all().order_by('-timestamp')
    serializer_class = PaymentSerializer
    permission_classes = [IsAdminUser]


# ✅ Email sender helper - placed at bottom to keep views clean
def send_payment_confirmation_email(to_email, booking_info):
    subject = 'Your Payment Confirmation'
    message = f"""
    Hello,

    Thank you for your payment.

    Booking ID: {booking_info.get('id')}
    Place: {booking_info.get('place')}
    Amount: {booking_info.get('amount')} KES
    Payment Method: {booking_info.get('method')}

    We hope you enjoy your experience!

    - The Travel Companion Team
    """
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [to_email])
