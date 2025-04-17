from django.urls import path
from .views import MpesaPaymentView, StripePaymentView, PaymentListView

urlpatterns = [
    path('mpesa/', MpesaPaymentView.as_view(), name='mpesa-payment'),
    path('gateway/', StripePaymentView.as_view(), name='gateway-payment'),
    path('all/', PaymentListView.as_view(), name='all-payments'),

]
