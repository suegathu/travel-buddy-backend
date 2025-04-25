from django.urls import path
from .views import (
    FlightListView,
    book_flight,
    verify_qr_code,
    check_in_flight,
    fetch_flights,
    get_available_seats,
    get_booking_details,
    my_flight_bookings,
    cancel_flight_booking,
    download_booking_pdf,

    # Admin views
    AdminFlightDeleteView,
    AdminFlightListCreateView,
    AdminFlightRetrieveUpdateView,
    AdminFlightStatsView,
    AdminFlightBookingListView,
    admin_update_flight_booking,
    admin_cancel_flight_booking,
    AdminFlightBookingStatsView,
)

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [

    # === Public flight user routes ===
    path('flights/', FlightListView.as_view(), name='flight-list'),
    path('book-flight/', book_flight, name='book-flight'),
    path('verify-qr-code/<uuid:booking_id>/', verify_qr_code, name='verify-qr-code'),
    path('check-in-flight/<uuid:booking_id>/', check_in_flight, name='check-in-flight'),
    path('fetch-flights/', fetch_flights, name='fetch-flights'),
    path('flights/<str:flight_number>/available-seats/', get_available_seats, name='available-seats'),
    path('get-booking-details/<uuid:booking_id>/', get_booking_details, name='get-booking-details'),
    path('my-flight-bookings/', my_flight_bookings, name='my-flight-bookings'),
    path('cancel-flight-booking/<uuid:booking_id>/', cancel_flight_booking, name='cancel-flight-booking'),
    path('bookings/<str:booking_id>/download/', download_booking_pdf, name='download-booking-pdf'),

    # === Admin flight management ===
    path('admin/flights/', AdminFlightListCreateView.as_view(), name='admin-flight-list-create'),
    path('admin/flights/<int:id>/', AdminFlightRetrieveUpdateView.as_view(), name='admin-flight-detail-update'),
    path('admin/flights/<int:id>/delete/', AdminFlightDeleteView.as_view(), name='admin-flight-delete'),
    path('admin/flight-stats/', AdminFlightStatsView.as_view(), name='admin-flight-stats'),

    # === Admin flight bookings management ===
    path('admin/bookings/', AdminFlightBookingListView.as_view(), name='admin-flight-bookings'),
    path('admin/bookings/<uuid:booking_id>/update/', admin_update_flight_booking, name='admin-update-flight-booking'),
    path('admin/bookings/<uuid:booking_id>/delete/', admin_cancel_flight_booking, name='admin-cancel-flight-booking'),
    path('admin/booking-stats/', AdminFlightBookingStatsView.as_view(), name='admin-flight-booking-stats'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
