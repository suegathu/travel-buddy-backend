from django.urls import path
from .views import (
    PlaceListView,
    PlaceDetailView,
    BookingCreateView,
    UserBookingsListAPIView,
    AdminBookingListUpdateView,
    AdminBookingUpdateView,
    UserBookingDetailAPIView,
    AdminBookingDeleteView,
    PlaceListCreateView
)

urlpatterns = [
    # Public place views
    path('places/', PlaceListView.as_view(), name='place-list'),
    path('places/<int:pk>/', PlaceDetailView.as_view(), name='place-detail'),
    path("place/", PlaceListCreateView.as_view(), name="place-list-create"),
    #path('places/search/', PlaceSearchView.as_view(), name='place-search'),

    # Booking endpoints for users
    path('bookings/', BookingCreateView.as_view(), name='create-booking'),
    path('bookings/my/', UserBookingsListAPIView.as_view(), name='user-bookings'),
    path('bookings/<int:pk>/', UserBookingDetailAPIView.as_view(), name='booking-detail'),

    # Admin-only booking management
    path('admin/bookings/', AdminBookingListUpdateView.as_view(), name='admin-booking-list'),
    path('admin/bookings/<int:pk>/', AdminBookingUpdateView.as_view(), name='admin-booking-update'),
    path('admin/bookings/<int:pk>/delete/', AdminBookingDeleteView.as_view(), name='admin-booking-delete'),
]
