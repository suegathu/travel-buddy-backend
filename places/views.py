from rest_framework import generics, permissions, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from datetime import timedelta
import requests
import random
import math
import django_filters

from .models import Place, Booking
from .serializers import PlaceSerializer, BookingSerializer, AdminBookingSerializer

import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Access the Pexels API key from the environment
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')

CACHE_EXPIRY_DAYS = 7

# Default restaurant images dictionary
DEFAULT_RESTAURANT_IMAGES = {
    'generic': [
        "https://www.google.com/url?sa=i&url=https%3A%2F%2Fcommons.wikimedia.org%2Fwiki%2FFile%3AIsland_Shangri-La%2C_Hong_Kong_-_Restaurant_Petrus.png&psig=AOvVaw0PKgHdo4lTa5BCEYm0ezup&ust=1744878681962000&source=images&cd=vfe&opi=89978449&ved=0CBEQjRxqFwoTCPCn_u6R3IwDFQAAAAAdAAAAABAE",
        "https://www.google.com/url?sa=i&url=https%3A%2F%2Fwww.pexels.com%2Fsearch%2Frestaurant%2F&psig=AOvVaw0PKgHdo4lTa5BCEYm0ezup&ust=1744878681962000&source=images&cd=vfe&opi=89978449&ved=0CBEQjRxqFwoTCPCn_u6R3IwDFQAAAAAdAAAAABAJ",
        "https://www.google.com/url?sa=i&url=https%3A%2F%2Funsplash.com%2Fs%2Fphotos%2Frestaurant&psig=AOvVaw0PKgHdo4lTa5BCEYm0ezup&ust=1744878681962000&source=images&cd=vfe&opi=89978449&ved=0CBEQjRxqFwoTCPCn_u6R3IwDFQAAAAAdAAAAABAQ",
        "https://www.google.com/imgres?imgurl=https%3A%2F%2Fmedia.istockphoto.com%2Fid%2F1316145932%2Fphoto%2Ftable-top-view-of-spicy-food.jpg%3Fs%3D612x612%26w%3D0%26k%3D20%26c%3DeaKRSIAoRGHMibSfahMyQS6iFADyVy1pnPdy1O5rZ98%3D&tbnid=2PUwJ0bMDRqiBM&vet=10CAoQxiAoCWoXChMI8Kf-7pHcjAMVAAAAAB0AAAAAEBU..i&imgrefurl=https%3A%2F%2Fwww.istockphoto.com%2Fphotos%2Ffood-and-drink-table&docid=aAdn_QbINBA8IM&w=612&h=408&itg=1&q=restaurant%20image%20png&ved=0CAoQxiAoCWoXChMI8Kf-7pHcjAMVAAAAAB0AAAAAEBU",
        "https://www.google.com/url?sa=i&url=https%3A%2F%2Flgbtqsd.news%2Fcallie-a-mediterranean-feast%2F&psig=AOvVaw0PKgHdo4lTa5BCEYm0ezup&ust=1744878681962000&source=images&cd=vfe&opi=89978449&ved=0CBEQjRxqFwoTCPCn_u6R3IwDFQAAAAAdAAAAABAe",
        "https://www.google.com/url?sa=i&url=https%3A%2F%2Fwww.sandiegoreader.com%2Fnews%2F2022%2Fjun%2F24%2Ffeast-callie-michelin-bib-comes-east-village%2F&psig=AOvVaw0PKgHdo4lTa5BCEYm0ezup&ust=1744878681962000&source=images&cd=vfe&opi=89978449&ved=0CBEQjRxqFwoTCPCn_u6R3IwDFQAAAAAdAAAAABAl"
    ],
    # You could add categories and specific URLs if needed
    # 'italian': ["URL_TO_ITALIAN_RESTAURANT_1", "URL_TO_ITALIAN_RESTAURANT_2"],
    # 'seafood': ["URL_TO_SEAFOOD_RESTAURANT_1"],
}

