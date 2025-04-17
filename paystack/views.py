# views.py
from django.shortcuts import render
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.conf import settings
from rest_framework import generics
from .models import PaystackPayment
from .serializers import PaystackPaymentSerializer
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
import uuid

class PaystackInitializeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        email = request.data.get("email")
        amount = request.data.get("amount")
        reference = request.data.get("reference", f"pay-{uuid.uuid4().hex[:10]}")
        place_id = request.data.get("place_id")
        
        if not email or not amount:
            return Response({"error": "Email and amount are required"}, status=400)

        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
        "email": email,
        "amount": int(float(amount) * 100),
        "currency": "KES",   # <<=== Add this line!
        "reference": reference,
        "callback_url": f"{settings.FRONTEND_URL}/payment/verify/",
        "metadata": {
            "user_id": request.user.id,
            "place_id": place_id
        }
    }


        response = requests.post("https://api.paystack.co/transaction/initialize", 
                                json=payload, headers=headers)
        result = response.json()

        if response.status_code == 200:
            # Save to DB
            PaystackPayment.objects.create(
                user=request.user,
                amount=amount,
                reference=reference,
                status="pending",
                place_id=place_id
            )
            return Response(result, status=200)
        else:
            return Response(result, status=response.status_code)


class PaystackMpesaSTKPushView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        phone = request.data.get("phone")
        email = request.data.get("email")
        amount = request.data.get("amount")
        reference = request.data.get("reference", f"mpesa-{uuid.uuid4().hex[:10]}")
        place_id = request.data.get("place_id")

        if not phone or not amount:
            return Response({"error": "Phone and amount are required"}, status=400)

        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "email": email,
            "amount": int(float(amount) * 100),
            "currency": "KES",
            "mobile_money": {
                "phone": phone,
                "provider": "mpesa"
            },
            "reference": reference,
            "metadata": {
                "user_id": request.user.id,
                "place_id": place_id
            }
        }

        response = requests.post("https://api.paystack.co/charge", 
                                json=payload, headers=headers)
        result = response.json()

        if response.status_code == 200:
            # Save to DB
            PaystackPayment.objects.create(
                user=request.user,
                phone=phone,
                amount=amount,
                reference=reference,
                status="pending",
                place_id=place_id
            )
            return Response({"message": "STK Push sent", "data": result}, status=200)
        else:
            return Response(result, status=response.status_code)


class PaymentStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, reference):
        try:
            # Try to get the payment from the database
            try:
                payment = PaystackPayment.objects.get(reference=reference)
                
                # If already verified in database
                if payment.status == "success":
                    return Response({
                        "status": "success",
                        "message": "Payment was successful"
                    })
            except PaystackPayment.DoesNotExist:
                # Payment might not be saved yet, we'll verify with Paystack directly
                pass
            
            # Check status from Paystack API
            headers = {
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"
            }
            
            response = requests.get(
                f"https://api.paystack.co/transaction/verify/{reference}",
                headers=headers
            )
            
            result = response.json()
            
            if response.status_code == 200 and result.get("status"):
                transaction_status = result["data"]["status"]
                
                # Update or create the payment record
                payment_data = {
                    "status": transaction_status if transaction_status in ["success", "failed"] else "pending",
                    "amount": result["data"]["amount"] / 100,  # Convert from kobo
                }
                
                # Extract metadata if available
                metadata = result["data"].get("metadata", {})
                place_id = metadata.get("place_id")
                if place_id:
                    payment_data["place_id"] = place_id
                
                # Update existing or create new payment record
                try:
                    payment = PaystackPayment.objects.get(reference=reference)
                    for key, value in payment_data.items():
                        setattr(payment, key, value)
                    payment.save()
                except PaystackPayment.DoesNotExist:
                    # Get user from metadata if possible
                    user_id = metadata.get("user_id") or request.user.id
                    try:
                        from django.contrib.auth import get_user_model
                        User = get_user_model()
                        user = User.objects.get(id=user_id)
                        
                        payment_data.update({
                            "user": user,
                            "reference": reference,
                            "email": result["data"].get("customer", {}).get("email", "")
                        })
                        
                        PaystackPayment.objects.create(**payment_data)
                    except User.DoesNotExist:
                        return Response({
                            "status": "error",
                            "message": "Could not associate payment with user"
                        }, status=400)
                
                # Return appropriate response based on status
                if transaction_status == "success":
                    return Response({
                        "status": "success",
                        "message": "Payment was successful"
                    })
                elif transaction_status == "failed":
                    return Response({
                        "status": "failed",
                        "message": "Payment failed"
                    })
                else:
                    return Response({
                        "status": "pending",
                        "message": "Payment is still processing"
                    })
            else:
                return Response({
                    "status": "error",
                    "message": "Could not verify payment status"
                }, status=400)
                
        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=500)

class UserPaystackPaymentsView(generics.ListAPIView):
    serializer_class = PaystackPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PaystackPayment.objects.filter(user=self.request.user)


@csrf_exempt
def paystack_webhook(request):
    if request.method == "POST":
        # Verify the webhook signature if needed
        payload = json.loads(request.body)
        event = payload.get("event")
        
        if event == "charge.success":
            reference = payload["data"]["reference"]
            amount = payload["data"]["amount"] / 100  # Convert from kobo
            status = "success"
            
            try:
                payment = PaystackPayment.objects.get(reference=reference)
                payment.status = status
                payment.verified = True
                payment.save()
                
                # Here you could create a ticket or process other business logic
                
            except PaystackPayment.DoesNotExist:
                # Create a new payment record if it doesn't exist
                user_id = payload["data"]["metadata"].get("user_id")
                place_id = payload["data"]["metadata"].get("place_id")
                
                if user_id:
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    try:
                        user = User.objects.get(id=user_id)
                        PaystackPayment.objects.create(
                            user=user,
                            amount=amount,
                            reference=reference,
                            status=status,
                            verified=True,
                            place_id=place_id
                        )
                    except User.DoesNotExist:
                        pass
        
        return JsonResponse({"status": "ok"})
    
    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=400)