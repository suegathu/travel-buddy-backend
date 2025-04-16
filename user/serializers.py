from rest_framework import serializers
from .models import CustomUser
from django.contrib.auth import authenticate
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework.serializers import Serializer, CharField, ValidationError

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    password2 = serializers.CharField(write_only=True, required=False)
    profile_image = serializers.ImageField(use_url=True)
    created_at = serializers.DateTimeField(read_only=True)
    last_login = serializers.DateTimeField(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id", "username", "email", "first_name", "last_name", "bio",
            "profile_image", "is_client", "is_admin_user", "is_active",
            "created_at", "last_login", "password", "password2"
        ]
        read_only_fields = [
            "id", "is_client", "is_admin_user", "created_at", "last_login"
        ]

    def validate(self, data):
        password = data.get("password")
        password2 = data.get("password2")

        if password or password2:
            if password != password2:
                raise serializers.ValidationError("Passwords do not match.")
        return data

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        validated_data.pop("password2", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = CustomUser.objects.create_user(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Invalid credentials")

User = get_user_model()

class ChangePasswordSerializer(Serializer):
    old_password = CharField(required=True)
    new_password = CharField(required=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value