# Category tags for OSM queries
CATEGORY_TAGS = {
    'hotel': [('tourism', 'hotel'), ('building', 'hotel')],
    'restaurant': [('amenity', 'restaurant'), ('tourism', 'restaurant')],
    'attraction': [('tourism', 'attraction'), ('leisure', 'park')],
}

# Helper functions
def haversine(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on Earth."""
    R = 6371  # Earth radius in kilometers
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_image_url(query, category='travel'):
    """Get an image URL from Pexels API with fallback options."""
    if category == 'restaurant':
        # Randomly select from the 'generic' list of default restaurant images
        return random.choice(DEFAULT_RESTAURANT_IMAGES.get('generic', [""]))

    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": 1}
    print(f"📸 Querying Pexels for: {query} | Category: {category}")

    try:
        res = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params)
        data = res.json()
        if data.get('photos'):
            return data['photos'][0]['src']['medium']
    except Exception as e:
        print(f"⚠️ Primary Pexels error: {e}")

    # Fallback options if primary search fails
    fallback_keywords = {
        'hotel': ['luxury hotel', 'resort', 'hotel room'],
        'restaurant': ['restaurant interior', 'fine dining', 'cafe exterior', 'gourmet food', 'restaurant building'],
        'attraction': ['landmark', 'tourist attraction', 'monument', 'famous building'],
        'travel': ['adventure', 'vacation', 'scenic view']
    }

    fallback_query = random.choice(fallback_keywords.get(category, ['travel']))

    try:
        res = requests.get("https://api.pexels.com/v1/search", headers=headers, params={"query": fallback_query, "per_page": 1})
        fallback_data = res.json()
        if fallback_data.get('photos'):
            return fallback_data['photos'][0]['src']['medium']
    except Exception as e:
        print(f"⚠️ Fallback Pexels error: {e}")

    return ''

def get_city_bbox_from_nominatim(city_name):
    """Get bounding box coordinates for a city using Nominatim."""
    try:
        res = requests.get("https://nominatim.openstreetmap.org/search", params={
            "q": city_name,
            "format": "json",
            "limit": 1
        }, headers={"User-Agent": "TravelCompanionApp/1.0"})
        res.raise_for_status()
        data = res.json()

        if data:
            bbox = data[0]["boundingbox"]
            return {
                "south": float(bbox[0]),
                "north": float(bbox[1]),
                "west": float(bbox[2]),
                "east": float(bbox[3])
            }
    except Exception as e:
        print(f"❌ Error getting city bounding box: {e}")

    return None

# Filter definitions
class PlaceFilter(django_filters.FilterSet):
    city = django_filters.CharFilter(field_name='city', lookup_expr='icontains')
    place_type = django_filters.CharFilter(field_name='place_type', lookup_expr='exact')
    type = django_filters.CharFilter(field_name='place_type', lookup_expr='exact')  # Alias for place_type
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model = Place
        fields = ['city', 'place_type', 'name']

# Pagination classes
class PlaceResultsPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

# API Views
class PlaceListView(generics.ListAPIView):
    serializer_class = PlaceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_class = PlaceFilter
    search_fields = ['name', 'city', 'place_type']
    pagination_class = None

    def get_queryset(self):
        """Apply filters and ensure consistent ordering."""
        # Start with ordered base queryset
        queryset = Place.objects.all().order_by('id')

        # Handle both 'type' and 'place_type' parameters
        place_type = self.request.query_params.get('type') or self.request.query_params.get('place_type')
        if place_type:
            print(f"Filtering by place_type: {place_type}")
            queryset = queryset.filter(place_type__iexact=place_type)

        # Apply city filter if provided
        city = self.request.query_params.get('city')
        if city:
            print(f"Filtering by city: {city}")
            queryset = queryset.filter(city__icontains=city)

        # Check if we need to refresh data
        refresh = self.request.query_params.get('refresh', 'false').lower() == 'true'
        if refresh and place_type and (city or self.request.query_params.get('lat')):
            # If refresh is requested and we have location info, try to get fresh data
            try:
                self._refresh_place_data(place_type, city)
                # Re-query to get fresh data
                queryset = Place.objects.all().order_by('id')
                if place_type:
                    queryset = queryset.filter(place_type__iexact=place_type)
                if city:
                    queryset = queryset.filter(city__icontains=city)
            except Exception as e:
                print(f"Error refreshing data: {e}")
                # Continue with existing data
                pass

        print(f"Query returned {queryset.count()} places")
        return queryset


    def _refresh_place_data(self, place_type, city=None):
        """Internal method to refresh place data from external sources."""
        print(f"Attempting to refresh {place_type} data for {city or 'unknown location'}")

        # Get bounding box if city provided
        bbox = None
        if city:
            bbox = get_city_bbox_from_nominatim(city)
            if not bbox:
                print(f"Could not get bbox for city: {city}")
                return
        else:
            # Would need lat/lon params here in a real implementation
            return

        # Get tags for OSM query
        tags = CATEGORY_TAGS.get(place_type, [('tourism', place_type)])

        # Construct Overpass query
        query_parts = []
        for key, value in tags:
            query_parts.append(f"""
                node["{key}"="{value}"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
                way["{key}"="{value}"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
            """)
        query = f"[out:json];({''.join(query_parts)});out center;"

        # Execute query and process results
        try:
            osm_res = requests.get("https://overpass-api.de/api/interpreter", params={"data": query})
            osm_res.raise_for_status()
            elements = osm_res.json().get("elements", [])
            print(f"Found {len(elements)} OSM elements")

            now = timezone.now()
            created_count = 0
            updated_count = 0

            for el in elements:
                tags = el.get("tags", {})
                name = tags.get("name", "Unnamed")
                lat = el.get("lat") or el.get("center", {}).get("lat")
                lon = el.get("lon") or el.get("center", {}).get("lon")
                address = tags.get("addr:full") or tags.get("addr:street", "")

                if not lat or not lon:
                    continue

                # Check if place exists by location
                existing_places = Place.objects.filter(
                    place_type=place_type,
                    latitude__range=(lat - 0.0001, lat + 0.0001),
                    longitude__range=(lon - 0.0001, lon + 0.0001)
                )

                image_url = ""
                if place_type == 'restaurant':
                    image_url = random.choice(DEFAULT_RESTAURANT_IMAGES.get('generic', [""]))
                else:
                    image_url = get_image_url(f"{name} {place_type}", place_type)

                price = round(random.uniform(10, 500), 2)

                if existing_places.exists():
                    # Update existing place
                    place = existing_places.first()
                    if place.name != name and name != "Unnamed":
                        place.name = name
                    if place.address != address and address:
                        place.address = address
                    place.last_updated = now
                    place.image_url = image_url # Force update image URL even if it exists
                    place.price = price # Force update price
                    place.save()
                    updated_count += 1
                else:
                    # Create new place
                    Place.objects.create(
                        name=name,
                        latitude=lat,
                        longitude=lon,
                        address=address,
                        place_type=place_type,
                        city=city,
                        image_url=image_url,
                        last_updated=now,
                        price=price
                    )
                    created_count += 1

            print(f"Created {created_count} new places, updated {updated_count} existing places")

        except Exception as e:
            print(f"Error fetching/processing OSM data: {e}")
            raise

class PlaceDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Place.objects.all()
    serializer_class = PlaceSerializer
    permission_classes = [permissions.IsAuthenticated]

class BookingCreateView(generics.CreateAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class AdminBookingListUpdateView(generics.ListAPIView):
    queryset = Booking.objects.all().order_by('-booking_date')
    serializer_class = AdminBookingSerializer
    permission_classes = [permissions.IsAdminUser]

class AdminBookingUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Booking.objects.all()
    serializer_class = AdminBookingSerializer
    permission_classes = [permissions.IsAdminUser]

class UserBookingsListAPIView(generics.ListAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).order_by('-booking_date')
    
# views.py
from rest_framework import generics, permissions
from .models import Booking
from .serializers import BookingDetailSerializer

class UserBookingDetailAPIView(generics.RetrieveAPIView):
    serializer_class = BookingDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Ensures user can only retrieve their own bookings
        return Booking.objects.filter(user=self.request.user)
   