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
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Aviationstack API key
AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
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
        # Whoops, you can't filter by date on the free plan
        # TODO: Fetch as many results as possibe using the limit param and then manually filter by date?
        # 'flight_date': request.query_params.get('flight_date'), # YYYY-MM-DD
        'dep_iata': request.query_params.get('dep_iata'),
        'arr_iata': request.query_params.get('arr_iata'),
    })

    if response.status_code != 200:
        logger.error(f"Failed to fetch flights: {response.text}")
        return Response({"error": "Failed to fetch flights"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    data = response.json().get("data", [])

    print(data)

    if not data:
        return Response({"error": "No flight data received"}, status=status.HTTP_404_NOT_FOUND)

    for flight_data in data:
        flight_number = flight_data.get("flight", {}).get("iata", "")
        airline = flight_data.get("airline", {}).get("name", "")
        origin = flight_data.get("departure", {}).get("airport", "")
        destination = flight_data.get("arrival", {}).get("airport", "")
        departure_time = flight_data.get("departure", {}).get("estimated", "")
        arrival_time = flight_data.get("arrival", {}).get("estimated", "")
        available_seats = 100  # Default value since Aviationstack doesn't provide this
        price = 200.00  # Default price

        if not arrival_time:
            arrival_time = "1970-01-01T00:00:00Z"  # Default value to prevent NULL error

        if flight_number and origin and destination:
            Flight.objects.get_or_create(
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

    flights = Flight.objects.all()
    serializer = FlightSerializer(flights, many=True)
    return Response(serializer.data)

# 🎟️ Book a Flight
@api_view(['POST'])
def book_flight(request):
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
        user=request.user,
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

    print(request.user)

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

    # TODO: Remove booked seats
    available_seats = [seat for seat in range(1, flight.available_seats + 1) if seat not in booked_seats]

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