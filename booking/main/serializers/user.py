from rest_framework import serializers
from main.models import *
from main.serializers.booking import BookingItemShortSerializer
from main.serializers.feeedback import FeedbackShortSerializer
from main.serializers.common import UserDataSerializer, CardSerializer
from main.rest import *
import datetime
from backend.services import *
from django.core.exceptions import *


randomService = DefaultRandomService()
kdfService = PbKdfService()

class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRole
        fields = (
            'id',
            'description',
            'can_create',
            'can_read',
            'can_update',
            'can_delete',
        )


class UserAccessCreateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    birth_date = serializers.DateField(write_only=True, required=False, allow_null=True)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    
    user_role = serializers.SlugRelatedField(
        slug_field = 'id',
        queryset = UserRole.objects.all()
    )

    class Meta:
        model = UserAccess
        fields = ('login', 'password', 'first_name','last_name', 'email', 'birth_date', 'user_role')
    
    def to_internal_value(self, data):
        return super().to_internal_value({
            'login': data.get('user-login'),
            'password': data.get('user-password'),
            'user_role': data.get('user-role'),
            'first_name': data.get('user-first-name'),
            'last_name': data.get('user-last-name'),
            'email': data.get('user-email'),
            'birth_date': data.get('user-birthdate') or None
        })
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        login = validated_data.pop('login')
        if UserAccess.objects.filter(login=login):
            raise ValidationError
       
        userData = UserData(
            first_name = validated_data.pop('first_name'), 
            last_name = validated_data.pop('last_name'),
            email = validated_data.pop('email'),
            birth_date = validated_data.pop('birth_date'),
            registered_at = datetime.datetime.now()
            )
        userData.save()
        salt = randomService.otp(12)
        dk = kdfService.dk(password, salt)

        userAccess = UserAccess(
            user_id = userData.id,
            login = login,
            salt = salt,
            dk = dk,
            user_data = userData,
            user_role = validated_data.pop('user_role')
        )
        userAccess.save()
        return userAccess
        
        

class UserAccessSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user_data.first_name")
    last_name = serializers.CharField(source="user_data.last_name")
    email = serializers.EmailField(source="user_data.email")
    birthdate = serializers.DateField(source="user_data.birth_date", allow_null=True)
    registeredAt = serializers.DateTimeField(source="user_data.registered_at")

    user_role = serializers.CharField(source="user_role.id")

    cards = CardSerializer(
        source="user_data.cards",
        many=True,
        read_only=True
    )

    bookingItems = BookingItemShortSerializer(
        source="booking_items",
        many=True,
        read_only=True
    )

    class Meta:
        model = UserAccess
        fields = (
            "id",
            "login",
            "user_role",
            "first_name",
            "last_name",
            "email",
            "birthdate",
            "registeredAt",
            "cards",
            "bookingItems",
        )

   