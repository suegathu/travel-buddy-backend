import requests
import qrcode
import logging
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Flight, FlightBooking
from .serializers import FlightSerializer, FlightBookingSerializer
from django.contrib.auth.models import AnonymousUser
from rest_framework.exceptions import AuthenticationFailed
import random 
from rest_framework import permissions
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Aviationstack API key
AVIATIONSTACK_API_KEY = os.getenv('AVIATIONSTACK_API_KEY')
API_URL = "http://api.aviationstack.com/v1/flights"

# ✈️ List All Flights
class FlightListView(generics.ListAPIView):
    queryset = Flight.objects.all()
    serializer_class = FlightSerializer

# ✈️ Fetch Flights from Aviationstack API and Save to Database
@api_view(['GET'])
def fetch_flights(request):
    if not AVIATIONSTACK_API_KEY:
        return Response({"error": "Missing API key"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # TODO: Add error handing if query params are missing
    response = requests.get(API_URL, params={
        # 'flight_status': 'scheduled',
        'access_key': AVIATIONSTACK_API_KEY,
        'dep_iata': request.query_params.get('dep_iata'),
        'arr_iata': request.query_params.get('arr_iata'),
    })

    if response.status_code != 200:
        logger.error(f"Failed to fetch flights: {response.text}")
        return Response({"error": "Failed to fetch flights"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    data = response.json().get("data", [])

    if not data:
        return Response({"error": "No flight data received"}, status=status.HTTP_404_NOT_FOUND)

    # Process each flight from the API
    for flight_data in data:
        flight_number = flight_data.get("flight", {}).get("iata", "")
        airline = flight_data.get("airline", {}).get("name") or "Unknown Airline"
        origin = flight_data.get("departure", {}).get("airport", "")
        destination = flight_data.get("arrival", {}).get("airport", "")
        departure_time = flight_data.get("departure", {}).get("estimated", "")
        arrival_time = flight_data.get("arrival", {}).get("estimated", "")
        available_seats = 100
        
        # Generate a random price between $150 and $800
        price = round(random.uniform(150.00, 800.00), 2)

        if not arrival_time:
            arrival_time = "1970-01-01T00:00:00Z"

        if flight_number and origin and destination:
            # Use update_or_create instead of get_or_create to ensure price updates on existing records
            flight, created = Flight.objects.update_or_create(
                flight_number=flight_number,
                defaults={
                    "airline": airline,
                    "origin": origin,
                    "destination": destination,
                    "departure_time": departure_time,
                    "arrival_time": arrival_time,
                    "available_seats": available_seats,
                    "price": price,
                },
            )
            
            # Debug log to confirm price was set correctly
            logger.debug(f"Flight {flight_number} {'created' if created else 'updated'} with price: {price}")

    flights = Flight.objects.all()
    serializer = FlightSerializer(flights, many=True)
    return Response(serializer.data)

# 🎟️ Book a Flight
@api_view(['POST'])
def book_flight(request):
    if not request.user.is_authenticated:  # Check if the user is authenticated
        raise AuthenticationFailed("You must be logged in to book a flight.")

    flight_number = request.data.get("flight_number")
    seat_number = request.data.get("seat_number")

    flight = get_object_or_404(Flight, flight_number=flight_number)

    # TODO: Confirm that the flight has the given seat

    if flight.available_seats <= 0:
        return Response({"error": "No seats available"}, status=status.HTTP_400_BAD_REQUEST)

    # Prevent duplicate seat bookings
    if FlightBooking.objects.filter(flight=flight, seat_number=seat_number).exists():
        return Response({"error": "Seat already booked"}, status=status.HTTP_400_BAD_REQUEST)

    # Create booking
    booking = FlightBooking.objects.create(
        user=request.user,  # Now we are sure request.user is authenticated
        flight=flight,
        seat_number=seat_number,
        status="pending"
    )

    # Reduce available seats
    flight.available_seats -= 1
    flight.save()

    # Generate QR Code
    qr_content = f"Booking ID: {booking.id} - Flight: {flight.flight_number}"
    qr = qrcode.make(qr_content)
    qr_io = BytesIO()
    qr.save(qr_io, format="PNG")
    booking.qr_code.save(f"{booking.id}.png", ContentFile(qr_io.getvalue()), save=True)

    # Send Email Confirmation
    send_mail(
        "Your Flight Booking Confirmation",
        f"Hello {request.user.username},\nYour flight booking is confirmed.\nBooking ID: {booking.id}\nFlight: {flight.flight_number}\nSeat: {seat_number}",
        settings.DEFAULT_FROM_EMAIL,
        [request.user.email],
        fail_silently=False,
    )

    serializer = FlightBookingSerializer(booking)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# ✅ Verify QR Code at the AirportFav
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_qr_code(request, booking_id):
    booking = get_object_or_404(FlightBooking, id=booking_id)

    if booking.status == 'checked_in':
        return Response({"message": "Passenger already checked in."}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "message": "Valid QR Code",
        "booking_id": booking.id,
        "flight_number": booking.flight.flight_number,
        "passenger": booking.user.username,
        "seat": booking.seat_number,
        "status": booking.status
    }, status=status.HTTP_200_OK)

# 🎟️ Check-in Flight
@api_view(['GET'])
def check_in_flight(request, booking_id):
    booking = get_object_or_404(FlightBooking, id=booking_id)

    if booking.status == 'checked_in':
        return Response({"message": "Passenger already checked in."}, status=status.HTTP_400_BAD_REQUEST)

    booking.status = 'checked_in'
    booking.save()

    return Response({
        "message": "Check-in successful!",
        "booking_status": booking.status
    }, status=status.HTTP_200_OK)

from rest_framework.renderers import JSONRenderer

@api_view(['GET'])
@renderer_classes([JSONRenderer])  # ✅ Ensure JSON response
def get_available_seats(request, flight_number):
    flight = get_object_or_404(Flight, flight_number=flight_number)
    booked_seats = list(FlightBooking.objects.filter(flight=flight).values_list('seat_number', flat=True))

    print("booked seats", booked_seats)

    ALL_SEATS = [f"{i}" for i in range(1, 101)]
    available_seats = [seat for seat in ALL_SEATS if seat not in booked_seats]


    return Response({"available_seats": available_seats}, status=status.HTTP_200_OK)
@api_view(['GET'])
def get_booking_details(request, booking_id):
    booking = get_object_or_404(FlightBooking, id=booking_id)
    return Response({
        "id": booking.id,
        "flight": booking.flight.flight_number,
        "seat": booking.seat_number,
        "status": booking.status,
        "qr_code_url": booking.qr_code.url if booking.qr_code else None
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_flight_bookings(request):
    bookings = FlightBooking.objects.filter(user=request.user)
    serializer = FlightBookingSerializer(bookings, many=True)
    return Response({'results': serializer.data})

@api_view(['DELETE'])
@permission_classes([permissions.IsAdminUser])
def admin_cancel_flight_booking(request, booking_id):
    """
    Delete a flight booking
    For admin use only.
    """
    try:
        booking = get_object_or_404(FlightBooking, id=booking_id)
        
        # Increment available seats when deleting a booking
        flight = booking.flight
        flight.available_seats += 1
        flight.save()
        
        # Store booking details for response
        booking_data = FlightBookingSerializer(booking).data
        
        # Delete the booking
        booking.delete()
        
        return Response({
            "message": "Booking deleted successfully", 
            "booking": booking_data
        })
    
    except Exception as e:
        logger.error(f"Error deleting booking {booking_id}: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['GET'])
@renderer_classes([JSONRenderer])  # ✅ Ensure JSON response
def get_flight_details(request, flight_number):
    flight = get_object_or_404(Flight, flight_number=flight_number)
    
    # Get bookings for this flight to show seat reservations
    bookings = FlightBooking.objects.filter(flight=flight)
    seat_reservations = {}
    
    for booking in bookings:
        if booking.seat_number:
            # Get user information
            user_name = "Unknown"
            if booking.user:
                user_name = booking.user.get_full_name() or booking.user.username
            
            seat_reservations[booking.seat_number] = {
                'user': user_name,
                'status': booking.status,
                'booking_id': booking.id
            }
    
    # Get all booked seats as a list
    booked_seats = list(bookings.values_list('seat_number', flat=True))
    
    # Calculate available seats
    ALL_SEATS = [f"{i}" for i in range(1, 101)]
    available_seats = [seat for seat in ALL_SEATS if seat not in booked_seats]
    
    # Create response with both flight details and seat information
    response_data = {
        "flight_details": {
            "flight_number": flight.flight_number,
            "airline": flight.airline,
            "origin": flight.origin,
            "destination": flight.destination,
            "departure_time": flight.departure_time,
            "arrival_time": flight.arrival_time,
            "price": str(flight.price),
            "total_seats": 100,
            "available_seats_count": len(available_seats)
        },
        "available_seats": available_seats,
        "seat_reservations": seat_reservations
    }
    
    return Response(response_data, status=status.HTTP_200_OK)    

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Count
from .models import Flight
from .serializers import FlightSerializer

class AdminFlightListCreateView(generics.ListCreateAPIView):
    """
    List all flights or create a new flight.
    For admin use only.
    """
    queryset = Flight.objects.all().order_by('-departure_time')
    serializer_class = FlightSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        """
        Optionally filter flights by query parameters
        """
        queryset = Flight.objects.all().order_by('-departure_time')
        airline = self.request.query_params.get('airline')
        origin = self.request.query_params.get('origin')
        destination = self.request.query_params.get('destination')
        flight_number = self.request.query_params.get('flight_number')
        
        if airline:
            queryset = queryset.filter(airline__icontains=airline)
        if origin:
            queryset = queryset.filter(origin__icontains=origin)
        if destination:
            queryset = queryset.filter(destination__icontains=destination)
        if flight_number:
            queryset = queryset.filter(flight_number__icontains=flight_number)
            
        return queryset

class AdminFlightRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update a flight.
    For admin use only.
    """
    queryset = Flight.objects.all()
    serializer_class = FlightSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'id'

class AdminFlightDeleteView(generics.DestroyAPIView):
    """
    Delete a flight.
    For admin use only.
    """
    queryset = Flight.objects.all()
    serializer_class = FlightSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'id'

class AdminFlightStatsView(generics.GenericAPIView):
    """
    Retrieve statistics about flights.
    For admin use only.
    """
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request, *args, **kwargs):
        total_flights = Flight.objects.count()
        upcoming_flights = Flight.objects.filter(departure_time__gt=timezone.now()).count()
        
        # Get airlines and their flight counts - using flight_number instead of id
        airline_stats = Flight.objects.values('airline').annotate(count=Count('flight_number')).order_by('-count')
        
        # Get most popular routes - using flight_number instead of id
        routes = Flight.objects.values('origin', 'destination').annotate(count=Count('flight_number')).order_by('-count')[:5]
        
        return Response({
            'total_flights': total_flights,
            'upcoming_flights': upcoming_flights,
            'airline_stats': airline_stats,
            'popular_routes': routes
        })
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from .models import FlightBooking, Flight
from .serializers import FlightBookingSerializer
import logging

logger = logging.getLogger(__name__)

class AdminFlightBookingListView(generics.ListAPIView):
    """
    List all flight bookings
    For admin use only.
    """
    permission_classes = [permissions.IsAdminUser]
    serializer_class = FlightBookingSerializer
    
    def get_queryset(self):
        """
        Optionally filter flight bookings by query parameters
        """
        queryset = FlightBooking.objects.all().order_by('-created_at')
        status = self.request.query_params.get('status')
        flight_number = self.request.query_params.get('flight_number')
        user_id = self.request.query_params.get('user_id')
        
        if status:
            queryset = queryset.filter(status=status)
        if flight_number:
            queryset = queryset.filter(flight__flight_number=flight_number)
        if user_id:
            queryset = queryset.filter(user__id=user_id)
            
        return queryset
    
    def list(self, request, *args, **kwargs):
        # Use the serializer directly and let it handle all the field mappings
        # This avoids manual field population that could cause inconsistencies
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

@api_view(['PATCH'])
@permission_classes([permissions.IsAdminUser])
def admin_update_flight_booking(request, booking_id):
    """
    Update the status of a flight booking
    For admin use only.
    """
    booking = get_object_or_404(FlightBooking, id=booking_id)
    
    # Only update specific fields
    if 'status' in request.data:
        booking.status = request.data['status']
        booking.save()
    
    serializer = FlightBookingSerializer(booking)
    return Response(serializer.data)

@api_view(['PATCH'])  # Ensure PATCH is included
@permission_classes([IsAuthenticated])
def cancel_flight_booking(request, booking_id):
    print(f"DEBUG: Reached cancel view for {booking_id}, user: {request.user}")
    try:
        # Get the booking object
        booking = FlightBooking.objects.get(id=booking_id, user=request.user)

        # Update the booking status to 'canceled'
        booking.status = 'canceled'
        booking.save()

        # Serialize the booking data to return in the response
        serializer = FlightBookingSerializer(booking)

        return Response({"message": "Booking canceled successfully", "booking": serializer.data}, status=status.HTTP_200_OK)

    except FlightBooking.DoesNotExist:
        return Response({"error": "Booking not found or you don't have permission to cancel this booking."},
                        status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AdminFlightBookingStatsView(generics.GenericAPIView):
    """
    Retrieve statistics about flight bookings
    For admin use only.
    """
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request, *args, **kwargs):
        total_bookings = FlightBooking.objects.count()
        confirmed_bookings = FlightBooking.objects.filter(status='confirmed').count()
        pending_bookings = FlightBooking.objects.filter(status='pending').count()
        checked_in_bookings = FlightBooking.objects.filter(status='checked_in').count()
        cancelled_bookings = FlightBooking.objects.filter(status='cancelled').count()
        
        # Calculate total revenue from confirmed bookings
        total_revenue = 0
        for booking in FlightBooking.objects.filter(status__in=['confirmed', 'checked_in']):
            total_revenue += booking.flight.price
        
        return Response({
            'total_bookings': total_bookings,
            'confirmed_bookings': confirmed_bookings,
            'pending_bookings': pending_bookings,
            'checked_in_bookings': checked_in_bookings,
            'cancelled_bookings': cancelled_bookings,
            'total_revenue': total_revenue
        })    