from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Payment
from .serializers import PaymentSerializer
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.generics import ListAPIView, RetrieveAPIView
from django.core.mail import send_mail
from django.conf import settings
import uuid
from places.models import Place, Booking
from django.contrib.auth import get_user_model

User = get_user_model()

class MpesaPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        reference = data.get('reference', str(uuid.uuid4()))
        place_id = data.get('place_id')
        
        # Fetch the place instance (if it exists)
        place = Place.objects.filter(id=place_id).first() if place_id else None
        
        # Get booking if provided
        booking_id = data.get('booking_id')
        booking = Booking.objects.filter(id=booking_id).first() if booking_id else None

        payment = Payment.objects.create(
            user=request.user,
            email=request.user.email,
            amount=data['amount'],
            payment_method='mpesa',  # Always use payment_method, not method
            reference=reference,
            status='success',
            place=place,
            booking=booking
        )

        # Send confirmation email
        send_payment_confirmation_email(
            to_email=request.user.email,
            booking_info={
                'id': payment.id,
                'place_name': place.name if place else 'N/A',
                'amount': payment.amount,
                'payment_method': payment.payment_method,  # Use consistent naming
                'reference': payment.reference
            }
        )

        return Response({'message': 'M-Pesa payment successful', 'reference': reference}, status=200)


class StripePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        reference = data.get('reference', str(uuid.uuid4()))
        place_id = data.get('place_id')
        
        # Fetch the place instance (if it exists)
        place = Place.objects.filter(id=place_id).first() if place_id else None
        
        # Get booking if provided
        booking_id = data.get('booking_id')
        booking = Booking.objects.filter(id=booking_id).first() if booking_id else None

        payment = Payment.objects.create(
            user=request.user,
            email=request.user.email,
            amount=data['amount'],
            payment_method=data['payment_method'],  # Changed from 'method' to match model
            reference=reference,
            status='success',
            place=place,
            booking=booking
        )

        # Send confirmation email
        send_payment_confirmation_email(
            to_email=request.user.email,
            booking_info={
                'id': payment.id,
                'place_name': payment.place.name if payment.place else 'N/A',
                'amount': payment.amount,
                'payment_method': payment.payment_method,
                'reference': payment.reference
            }
        )

        return Response({'message': f"{data['payment_method']} payment successful", 'reference': reference}, status=200)


class PaymentListView(ListAPIView):
    """
    Admin endpoint to fetch all payments
    """
    queryset = Payment.objects.all().order_by('-timestamp')
    serializer_class = PaymentSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Support filtering by query parameters
        status = self.request.query_params.get('status')
        payment_method = self.request.query_params.get('payment_method')  # Use payment_method consistently
        email = self.request.query_params.get('email')
        reference = self.request.query_params.get('reference')
        
        if status:
            queryset = queryset.filter(status=status)
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)  # Ensure this matches model field
        if email:
            queryset = queryset.filter(email__icontains=email)
        if reference:
            queryset = queryset.filter(reference__icontains=reference)
            
        return queryset

class PaymentDetailView(RetrieveAPIView):
    """
    Admin endpoint to fetch a specific payment detail
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'id'

class UserPaymentListView(ListAPIView):
    """
    Endpoint for users to view their own payments
    """
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return Payment.objects.filter(user=user).order_by('-timestamp')

class PaymentStatusUpdateView(APIView):
    """
    Admin endpoint to update payment status
    """
    permission_classes = [IsAdminUser]
    
    def patch(self, request, payment_id):
        try:
            payment = Payment.objects.get(id=payment_id)
            new_status = request.data.get('status')
            
            if new_status not in ['pending', 'success', 'failed']:
                return Response({"error": "Invalid status value"}, status=status.HTTP_400_BAD_REQUEST)
                
            payment.status = new_status
            payment.save()
            
            # If payment is marked as successful, send confirmation email
            if new_status == 'success':
                booking_info = {
                    'id': payment.id,
                    'place_name': payment.place.name if payment.place else 'N/A',
                    'amount': payment.amount,
                    'payment_method': payment.payment_method,
                    'reference': payment.reference
                }
                send_payment_confirmation_email(payment.email, booking_info)
            
            return Response(PaymentSerializer(payment).data)
            
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# New endpoint to verify payment status
class PaymentVerificationView(APIView):
    """
    Endpoint to verify payment status by reference
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, reference):
        try:
            payment = Payment.objects.get(reference=reference)
            return Response({
                'status': payment.status,
                'payment_method': payment.payment_method,  # Make sure this matches your model field
                'amount': str(payment.amount)
            })
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

# Email sender helper - consolidated to avoid duplication
def send_payment_confirmation_email(to_email, booking_info):
    subject = 'Your Payment Confirmation'
    message = f"""
    Hello,
    
    Thank you for your payment.
    
    Reference: {booking_info.get('reference')}
    Place: {booking_info.get('place_name')}
    Amount: {booking_info.get('amount')} KES
    Payment Method: {booking_info.get('payment_method')}
    
    We hope you enjoy your experience!
    
    - The Travel Companion Team
    """
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [to_email])