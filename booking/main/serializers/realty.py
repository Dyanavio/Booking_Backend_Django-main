from rest_framework import serializers
from main.models import *
#from main.serializers.user import UserDataSerializer
from main.serializers.feeedback import FeedbackSerializer, AccRatesSerializer
from main.serializers.location import CitySerializer
from main.serializers.booking import BookingItemSerializer
from django.urls import reverse
from django.conf import settings
from main.models import RealtyGroup # Import your group model


class RealtySearchSerializer(serializers.Serializer):
    Price = serializers.FloatField(required=False)
    Rating = serializers.IntegerField(required=False, min_value=0, max_value=5)
    Checkboxes = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    login = serializers.CharField(write_only=True, required=False)

class RealtyCreateSerializer(serializers.ModelSerializer):
    country = serializers.CharField(write_only=True)
    city = serializers.CharField(write_only=True)
    group = serializers.CharField(write_only=True)

    class Meta:
        model = Realty
        fields = (
            'name',
            'description',
            'slug',
            'price',
            'country',
            'city',
            'group',
        )

    def to_internal_value(self, data):
       mutable = data.copy()

       mutable['name'] = data.get('realty-name')
       mutable['description'] = data.get('realty-description')
       mutable['slug'] = data.get('realty-slug')
       mutable['price'] = data.get('realty-price')
       mutable['country'] = data.get('realty-country')
       mutable['city'] = data.get('realty-city')
       mutable['group'] = data.get('realty-group')

       return super().to_internal_value(mutable)

    def create(self, validated_data):
        country_name = validated_data.pop('country').strip()
        city_name = validated_data.pop('city').strip()
        group_name = validated_data.pop('group').strip()

        country, _ = Country.objects.get_or_create(
            name__iexact=country_name,
            defaults={'name': country_name}
        )

        city, _ = City.objects.get_or_create(
            name__iexact=city_name,
            country=country,
            defaults={
                'name': city_name,
                'country': country
            }
        )

        group, _ = RealtyGroup.objects.get_or_create(
            name__iexact=group_name,
            defaults={
                'name': group_name,
                'slug': group_name.lower().replace(' ', '-'),
                'description': group_name
            }
        )

        realty = Realty.objects.create(
            city=city,
            realty_group=group,
            **validated_data
        )

        return realty


class LikedRealtySearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = LikedRealty
        fields = (
            'id',
        )


class RealtySerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)
    group = serializers.CharField(source='realty_group.name', read_only=True)

    feedbacks = FeedbackSerializer(many=True, read_only=True)
    booking_items = BookingItemSerializer(many=True, read_only=True)

    images = serializers.SerializerMethodField()
    accRates = serializers.SerializerMethodField()

    liked = serializers.SerializerMethodField()

    class Meta:
        model = Realty
        fields = (
            'id',
            'name',
            'description',
            'slug',
            'price',
            'city',
            'group',
            'accRates',
            'feedbacks',
            'booking_items',
            'images',
            'liked'
        )

    def get_liked(self, obj):
        user_access = self.context.get("user_access")
        if not user_access:
            return "error"
        like_instance = obj.liked_by.filter(
            user_access=user_access
        ).first()

        if like_instance:
            return LikedRealtySearchSerializer(like_instance).data

        return None


    def get_images(self, obj):
        request = self.context.get("request")
        result = []

        for img in obj.images.all():
            url = f"{settings.SITE_URL}{reverse('storageItem', kwargs={'itemId': img.image_url})}"

            if request:
                url = request.build_absolute_uri(url)

            result.append({
                "imageUrl": url
            })

        return result


    def get_accRates(self, obj):
        avg = 0.0
        count = 0

        if hasattr(obj, "avg_rating") and obj.avg_rating is not None:
            avg = round(float(obj.avg_rating), 2)

        if hasattr(obj, "rates_count") and obj.rates_count is not None:
            count = int(obj.rates_count)

        return AccRatesSerializer({
            "avgRate": avg,
            "countRate": count
        }).data


class RealtyUpdateSerializer(serializers.ModelSerializer):
    data = serializers.DictField(write_only=True)
    realty_name = serializers.CharField(
        source='name',
        write_only=True,
        required=False
    )

    realty_description = serializers.CharField(
        source='description',
        write_only=True,
        required=False
    )

    realty_slug = serializers.SlugField(
        source='slug',
        write_only=True,
        required=False
    )

    realty_price = serializers.DecimalField(
        source='price',
        max_digits=10,
        decimal_places=2,
        write_only=True,
        required=False
    )

    realty_group = serializers.CharField(
        write_only=True,
        required=False
    )


    realty_city = serializers.CharField(
        write_only=True,
        required=False
    )

    realty_country = serializers.CharField(
        write_only=True,
        required=False
    )

    realty_deleted_at = serializers.DateField(
        write_only=True,
        required=False
    )

    class Meta:
        model = Realty
        fields = (
            'realty_name',
            'realty_description',
            'realty_slug',
            'realty_price',
            'realty_group',
            'realty_city',
            'realty_country',
            'realty_deleted_at',
            'images',
            'data',
        )

    def update(self, instance, validated_data):
        group_name = validated_data.pop('realty_group', None)

        if group_name:
            group = RealtyGroup.objects.filter(name=group_name).first()
            if group:
                instance.realty_group = group

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
    

class LikedRealtySerializer(serializers.ModelSerializer):
    realty = serializers.SerializerMethodField()

    user_login = serializers.CharField(
        source='user_access.login',
        read_only=True
    )

    class Meta:
        model = LikedRealty
        fields = (
            'id',
            'created_at',
            'user_login',
            'realty',
        )

    def get_realty(self, obj):
        return RealtySerializer(
            obj.realty,
            context=self.context
        ).data


class LikedRealtyListSerializer(serializers.ModelSerializer):
    realty = RealtySerializer(read_only=True) 

    class Meta:
        model = LikedRealty
        fields = ('id', 'created_at', 'realty')


class LikedRealtyCreateSerializer(serializers.ModelSerializer):
    realty_id = serializers.UUIDField(write_only=True)
    user_login = serializers.CharField(write_only=True)

    class Meta:
        model = LikedRealty
        fields = ('realty_id', 'user_login')

    def validate(self, attrs):
        realty = Realty.objects.filter(id=attrs['realty_id']).first()
        if not realty:
            raise serializers.ValidationError("Realty not found")

        user = UserAccess.objects.filter(login=attrs['user_login']).first()
        if not user:
            raise serializers.ValidationError("User not found")

        if LikedRealty.objects.filter(realty=realty, user_access=user).exists():
            raise serializers.ValidationError("Realty already liked")

        attrs['realty'] = realty
        attrs['user_access'] = user
        return attrs

    def create(self, validated_data):
        validated_data.pop('realty_id')
        validated_data.pop('user_login')
        return super().create(validated_data)
