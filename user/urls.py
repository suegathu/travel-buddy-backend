from django.urls import path
from .views import (
    RegisterView,
    UserProfileView,
    LogoutView,
    SingleUserView,
    AllUsersView,
    ChangePasswordView
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # Admin-only views
    path('admin/users/', AllUsersView.as_view(), name='all_users'),
    path('admin/users/<int:pk>/', SingleUserView.as_view(), name='single_user'),

    path("change-password/", ChangePasswordView.as_view(), name="change-password"),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
