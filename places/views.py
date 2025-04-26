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
from rest_framework import generics, permissions
from .models import Place, Booking
from .serializers import PlaceSerializer, BookingSerializer, AdminBookingSerializer, BookingDetailSerializer
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly

import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Access the Pexels API key from the environment
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')

CACHE_EXPIRY_DAYS = 7

# Default image for consistent fallback
DEFAULT_PLACE_IMAGE = 'https://images.pexels.com/photos/6267/menu-restaurant-vintage-table.jpg'

# Category tags for OSM queries
CATEGORY_TAGS = {
    'hotel': [('tourism', 'hotel'), ('building', 'hotel')],
    'restaurant': [('amenity', 'restaurant'), ('tourism', 'restaurant')],
    'attraction': [('tourism', 'attraction'), ('leisure', 'park')],
}

# Price range configuration by place type
PRICE_RANGES = {
    'hotel': (50, 500),  # Hotels: $50-$500
    'restaurant': (10, 100),  # Restaurants: $10-$100
    'attraction': (5, 50),  # Attractions: $5-$50
    'default': (10, 200)  # Default range for any other type
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

def generate_random_price(place_type):
    """Generate a random price based on place type."""
    min_price, max_price = PRICE_RANGES.get(place_type.lower(), PRICE_RANGES['default'])
    return round(random.uniform(min_price, max_price), 2)

def generate_random_rating():
    """Generate a random rating between 1.0 and 5.0."""
    # Skew towards higher ratings (more realistic)
    # Higher probability for ratings between 3.5-4.8
    base_rating = random.uniform(2.5, 5.0)
    # Apply some variance, but keep within 1-5 range
    final_rating = min(5.0, max(1.0, base_rating + random.uniform(-0.5, 0.3)))
    return round(final_rating, 1)

def get_image_url(query, category='travel'):
    """Get an image URL from Pexels API with fallback options."""
    # Try Pexels API for category
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": 1}
    print(f"📸 Querying Pexels for: {query} | Category: {category}")

    # First, check if we should use default image to reduce API calls
    if not PEXELS_API_KEY or random.random() < 0.2:  # 20% chance to use default to reduce API load
        return DEFAULT_PLACE_IMAGE

    try:
        res = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params, timeout=3)
        if res.status_code == 200:
            data = res.json()
            if data.get('photos'):
                return data['photos'][0]['src']['medium']
            print(f"⚠️ No photos found for query: {query}")
        else:
            print(f"⚠️ Pexels API returned status code {res.status_code}")
    except requests.exceptions.Timeout:
        print(f"⚠️ Pexels API timeout for query: {query}")
        return DEFAULT_PLACE_IMAGE
    except Exception as e:
        print(f"⚠️ Primary Pexels error: {e}")
        return DEFAULT_PLACE_IMAGE  # Return default immediately on any error

    # Use simpler fallback approach to reduce API calls
    fallback_keywords = {
        'hotel': ['luxury hotel', 'hotel room'],
        'restaurant': ['restaurant', 'dining'],
        'attraction': ['attraction', 'landmark'],
        'travel': ['travel', 'vacation']
    }
    
    # Only try one fallback with short timeout
    try:
        fallback_query = random.choice(fallback_keywords.get(category, ['travel']))
        print(f"🔄 Trying fallback query: {fallback_query}")
        
        res = requests.get("https://api.pexels.com/v1/search", 
                          headers=headers, 
                          params={"query": fallback_query, "per_page": 1}, 
                          timeout=2)  # Shorter timeout for fallback
        
        if res.status_code == 200:
            fallback_data = res.json()
            if fallback_data.get('photos'):
                return fallback_data['photos'][0]['src']['medium']
    except Exception:
        pass  # Silently fail on fallback
    
    # Last resort placeholder
    return DEFAULT_PLACE_IMAGE

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
        if refresh and (place_type or city or self.request.query_params.get('lat')):
            try:
                if place_type:
                    self._refresh_place_data(place_type, city)
                else:
                    for pt in CATEGORY_TAGS.keys():
                        self._refresh_place_data(pt, city)
                
                queryset = Place.objects.all().order_by('id')
                if place_type:
                    queryset = queryset.filter(place_type__iexact=place_type)
                if city:
                    queryset = queryset.filter(city__icontains=city)
            except Exception as e:
                print(f"Error refreshing data: {e}")

        # For places with no price or rating, generate and save them
        for place in queryset.all():  # Use .all() to evaluate the query once
            updated = False
            if place.price is None or place.price == 0:
                place.price = generate_random_price(place.place_type)
                updated = True
            if place.rating is None or place.rating == 0:
                place.rating = generate_random_rating()
                updated = True
            if place.image_url is None or place.image_url == "":
                if place.place_type == 'restaurant':
                    cuisine = getattr(place, 'cuisine', 'food')
                    search_term = f"{cuisine} restaurant food"
                else:
                    search_term = f"{place.name} {place.place_type}"
                place.image_url = get_image_url(search_term, place.place_type)
                updated = True
            if updated:
                place.save()

        # Get count for logging
        result_count = queryset.count()
        print(f"Query returned {result_count} places")
        
        # Apply price filters in memory to preserve the QuerySet
        filters_min_price = self.request.query_params.get('minPrice')
        filters_max_price = self.request.query_params.get('maxPrice')
        
        # We'll store need_filter flag to know if we need client-side filtering
        need_filter = False
        min_price = None
        max_price = None
        
        if filters_min_price:
            try:
                min_price = float(filters_min_price)
                need_filter = True
            except ValueError:
                pass
                
        if filters_max_price:
            try:
                max_price = float(filters_max_price)
                need_filter = True
            except ValueError:
                pass

        # Log the limit (but don't apply it yet)
        limit = self.request.query_params.get('limit')
        try:
            limit = int(limit) if limit is not None else 10
            print(f"Will limit results to {limit} places")
        except ValueError:
            limit = 10
            print("Invalid limit parameter, defaulting to 10.")
        
        # Return the queryset (still a QuerySet object, not a list)
        # This will be further processed by the filter backends
        return queryset

