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
from rest_framework import status
from django.db.models import Sum

from decimal import Decimal


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
        queryset = DeliveryAddress.objects.filter(user=self.request.user).order_by('-created_at')
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


class AdminOrderDetailsAPIView(RetrieveAPIView):
    serializer_class = CustomerOrderListSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'id'

    def get_object(self):
        id = self.kwargs['id']
        query = SubOrder.objects.get(id=id)
        return query


class AgentOrderList(ListAPIView):
    serializer_class = AgentOrderListSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        tomorrow = datetime.today() + timedelta(days=1)
        deliver_to_mukam = self.request.GET.get('deliver_to_mukam')
        deliver_start_date = self.request.GET.get('deliver_start_date')
        deliver_end_date = self.request.GET.get('deliver_end_date')
        order_start_date = self.request.GET.get('order_start_date')
        order_end_date = self.request.GET.get('order_end_date')
        farmer = self.request.GET.get('farmer')
        order_status = self.request.GET.get('order_status')
        district = self.request.GET.get('district')


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
        if deliver_start_date and deliver_end_date:
            queryset = queryset.filter(Q(delivery_date__range=(deliver_start_date,deliver_end_date)))
        if order_start_date and order_end_date:
            oed = datetime.strptime(str(order_end_date), '%Y-%m-%d')
            order_end_date = oed + timedelta(days=1)
            queryset = queryset.filter(Q(created_at__range=(order_start_date,order_end_date)))
        if farmer:
            queryset = queryset.filter(Q(order_item_suborder__product__user__id=farmer))
        if order_status:
            queryset = queryset.filter(Q(order_status=order_status))
        if district:
            queryset = queryset.filter(Q(delivery_address__district__id=district))
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
    # pagination_class = CustomPagination

    def get_queryset(self):
        user = self.request.user
        if self.request.user.user_type == "AGENT":
            tomorrow = datetime.today() + timedelta(days=1)
            # queryset = User.objects.filter(Q(agent_user_id=user.id), Q(user_type="FARMER"), Q(product_seller__order_item_product__isnull=False)).exclude(~Q(product_seller__possible_productions_date=tomorrow)).order_by('id').distinct()

            queryset = User.objects.filter(Q(agent_user_id=user.id), Q(user_type="FARMER"), Q(product_seller__order_item_product__isnull=False), Q(product_seller__possible_productions_date=tomorrow)).order_by('id').distinct()
        else:
            queryset = None
        return queryset


class AgentPickupLocationListOfAgentAPIView(ListAPIView):
    serializer_class = PickupLocationListSerializer

    def get_queryset(self):
        user = self.request.user
        if self.request.user.user_type == "AGENT":
            agent_upazilla = self.request.user.upazilla
            queryset = PickupLocation.objects.filter(status=True, upazilla=agent_upazilla)
        else:
            queryset = None
        return queryset


class PickupLocationQcPassedInfoUpdateAPIView(UpdateAPIView):
    serializer_class = PickupLocationQcPassedInfoUpdateSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'id'

    def get_object(self):
        id = self.kwargs['id']
        query = User.objects.get(id=id)
        return query


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
    permission_classes = [AllowAny]
    serializer_class = AdminOrdersListByPickupPointsListSerializer

    def get_queryset(self):
       today = datetime.today()
       pickup_points = PickupLocation.objects.filter(Q(status=True), Q(order_item_pickup_location__product__possible_productions_date=today))
       location = []
       for pickup_point in pickup_points:
           order = OrderItem.objects.filter(pickup_location=pickup_point)
           if order.exists():
               location.append(pickup_point.id)

       queryset = PickupLocation.objects.filter(id__in=location)
       return queryset


