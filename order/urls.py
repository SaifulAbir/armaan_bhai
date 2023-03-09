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
    path('admin/order-update/<str:id>/', OrderUpdateAPIView.as_view()),
    path('customer-order-list/', CustomerOrderList.as_view()),
    path('customer-order-details/<str:id>/', CustomerOrderDetailsAPIView.as_view()),
    path('admin-order-details/<str:id>/', AdminOrderDetailsAPIView.as_view()),
    path('agent-order-list/', AgentOrderList.as_view()),
    #path('admin/collect-order-list/', CollectOrderList.as_view()),
    # pickup location
    path('create/pickup-location/', PickupLocationCreateAPIView.as_view()),
    path('pickup-location/list/', PickupLocationListAPIView.as_view()),
    path('pickup-location-details/<int:pid>/', PickupLocationDetailsAPIView.as_view()),
    path('update/pickup-location/<int:pk>/', PickupLocationUpdateAPIView.as_view()),
    # agent pickup location
    path('create/agent-pickup-location/', AgentPickupLocationCreateAPIView.as_view()),
    path('agent-pickup-location/list/', AgentPickupLocationListAPIView.as_view()),
    path('update/agent-pickup-location/<int:pk>/', AgentPickupLocationUpdateAPIView.as_view()),
    # set pickup / Mukam location
    path('agent/agent-set-pickup-location-on-order/list/', AgentSetPickupLocationOnOrderListAPIView.as_view()),
    path('agent/agent-pickup-location/list/', AgentPickupLocationListOfAgentAPIView.as_view()),
    path('agent/update-pickup-location-qc-passed-info/<str:id>/', PickupLocationQcPassedInfoUpdateAPIView.as_view()),
    # add payment method
    path('agent/create-payment-method/', PaymentMethodCreateAPIView.as_view()),
    path('agent/payment-details/<int:farmer_id>/', PaymentDetailsAPIView.as_view()),
    path('agent/payment-details-update/<int:id>/', PaymentDetailsUpdateAPIView.as_view()),

    # Pickup Api
    path('admin/order_list_by_pickup_point/', AdminOrdersListByPickupPointsListAPIView.as_view()),
    path('farmer-payment-list/', FarmerPaymentListAPIView.as_view()),
    path('farmer-payment-status-update/<int:id>/', FarmerPaymentStatusUpdateAPIView.as_view()),

    # order list of qc passed order
    path('admin/order-list-of-qc-passed-order/', AdminOrderListOfQcPassedOrderAPIView.as_view()),
    path('admin/order-status-update/<int:pk>/', AdminOrdertStatusUpdateAPIView.as_view()),
]