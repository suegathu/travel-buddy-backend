from django.urls import path
from . import views

urlpatterns = [
    # Payment processing endpoints
    path('mpesa/', views.MpesaPaymentView.as_view(), name='mpesa-payment'),
    path('stripe/', views.StripePaymentView.as_view(), name='stripe-payment'),
    
    # Payment management endpoints
    path('all/', views.PaymentListView.as_view(), name='payment-list'),
    path('<int:id>/', views.PaymentDetailView.as_view(), name='payment-detail'),
    path('user/', views.UserPaymentListView.as_view(), name='user-payment-list'),
    path('<int:payment_id>/status/', views.PaymentStatusUpdateView.as_view(), name='payment-status-update'),
    
    # Payment verification endpoint
    path('status/<str:reference>/', views.PaymentVerificationView.as_view(), name='payment-verification'),
]