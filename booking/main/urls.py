from django.urls import path, include
from main.views.user import UserViewSet, userDetail, login, register, getUsersTable
from main.views.realty import RealtyViewSet, item, cities, RealtySearchViewSet, getRealtiesTable, LikedRealtyViewSet
from main.views.feedback import FeedbackView
from main.views.booking import BookingView, BookingDetailView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'api/realty', RealtyViewSet, basename='realty')
router.register(r'api/user', UserViewSet, basename='user')
router.register(r'api/liked-realties', LikedRealtyViewSet, basename='liked-realties')


urlpatterns = [
    path('api/user/<str:login>', userDetail, name='userDetail'),
    path('api/auth/', login, name='login'), 
    path('api/auth/register', register, name='auth_register'), #POST
    path('api/realty/search', RealtySearchViewSet, name='realty_search'),

    path('', include(router.urls)),
    path("Storage/Item/<str:itemId>", item, name="storageItem"),
    path("api/feedback", FeedbackView.as_view(), name="feedback"),

    path('api/booking-item', BookingView.as_view(), name='booking_item'),
    path('api/booking-item/<uuid:id>', BookingDetailView.as_view(), name='booking_item'),

    path('Administrator/GetRealtiesTable', getRealtiesTable, name="getRealtiesTable"),
    path("Administrator/GetUsersTable", getUsersTable, name='getUsersTable'),

    path("api/cities/", cities, name="cities"),
    

]
