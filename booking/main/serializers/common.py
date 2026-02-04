from rest_framework import serializers
from main.models import *

class CardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Card
        fields = (
            'id',
            'number',
            'cardholder_name',
            'expiration_date',
        )

class UserDataSerializer(serializers.ModelSerializer):
    cards = CardSerializer(many=True, read_only=True)

    class Meta:
        model = UserData
        fields = (
            'id',
            'first_name',
            'last_name',
            'email',
            'birth_date',
            'registered_at',
            'cards',
        )

class CommonUserAccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAccess
        fields = ("id", "login", "user_id")

class CommonRealtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Realty
        fields = ("id",)