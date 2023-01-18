from django.urls import path
from .api import *

urlpatterns = [
    path('create-delivery-address/', DeliveryAddressCreateAPIView.as_view()),
    path('update-delivery-address/<int:id>/', DeliveryAddressUpdateAPIView.as_view()),
    path('delivery-address-list/', DeliveryAddressListAPIView.as_view()),
    path('delete-delivery-address/<int:id>/', DeliveryAddressDeleteAPIView.as_view()),
    # checkout
    path('checkout/', CheckoutAPIView.as_view()),
    path('checkout-details/<str:id>/', CheckoutDetailsAPIView.as_view()),
]