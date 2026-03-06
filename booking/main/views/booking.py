from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend
from main.models import *
from main.serializers.booking import BookingItemSerializer, BookingItemShortSerializer
from main.filters import BookingItemFilter
from main.rest import RestResponse, RestStatus
import datetime
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

class BookingView(APIView):
    filter_backends = [DjangoFilterBackend]
    filterset_class = BookingItemFilter

    @staticmethod
    def has_overlap(realty_id, start_date, end_date, exclude_id=None):
        qs = BookingItem.objects.filter(
            realty_id=realty_id,
            deleted_at__isnull=True,
            start_date__lt=end_date,
            end_date__gt=start_date
        )

        if exclude_id:
            qs = qs.exclude(id=exclude_id)

        return qs.exists()

    def get(self, request):
        queryset = BookingItem.objects.all()

        booking_filter = BookingItemFilter(request.GET, queryset=queryset)
        queryset = booking_filter.qs

        serializer = BookingItemSerializer(queryset, many=True)

        return Response(
            RestResponse(
                RestStatus(True, 200, "OK"),
                serializer.data
            ).to_dict(),
            status=status.HTTP_200_OK
        )
    
    def post(self, request):
        data = request.data

        try:
            user_access = UserAccess.objects.get(id=data.get("userAccessId"))
            realty_id = data.get("realtyId")
            start_date = data.get("startDate")
            end_date = data.get("endDate")
            booking_id = data.get("id")

            if not realty_id or not start_date or not end_date:
                return Response(
                    RestResponse(
                        RestStatus(False, 400, "Bad Request"),
                        "Missing required fields"
                    ).to_dict(),
                    status=status.HTTP_400_BAD_REQUEST
                )

            if start_date >= end_date:
                return Response(
                    RestResponse(
                        RestStatus(False, 400, "Invalid date range"),
                        None
                    ).to_dict(),
                    status=status.HTTP_400_BAD_REQUEST
                )

            if self.has_overlap(
                realty_id=realty_id,
                start_date=start_date,
                end_date=end_date,
                exclude_id=booking_id
            ):
                return Response(
                    RestResponse(
                        RestStatus(False, 409, "Conflict"),
                        "Realty already booked for selected dates"
                    ).to_dict(),
                    status=status.HTTP_409_CONFLICT
                )

            booking_item = BookingItem.objects.create(
                realty_id=realty_id,
                start_date=start_date,
                end_date=end_date,
                user_access=user_access
            )

            serializer = BookingItemSerializer(booking_item)

            return Response(
                RestResponse(
                    RestStatus(True, 201, "Created"),
                    serializer.data
                ).to_dict(),
                status=status.HTTP_201_CREATED
            )

        except UserAccess.DoesNotExist:
            return Response(
                RestResponse(
                    RestStatus(False, 404, "User not found"),
                    None
                ).to_dict(),
                status=status.HTTP_404_NOT_FOUND
            )


#----------------------------------------------------------------------------------------------

class BookingDetailView(APIView):
    @staticmethod
    def has_overlap(realty_id, start_date, end_date, exclude_id=None):
        qs = BookingItem.objects.filter(
            realty_id=realty_id,
            deleted_at__isnull=True,
            start_date__lt=end_date,
            end_date__gt=start_date
        )

        if exclude_id:
            qs = qs.exclude(id=exclude_id)

        return qs.exists()
    
    @staticmethod
    def parse_and_make_aware(date_string):
        if not date_string:
            return None
            
        dt = parse_datetime(date_string)
        
        if dt is None:
            parsed_date = parse_date(date_string)
            if parsed_date:
                dt = datetime.datetime.combine(parsed_date, datetime.time.min)
                
        if dt:
            return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
            
        return None
    
    def get_object(self, id):
        try:
            return BookingItem.objects.get(id=id)
        except BookingItem.DoesNotExist:
            return None

    def get(self, request, id):
        booking_item = self.get_object(id)
        if not booking_item:
            return Response(
                RestResponse(
                    RestStatus(False, 404, "Not Found"),
                    None
                ).to_dict(),
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = BookingItemShortSerializer(booking_item)

        return Response(
            RestResponse(
                RestStatus(True, 200, "OK"),
                serializer.data
            ).to_dict(),
            status=status.HTTP_200_OK
        )
    
    def patch(self, request, id):
        data = request.data

        try:
            realty_id = data.get("realtyId")
            start_date_str = data.get("startDate")
            end_date_str = data.get("endDate")

            start_date = self.parse_and_make_aware(start_date_str)
            end_date = self.parse_and_make_aware(end_date_str)

            booking = self.get_object(id)

            if not realty_id or not start_date or not end_date or not booking:
                return Response(
                    RestResponse(
                        RestStatus(False, 400, "Bad Request"),
                        "Missing required fields"
                    ).to_dict(),
                    status=status.HTTP_400_BAD_REQUEST
                )

            if start_date >= end_date or start_date < timezone.now():
                return Response(
                    RestResponse(
                        RestStatus(False, 400, "Invalid date range"),
                        None
                    ).to_dict(),
                    status=status.HTTP_400_BAD_REQUEST
                )

            if self.has_overlap(
                realty_id=realty_id,
                start_date=start_date,
                end_date=end_date,
                exclude_id=id
            ):
                return Response(
                    RestResponse(
                        RestStatus(False, 409, "Conflict"),
                        "Realty already booked for selected dates"
                    ).to_dict(),
                    status=status.HTTP_409_CONFLICT
                )

            booking.start_date = start_date
            booking.end_date = end_date

            booking.save()

            serializer = BookingItemShortSerializer(booking)

            return Response(
                RestResponse(
                    RestStatus(True, 200, "Ok"),
                    serializer.data
                ).to_dict(),
                status=status.HTTP_200_OK
            )

        except UserAccess.DoesNotExist:
            return Response(
                RestResponse(
                    RestStatus(False, 404, "User not found"),
                    None
                ).to_dict(),
                status=status.HTTP_404_NOT_FOUND
            )
    
    def delete(self, request, id):
        booking_item = self.get_object(id)
        
        if not booking_item:
            return Response(
                RestResponse(
                    RestStatus(False, 404, "Not Found"),
                    "Booking not found."
                ).to_dict(),
                status=status.HTTP_404_NOT_FOUND
            )

        booking_item.deleted_at = timezone.now()
        booking_item.save()

        return Response(
            RestResponse(
                RestStatus(True, 200, "Deleted successfully"),
                None
            ).to_dict(),
            status=status.HTTP_200_OK 
        )