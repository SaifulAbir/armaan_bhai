from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView, ListAPIView, DestroyAPIView, RetrieveAPIView, \
    UpdateAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from datetime import datetime, timedelta
from armaan_bhai.pagination import CustomPagination
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from order.serializers import *
from django.db.models import Q
from order.models import *
from user.models import *


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
    serializer_class = DeliveryAddressListSerializer

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
    serializer_class = CustomerOrderListSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        request = self.request
        order_status = request.GET.get('order_status')
        queryset = SubOrder.objects.filter(
            user=self.request.user).order_by('-created_at')
        if order_status:
            queryset = queryset.filter(order_status=order_status)
        return queryset


class CustomerOrderDetailsAPIView(RetrieveAPIView):
    serializer_class = CustomerOrderListSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'id'

    def get_object(self):
        id = self.kwargs['id']
        query = SubOrder.objects.get(id=id, user=self.request.user)
        return query


class AgentOrderList(ListAPIView):
    serializer_class = AgentOrderListSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        tomorrow = datetime.today() + timedelta(days=1)
        deliver_to_mukam = self.request.GET.get('deliver_to_mukam')
        if self.request.user.user_type == "AGENT":
            queryset = SubOrder.objects.filter(
                order_item_suborder__product__user__agent_user_id=self.request.user.id).order_by('-created_at')
        elif self.request.user.user_type == "FARMER":
            queryset = SubOrder.objects.filter(
                order_item_suborder__product__user=self.request.user).order_by('-created_at')
        else:
            queryset = SubOrder.objects.all().order_by('-created_at')
        if deliver_to_mukam == "true":
            queryset = queryset.filter(
                delivery_date__date=tomorrow, is_qc_passed=True)
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
    pagination_class = CustomPagination

    def get_queryset(self):
        queryset = PickupLocation.objects.filter(status=True)
        return queryset


class PickupLocationDetailsAPIView(RetrieveAPIView):
    serializer_class = PickupLocationListSerializer
    lookup_field = 'pid'
    lookup_url_kwarg = 'pid'

    def get_object(self):
        id = self.kwargs['pid']
        try:
            query = PickupLocation.objects.get(id=id, status=True)
            return query
        except PickupLocation.DoesNotExist:
            raise NotFound("Pickup Location not found")


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


class AgentSetPickupLocationOnOrderListAPIView(ListAPIView):
    serializer_class = AgentOrderListForSetupPickupLocationSerializer

    def get_queryset(self):
        user = self.request.user
        if self.request.user.user_type == "AGENT":
            tomorrow = datetime.today() + timedelta(days=1)
            # queryset = User.objects.filter(agent_user_id=user.id, user_type="FARMER").exclude(~Q(product_seller__possible_productions_date=tomorrow))

            queryset = User.objects.filter(agent_user_id=user.id, user_type="FARMER").exclude(~Q(product_seller__possible_productions_date=tomorrow))
        else:
            queryset = None
        return queryset


class AgentPickupLocationListOfAgentAPIView(ListAPIView):
    serializer_class = AgentPickupLocationListSerializer

    def get_queryset(self):
        user = self.request.user
        if self.request.user.user_type == "AGENT":
            agent_district = self.request.user.district
            # queryset = AgentPickupLocation.objects.filter(user=user.id ,status=True)
            queryset = PickupLocation.objects.filter(status=True, district=agent_district)
        else:
            queryset = None
        return queryset


class PickupLocationQcPassedInfoUpdateAPIView(UpdateAPIView):
    serializer_class = PickupLocationQcPassedInfoUpdateSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'id'

    def get_object(self):
        id = self.kwargs['id']
        query = OrderItem.objects.get(id=id)
        return query

    # queryset=OrderItem.objects.all()
    # serializer_class = PickupLocationQcPassedInfoUpdateSerializer

    # def get_object(self):
    #     return Profile.objects.annotate(
    #         total_donor=Count(
    #             Concat('profile_goal__goal_payment__goal', 'profile_goal__goal_payment__user'),
    #             filter=Q(profile_goal__goal_payment__status='PAID'),
    #             distinct=True
    #         ),
    #         total_completed_goals = Count(
    #             'profile_goal', filter=Q(profile_goal__paid_amount=F('profile_goal__total_amount'))
    #         )
    #     ).get(user=self.request.user)

    # def put(self, request, *args, **kwargs):
    #     return self.update(request, *args, **kwargs)

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


class PaymentDetailsAPIView(RetrieveAPIView):
    serializer_class = PaymentDetailsSerializer
    lookup_field = 'farmer_id'
    lookup_url_kwarg = 'farmer_id'


    def get_queryset(self):
        farmer_id = self.kwargs['farmer_id']
        try:
            query = FarmerAccountInfo.objects.filter(farmer=farmer_id)
            return query
        except FarmerAccountInfo.DoesNotExist:
            raise NotFound("Payment Details not found")


class PaymentDetailsUpdateAPIView(UpdateAPIView):
    serializer_class = PaymentDetailsUpdateSerializer
    queryset = FarmerAccountInfo.objects.all()
    lookup_field = 'id'
    lookup_url_kwarg = 'id'


class AdminOrdersListByPickupPointsListAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    # pagination_class = Pro
    serializer_class = AdminOrdersListByPickupPointsListSerializer

    def get_queryset(self):
        query = SubOrder.objects.filter(order_status='ON_PROCESS', order_item_suborder__is_qc_passed='PASS')
        return query

