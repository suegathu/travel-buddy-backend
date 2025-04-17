# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('paystack/initialize/', views.PaystackInitializeView.as_view(), name='paystack_initialize'),
    path('paystack/mpesa/', views.PaystackMpesaSTKPushView.as_view(), name='paystack_mpesa'),
    path('status/<str:reference>/', views.PaymentStatusView.as_view(), name='payment_status'),
    path('user/', views.UserPaystackPaymentsView.as_view(), name='user_payments'),
    path('webhook/', views.paystack_webhook, name='paystack_webhook'),
]