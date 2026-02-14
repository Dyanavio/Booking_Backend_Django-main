from django.http import HttpResponse, Http404, JsonResponse
from main.models import *
from main.rest import *
from main.serializers.user import *
from main.serializers.booking import *
from main.serializers.realty import *
from main.serializers.feeedback import *
from main.serializers.location import *
from main.filters import *
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Avg, Count
from django.db.models.functions import Coalesce
from django.core.serializers import serialize
from backend.services import *
from django.shortcuts import get_object_or_404
from django.utils import timezone


storageService = DiskStorageService()


def item(request, itemId):
    try:
        content = storageService.getItemBytes(itemId)
        mime_type = storageService.tryGetMimeType(itemId)
        return HttpResponse(content, content_type=mime_type)
    except (FileNotFoundError, ValueError):
        raise Http404("Item not found")
    
def cities(request):
    cities = City.objects.values_list('name', flat=True)

    response = RestResponse(
            status=RestStatus(True, 200, "Ok"),
            data = list(cities)
        )
    return JsonResponse(response.to_dict(), status=200)
    
# -----------------------------------------------------------------------------------------------

class RealtyViewSet(ModelViewSet):
    #slug like id to requests
    #lookup_field = 'slug'
    queryset = Realty.objects.filter(deleted_at__isnull=True)
    filter_backends = [DjangoFilterBackend]
    filterset_class = RealtyFilter

    queryset = queryset.annotate(
        avg_rating=Avg("feedbacks__rate"),
        rates_count=Count("feedbacks")
    )
    
    def get_serializer_class(self):
        if self.action == 'create':
            return RealtyCreateSerializer
        return RealtySerializer

    #GET /realty/
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        response = RestResponse(
            status=RestStatus(True, 200, "OK"),
            data=serializer.data
        )

        return Response(response.to_dict(), status=status.HTTP_200_OK)

    #GET /realty/{id}/
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        response = RestResponse(
            status=RestStatus(True, 200, "OK"),
            data=serializer.data
        )

        return Response(response.to_dict(), status=status.HTTP_200_OK)

    #POST /realty/
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        image_file = request.FILES.get("realty-img")
        if not image_file:
            return Response(
                {"error": "Image is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        saved_name = storageService.saveItem(image_file)

        itemImage = ItemImage(
            image_url=saved_name,
            order=0,
            realty=instance
        )
        itemImage.save()

        response = RestResponse(
            status=RestStatus(True, 201, "Created"),
            data=serializer.data
        )
        return Response(response.to_dict(), status=status.HTTP_201_CREATED)
 
    #PATCH /realty/
    def patch(self, request, *args, **kwargs):
        slug = request.data.get('realty-former-slug')
        instance = get_object_or_404(Realty, slug=slug)

        name = request.data.get('realty-name')
        if name:
            instance.name = name

        description = request.data.get('realty-description')
        if description:
            instance.description = description

        slug_new = request.data.get('realty-slug')
        if slug_new:
            instance.slug = slug_new

        price = request.data.get('realty-price')
        if price:
            instance.price = price

        group_name = request.data.get('realty-group')
        if group_name:
            group = RealtyGroup.objects.filter(name=group_name).first()
            if group:
                instance.realty_group = group

        city_name = request.data.get('realty-city')
        country_name = request.data.get('realty-country')
        if city_name or country_name:
            city_qs = City.objects.all()
            if city_name:
                city_qs = city_qs.filter(name=city_name)
            if country_name:
                city_qs = city_qs.filter(country__name=country_name)
            city = city_qs.first()
            if not city:
                if not Country.objects.filter(name = country_name).first():
                    new_country = Country(name=country_name)
                    new_country.save()
                new_city = City(name=city_name, country=new_country)
                new_city.save()
                city = new_city
            instance.city = city

        instance.save()

        if 'realty-main-image' in request.FILES:
            image_file = request.FILES['realty-main-image']
            saved_name = storageService.saveItem(image_file)
            ItemImage.objects.create(
                image_url=saved_name,
                order=0,
                realty=instance
            )

        if 'realty-secondary-images' in request.FILES:
            for image_file in request.FILES.getlist('realty-secondary-images'):
                saved_name = storageService.saveItem(image_file)
                ItemImage.objects.create(
                    image_url=saved_name,
                    order=1,
                    realty=instance
                )
                

        serializer = RealtySerializer(instance, context={'request': request})
        response = RestResponse(
            status=RestStatus(True, 200, "Ok"),
            data=serializer.data
        )
        return Response(response.to_dict(), status=200)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted_at = timezone.now()
        instance.save()

        return Response({
            "status": {
                "isOk": True,
                "code": 200,
                "phrase": "Ok"
            },
            "data": {
                "message": f"Realty with slug {instance.slug} deleted"
            }
        }, status=200)

    
# -----------------------------------------------------------------------------------------------

@api_view(["POST"])
def RealtySearchViewSet(request):
    serializer = RealtySearchSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    data = serializer.validated_data

    queryset = Realty.objects.filter(deleted_at__isnull=True)

    if "City" in data and data["City"] != "":
        queryset = queryset.filter(city__name=data["City"])

    if "Price" in data:
        queryset = queryset.filter(price__gte=data["Price"])

    if "Checkboxes" in data and data["Checkboxes"]:
        queryset = queryset.filter(
            realty_group__slug__in=data["Checkboxes"]
        )

    queryset = queryset.annotate(
        avg_rating=Coalesce(Avg("feedbacks__rate"), 0.0)
    )

    if "Rating" in data:
        queryset = queryset.filter(avg_rating__gte=data["Rating"])
    
  

    queryset = queryset.distinct()

    user_access = None
    login = data.get("login")

    if login:
        user_access = UserAccess.objects.filter(login=login).first()

    result = RealtySerializer(
        queryset,
        many=True,
        context={
            "request": request,
            "user_access": user_access
        }
    ).data

    response = RestResponse(
        status=RestStatus(True, 200, "OK"),
        data=result
    )

    return Response(response.to_dict(), status=status.HTTP_200_OK)


def getRealtiesTable(request):
    realties = Realty.objects.all()
    tableBodyContent = ""
    for realty in realties:
        if realty.deleted_at is not None:
            continue
        tableBodyContent +=  f"<tr><td>{realty.name}</td> <td>{realty.description}</td> <td>{realty.slug}</td> <td>{realty.price}</td> <td>{realty.city.country.name}</td> <td>{realty.city.name}</td> <td>{realty.realty_group.name}</td> </tr>"
        response = RestResponse(
            status=RestStatus(True, 200, "Ok"),
            data = tableBodyContent
        )
    return JsonResponse(response.to_dict(), status=200)


# -----------------------------------------------------------------------------------------------

class LikedRealtyViewSet(ModelViewSet):
    queryset = LikedRealty.objects.select_related(
        'realty',
        'user_access'
    )
    http_method_names = ['get', 'post', 'delete']

    def get_serializer_class(self):
        if self.action == 'create':
            return LikedRealtyCreateSerializer
        return LikedRealtySerializer
    
    def get_queryset(self):
        queryset = LikedRealty.objects.select_related(
            'user_access',
            'realty',
            'realty__city',        
            'realty__realty_group' 
        ).prefetch_related(
            'realty__images',      
            'realty__feedbacks',   
            'realty__booking_items'
        )

        login = self.request.query_params.get('login')
        if login:
            queryset = queryset.filter(user_access__login__iexact=login)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        read_serializer = LikedRealtyListSerializer(instance, context={'request': request}) 

        response = RestResponse(
            status=RestStatus(True, 201, "Created"),
            data=read_serializer.data
        )
        return Response(response.to_dict(), status=status.HTTP_201_CREATED)


    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        login = request.query_params.get("login")
        user_access = None

        if login:
            user_access = UserAccess.objects.filter(login__iexact=login).first()

        serializer = self.get_serializer(
            queryset,
            many=True,
            context={
                "request": request,
                "user_access": user_access
            }
        )

        response = RestResponse(
            status=RestStatus(True, 200, "OK"),
            data=serializer.data
        )
        return Response(response.to_dict(), status=status.HTTP_200_OK)

    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()

        return Response({
            "status": {
                "isOk": True,
                "code": 200,
                "phrase": "Ok"
            },
            "data": {
                "message": "Removed from favorites"
            }
        }, status=status.HTTP_200_OK)

