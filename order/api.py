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
            queryset = User.objects.filter(agent_user_id=user.id, user_type="FARMER").exclude(~Q(product_seller__possible_productions_date=tomorrow)).order_by()
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
        queryset = PickupLocation.objects.filter(
            order_item_pickup_location__product__possible_productions_date=datetime.today(),
            order_item_pickup_location__is_qc_passed="PASS")

        print(queryset)
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

            farmer_payments = []
            for farmer_data in farmer_dict.values():
                farmer_id = farmer_data['farmer_id']
                farmer = User.objects.get(id=farmer_id)
                account_info = FarmerAccountInfo.objects.get(farmer=farmer)
                existpaymentHistory = PaymentHistory.objects.filter(
                    farmer_account_info=account_info, date=datetime.today())
                if existpaymentHistory:
                    for payment in existpaymentHistory:
                        if payment.status == 'PAID':
                            new_item_list = []
                            for item_data in farmer_data['item_list']:
                                if not payment.order_items.filter(id=item_data['product_id']).exists():
                                    new_item_list.append(item_data)
                            if new_item_list:
                                final_item_list = []
                                for item_data in new_item_list:
                                    checkitemexit =PaymentHistory.objects.filter(order_items=item_data['product_id'],date=datetime.today())
                                    if not checkitemexit:
                                        final_item_list.append(item_data)
                                
                                if final_item_list:
                                    new_payment = PaymentHistory.objects.create(
                                        farmer=account_info.farmer,
                                        farmer_account_info=account_info,
                                        amount=0,
                                    )
                                    for item_data in final_item_list:
                                        order_item = OrderItem.objects.get(
                                            id=item_data['product_id'])
                                        new_payment.order_items.add(order_item)
                                        new_payment.amount += item_data['total_price']
                                        new_payment.save()
                                    farmer_payments.append(new_payment)
                                        # print(item_data["total_price"])
                                        # return
                                        # new_payment = PaymentHistory.objects.create(
                                        #     farmer=account_info.farmer,
                                        #     farmer_account_info=account_info,
                                        #     amount=farmer_data['farmer_id']['item_list']['total_price'],
                                        # )
                                        # for item_data in new_item_list:
                                        #     order_item = OrderItem.objects.get(
                                        #         id=item_data['product_id'])
                                        #     new_payment.order_items.add(order_item)
                                        # new_payment.save()
                                        # farmer_payments.append(new_payment)
                                else:
                                    farmer_payments.append(payment)
                            
                        
                        else:
                            print(payment)        
                            payment.order_items.clear()
                            for item_data in farmer_data['item_list']:
                                order_item = OrderItem.objects.get(
                                    id=item_data['product_id'])
                                payment.order_items.add(order_item)
                            payment.amount = farmer_data['total_amount']
                            payment.save()
                    
                else:
                    payment = PaymentHistory.objects.create(
                        farmer=account_info.farmer,
                        farmer_account_info=account_info,
                        amount=farmer_data['total_amount'],
                    )
                    for item_data in farmer_data['item_list']:
                        order_item = OrderItem.objects.get(
                            id=item_data['product_id'])
                        payment.order_items.add(order_item)
                farmer_payments.append(payment)

            return PaymentHistory.objects.filter(id__in=[p.id for p in farmer_payments])

        except Exception as e:
            print(e)
            raise NotFound("No Farmer List Found to Pay")


class FarmerPaymentStatusUpdateAPIView(UpdateAPIView):
    queryset = PaymentHistory.objects.all()
    lookup_field = 'id'
    lookup_url_kwarg = 'id'

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        newStatus = request.data.get('status')
        if newStatus:
            instance.status = newStatus
            instance.save()
            return Response({'status': instance.status}, status=status.HTTP_200_OK)
        else:
            return Response({'status': 'Status not provided'}, status=status.HTTP_400_BAD_REQUEST)