class FarmerPaymentListAPIView(ListAPIView):
    serializer_class = FarmerPaymentListSerializer

    def get_queryset(self):
        try:
            product_list = Product.objects.filter(
                status='PUBLISH', possible_productions_date=datetime.today())
            order_list = OrderItem.objects.filter(
                product__in=product_list, is_qc_passed='PASS', order__order_status='ON_TRANSIT')
            farmer_dict = {}
            for order in order_list:
                farmer_id = order.product.user.id
                if farmer_id in farmer_dict:
                    farmer_dict[farmer_id]["total_amount"] += order.total_price
                    farmer_dict[farmer_id]["item_list"].append({
                        "product_id": order.id,
                        "product_name": order.product.title,
                        "quantity": order.quantity,
                        "price": order.unit_price,
                        "total_price": order.total_price
                    })
                else:
                    farmer_dict[farmer_id] = {
                        "farmer_id": farmer_id,
                        "total_amount": order.total_price,
                        "item_list": [
                            {
                                "product_id": order.id,
                                "product_name": order.product.title,
                                "quantity": order.quantity,
                                "price": order.unit_price,
                                "total_price": order.total_price
                            }
                        ]
                    }


            for farmer in farmer_dict.values():
                farmer_id = farmer['farmer_id']
                farmerq = User.objects.get(id=farmer_id)
                account_info = FarmerAccountInfo.objects.get(farmer=farmerq)

                checkfarmerexist = PaymentHistory.objects.filter(
                    farmer=farmer_id, date=datetime.today())
                if checkfarmerexist:
                    due_payment_history = PaymentHistory.objects.filter(
                        farmer=farmerq, status='DUE', date=datetime.today())
                    if due_payment_history:
                        firstpayment = due_payment_history.first()
                        noneitemlist = []
                        for item in farmer["item_list"]:
                            order_item1 = OrderItem.objects.get(
                                id=item["product_id"])
                            if order_item1.payment_status == 'NONE':
                                noneitemlist.append(item)
                        if noneitemlist:
                            for item in noneitemlist:
                                order_item = OrderItem.objects.get(
                                    id=item["product_id"])
                                firstpayment.order_items.add(order_item)
                                firstpayment.amount += Decimal(
                                    item["total_price"])
                                firstpayment.save()
                                order_item.payment_status = 'DUE'
                                order_item.save()
                        else:
                            pass
                    else:
                        noneitemlist = []
                        for item in farmer["item_list"]:
                            order_item1 = OrderItem.objects.get(
                                id=item["product_id"])

                            if order_item1.payment_status == 'NONE':
                                noneitemlist.append(item)
                        if noneitemlist:
                            payment_history = PaymentHistory.objects.create(
                                farmer=farmerq,
                                farmer_account_info=account_info,
                                amount=0
                            )
                            for item in noneitemlist:
                                order_item = OrderItem.objects.get(
                                    id=item["product_id"])
                                payment_history.order_items.add(order_item)
                                payment_history.amount += Decimal(
                                    item["total_price"])
                                payment_history.save()
                                order_item.payment_status = 'DUE'
                                order_item.save()

                else:
                    noneitemlist = []
                    for item in farmer["item_list"]:
                        order_item1 = OrderItem.objects.get(
                            id=item["product_id"])
                        if order_item1.payment_status == 'NONE':
                            noneitemlist.append(item)
                    payment_history = PaymentHistory.objects.create(
                        farmer=farmerq,
                        farmer_account_info=account_info,
                        amount=0,
                    )
                    if noneitemlist:
                        for item in noneitemlist:
                            order_item = OrderItem.objects.get(
                                id=item["product_id"])
                            payment_history.order_items.add(order_item)
                            payment_history.amount += Decimal(
                                item["total_price"])
                            payment_history.save()
                            order_item.payment_status = 'DUE'
                            order_item.save()
            payment_history_for_today = PaymentHistory.objects.filter(
                date=datetime.today())
            return payment_history_for_today

        except Exception as e:
            print(e)
            raise NotFound("No Farmer List Found to Pay")


class FarmerPaymentStatusUpdateAPIView(UpdateAPIView):
    serializer_class = FarmerPaymentStatusUpdateSerializer
    queryset = PaymentHistory.objects.all()
    lookup_field = 'id'
    lookup_url_kwarg = 'id'

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        newStatus = request.data.get('status')
        if newStatus:
            instance.status = newStatus
            # update order items payment_status to PAID
            if newStatus == 'PAID':
                for order_item in instance.order_items.all():
                    order_item.payment_status = 'PAID'
                    order_item.save()
            else:
                for order_item in instance.order_items.all():
                    order_item.payment_status = 'DUE'
                    order_item.save()
            instance.save()
            print(instance, 'instance.status')
            return Response({'status': instance.status}, status=status.HTTP_200_OK)
        else:
            return Response({'status': 'Status not provided'}, status=status.HTTP_400_BAD_REQUEST)


class AdminOrderListOfQcPassedOrderAPIView(ListAPIView):
    serializer_class = AdminOrderListSerializer

    def get_queryset(self):
        # if self.request.user.is_admin == True:

            request = self.request
            today = request.GET.get('today')
            this_week = request.GET.get('this_week')

            queryset = SubOrder.objects.filter(order_status='ON_TRANSIT')
            if today:
                today_date = datetime.today().date()
                queryset = queryset.filter(Q(delivery_date__date=today_date))
            if this_week:
                today_date = datetime.today().date()
                today = today_date.strftime("%d/%m/%Y")
                dt = datetime.strptime(str(today), '%d/%m/%Y')
                week_start = dt - (timedelta(days=dt.weekday()) + timedelta(days=2))
                week_end = week_start + timedelta(days=6)
                queryset = queryset.filter(Q(delivery_date__range=(week_start,week_end)))

            return queryset
        # else:
        #     raise ValidationError(
        #         {"msg": 'You can not see Order list, because you are not an Admin!'})


class AdminOrderStatusUpdateAPIView(UpdateAPIView):
    serializer_class = OrderStatusSerializer
    queryset = SubOrder.objects.all()


class FarmerInfoListAPIView(ListAPIView):
    serializer_class = FarmerInfoListSerializer

    def get_queryset(self):
        if self.request.user.user_type == "ADMIN":
            queryset = User.objects.filter(user_type='FARMER')
        if self.request.user.user_type == "AGENT":
            queryset = User.objects.filter(user_type='FARMER', agent_user_id=self.request.user.id)
        if queryset:
            return queryset
        else:
            return []


class DistrictInfoListAPIView(ListAPIView):
    serializer_class = DistrictSerializer

    def get_queryset(self):
        if self.request.user.user_type == "ADMIN":
            queryset = District.objects.all()
        if self.request.user.user_type == "AGENT":
            # queryset = District.objects.filter(division__division_user__id=self.request.user.id)
            queryset = District.objects.all()
        if queryset:
            return queryset
        else:
            return []


class AdminSalesOfAnAgentAPIView(ListAPIView):
    serializer_class = SalesOfAnAgentSerializer

    def get_queryset(self):
        queryset = User.objects.filter(user_type='AGENT')
        if queryset:
            return queryset
        else:
            return []