def filter_queryset(self, queryset):
    """Override filter_queryset to handle price filtering and limiting after other filters"""
    # Apply standard filter backends first (will preserve QuerySet)
    queryset = super().filter_queryset(queryset)
    
    # Now apply manual price filtering if needed
    filters_min_price = self.request.query_params.get('minPrice')
    filters_max_price = self.request.query_params.get('maxPrice')
    
    if filters_min_price:
        try:
            min_price = float(filters_min_price)
            queryset = queryset.filter(price__gte=min_price)
        except ValueError:
            pass
            
    if filters_max_price:
        try:
            max_price = float(filters_max_price)
            queryset = queryset.filter(price__lte=max_price)
        except ValueError:
            pass
    
    # Apply limit at the very end, only for the final result
    limit = self.request.query_params.get('limit')
    try:
        limit = int(limit) if limit is not None else 10
    except ValueError:
        limit = 10
    
    # Now we can safely slice, as this is the last operation
    return queryset[:limit]

    def _refresh_place_data(self, place_type, city=None):
        """Internal method to refresh place data from external sources."""
        print(f"Attempting to refresh {place_type} data for {city or 'unknown location'}")

        # Limit refreshes to prevent overload
        MAX_RECORDS_TO_PROCESS = 15  # Process max 15 places per request
        
        # City bounding box overrides (centered downtown areas)
        CITY_BBOX_OVERRIDES = {
            "new york": {"south": 40.70, "north": 40.75, "west": -74.01, "east": -73.97},
            "toronto": {"south": 43.64, "north": 43.66, "west": -79.39, "east": -79.37},
        }

        bbox = None
        if city:
            city_lower = city.strip().lower()
            if city_lower in CITY_BBOX_OVERRIDES:
                bbox = CITY_BBOX_OVERRIDES[city_lower]
                print(f"Using custom bounding box for {city}")
            else:
                try:
                    bbox = get_city_bbox_from_nominatim(city)
                except Exception as e:
                    print(f"Error getting city bbox: {e}")
                    return
                    
                if not bbox:
                    print(f"Could not get bbox for city: {city}")
                    return

                # Shrink large bounding boxes to reduce Overpass load
                lat_range = float(bbox["north"]) - float(bbox["south"])
                lon_range = float(bbox["east"]) - float(bbox["west"])
                if lat_range > 0.3 or lon_range > 0.3:
                    print("Shrinking large bounding box")
                    shrink_factor = 0.05
                    bbox["south"] = float(bbox["south"]) + shrink_factor
                    bbox["north"] = float(bbox["north"]) - shrink_factor
                    bbox["west"] = float(bbox["west"]) + shrink_factor
                    bbox["east"] = float(bbox["east"]) - shrink_factor
        else:
            return  # No location info

        tags = CATEGORY_TAGS.get(place_type, [('tourism', place_type)])

        # Build Overpass query
        query_parts = []
        for key, value in tags:
            query_parts.append(f"""
                node["{key}"="{value}"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
                way["{key}"="{value}"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
            """)
        query = f"[out:json];({''.join(query_parts)});out center;"

        try:
            osm_res = requests.get("https://overpass-api.de/api/interpreter", params={"data": query}, timeout=10)
            osm_res.raise_for_status()
            elements = osm_res.json().get("elements", [])
            print(f"Found {len(elements)} OSM elements")

            # Limit processing to prevent timeout
            if len(elements) > MAX_RECORDS_TO_PROCESS:
                print(f"Limiting processing to {MAX_RECORDS_TO_PROCESS} elements")
                elements = elements[:MAX_RECORDS_TO_PROCESS]

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

                existing_places = Place.objects.filter(
                    place_type=place_type,
                    latitude__range=(lat - 0.0001, lat + 0.0001),
                    longitude__range=(lon - 0.0001, lon + 0.0001)
                )

                cuisine = tags.get("cuisine", "food")
                search_term = f"{name} {cuisine} {place_type}"
                
                # Generate random price and rating first
                price = generate_random_price(place_type)
                rating = generate_random_rating()
                
                # Only fetch new image if we don't have one already
                image_url = DEFAULT_PLACE_IMAGE
                if not existing_places.exists() or not existing_places.first().image_url:
                    image_url = get_image_url(search_term, place_type)

                if existing_places.exists():
                    place = existing_places.first()
                    if place.name != name and name != "Unnamed":
                        place.name = name
                    if place.address != address and address:
                        place.address = address
                    place.last_updated = now
                    # Only update image if we don't have one or it's default
                    if not place.image_url or place.image_url == DEFAULT_PLACE_IMAGE:
                        place.image_url = image_url
                    place.price = price
                    place.rating = rating
                    place.save()
                    updated_count += 1
                else:
                    Place.objects.create(
                        name=name,
                        latitude=lat,
                        longitude=lon,
                        address=address,
                        place_type=place_type,
                        city=city,
                        image_url=image_url,
                        last_updated=now,
                        price=price,
                        rating=rating
                    )
                    created_count += 1

            print(f"Created {created_count} new places, updated {updated_count} existing places")

        except requests.exceptions.Timeout:
            print("Timeout error when fetching OSM data")
        except Exception as e:
            print(f"Error fetching/processing OSM data: {e}")


class PlaceListCreateView(ListCreateAPIView):
    serializer_class = PlaceSerializer
    permission_classes = [IsAdminUser]  
    
    def get_queryset(self):
        queryset = Place.objects.all()
        city = self.request.query_params.get("city")
        type_ = self.request.query_params.get("type")
        local_only = self.request.query_params.get("local_only") == "true"
        
        if city:
            queryset = queryset.filter(city__iexact=city)
        if type_:
            queryset = queryset.filter(type__iexact=type_)
        if local_only:
            queryset = queryset.filter(osm_id__isnull=True)  
            
        return queryset
    
    def perform_create(self, serializer):
        # Track who added the place
        serializer.save(created_by=self.request.user)

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

class AdminBookingDeleteView(generics.DestroyAPIView):
    queryset = Booking.objects.all()
    serializer_class = AdminBookingSerializer
    permission_classes = [permissions.IsAdminUser]

class UserBookingsListAPIView(generics.ListAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).order_by('-booking_date')

class UserBookingDetailAPIView(generics.RetrieveAPIView):
    serializer_class = BookingDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Ensures user can only retrieve their own bookings
        return Booking.objects.filter(user=self.request.user)