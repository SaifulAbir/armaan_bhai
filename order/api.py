from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView, ListAPIView, DestroyAPIView, RetrieveAPIView, \
    UpdateAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from datetime import datetime, timedelta
from armaan_bhai.pagination import CustomPagination
from order.serializers import *


class DeliveryAddressCreateAPIView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAddressSerializer

    def post(self, request, *args, **kwargs):
        # request.data['user'] = request.user
        return super(DeliveryAddressCreateAPIView, self).post(request, *args, **kwargs)


class DeliveryAddressUpdateAPIView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAddressSerializer
    queryset = DeliveryAddress.objects.all()
    lookup_field = 'id'
    lookup_url_kwarg = "id"

    def put(self, request, *args, **kwargs):
        return super(DeliveryAddressUpdateAPIView, self).put(request, *args, **kwargs)


class DeliveryAddressListAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAddressSerializer

    def get_queryset(self):
        queryset = DeliveryAddress.objects.filter(user=self.request.user)
        return queryset


class DeliveryAddressDeleteAPIView(DestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAddressSerializer
    queryset = DeliveryAddress.objects.all()
    lookup_field = 'id'
    lookup_url_kwarg = "id"

    def delete(self, request, *args, **kwargs):
        return super(DeliveryAddressDeleteAPIView, self).delete(request, *args, **kwargs)


class CheckoutAPIView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CheckoutSerializer

    def post(self, request, *args, **kwargs):
        return super(CheckoutAPIView, self).post(request, *args, **kwargs)


class CheckoutDetailsAPIView(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = CheckoutDetailsSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'id'

    def get_object(self):
        id = self.kwargs['id']
        query = Order.objects.get(id=id)
        return query


class CustomerOrderList(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CustomerOrderListSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        request = self.request
        order_status = request.GET.get('order_status')
        queryset = Order.objects.filter(user=self.request.user).order_by('-created_at')
        if order_status:
            queryset = queryset.filter(order_status = order_status)
        return queryset


class AgentOrderList(ListAPIView):
    serializer_class = AgentOrderListSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        tomorrow = datetime.today() + timedelta(days=1)
        deliver_to_mukam = self.request.GET.get('deliver_to_mukam')
        if self.request.user.user_type == "AGENT":
            queryset = Order.objects.filter(order_item_order__product__user__agent_user_id=self.request.user.id).order_by('-created_at')
        else:
            queryset = Order.objects.all().order_by('-created_at')
        if deliver_to_mukam == "true":
            queryset = queryset.filter(delivery_date__date=tomorrow, is_qc_passed=True)
        return queryset

#
# class CollectOrderList(ListAPIView):
#     serializer_class = AgentOrderListSerializer
#     pagination_class = CustomPagination
#
#     def get_queryset(self):
#         queryset = Order.objects.filter(order_date__lt=datetime.today()).order_by('-created_at')
#         return queryset


class PickupLocationCreateAPIView(CreateAPIView):
    serializer_class = PickupLocationSerializer


class PickupLocationListAPIView(ListAPIView):
    serializer_class = PickupLocationListSerializer

    def get_queryset(self):
        queryset = PickupLocation.objects.filter(status=True)
        return queryset


class PickupLocationUpdateAPIView(UpdateAPIView):
    serializer_class = PickupLocationSerializer
    queryset = PickupLocation.objects.all()


class AgentPickupLocationCreateAPIView(CreateAPIView):
    serializer_class = AgentPickupLocationSerializer


class AgentPickupLocationListAPIView(ListAPIView):
    serializer_class = AgentPickupLocationListSerializer

    def get_queryset(self):
        queryset = AgentPickupLocation.objects.filter(status=True)
        return queryset


class AgentPickupLocationUpdateAPIView(UpdateAPIView):
    serializer_class = AgentPickupLocationSerializer
    queryset = AgentPickupLocation.objects.all()


class OrderUpdateAPIView(UpdateAPIView):
    serializer_class = OrderUpdateSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'id'

    def get_object(self):
        id = self.kwargs['id']
        query = Order.objects.get(id=id)
        return query


class PaymentMethodCreateAPIView(CreateAPIView):
    serializer_class = PaymentMethodSerializer

    def post(self, request, *args, **kwargs):
        return super(PaymentMethodCreateAPIView, self).post(request, *args, **kwargs)


class OrdersListByPickupPointsListAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    # pagination_class = Pro
    # serializer_class = AgentOrderListSerializer