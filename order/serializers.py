import decimal

from rest_framework import serializers
from order.models import DeliveryAddress, OrderItem, Order, CouponStat, Coupon, PickupLocation, AgentPickupLocation, \
    FarmerAccountInfo, SubOrder, PaymentHistory
from product.models import Inventory, Product
from product.serializers import ProductViewSerializer
from user.models import User, AgentFarmer
from datetime import datetime, timedelta
from user.serializers import CustomerProfileDetailSerializer, DivisionSerializer, DistrictSerializer, UpazillaSerializer
from django.utils import timezone
from django.db.models import Sum
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from datetime import date
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings


class DeliveryAddressSerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(source='district.name', read_only=True)
    division_name = serializers.CharField(source='division.name', read_only=True)
    upazilla_name = serializers.CharField(source='upazilla.name', read_only=True)
    class Meta:
        model = DeliveryAddress
        fields = ['id', 'user', 'name', 'address', 'phone', 'email', 'district', 'district_name', 'division', 'division_name', 'upazilla', 'upazilla_name']

    def create(self, validated_data):
        address_instance = DeliveryAddress.objects.create(**validated_data, user=self.context['request'].user)
        return address_instance


class DeliveryAddressListSerializer(serializers.ModelSerializer):
    division = DivisionSerializer(many=False, read_only=True)
    district = DistrictSerializer(many=False, read_only=True)
    upazilla = UpazillaSerializer(many=False, read_only=True)

    class Meta:
        model = DeliveryAddress
        fields = ['id', 'user', 'name', 'address', 'phone', 'email', 'district', 'division', 'upazilla']


class ProductItemCheckoutSerializer(serializers.ModelSerializer):
    # product_title = serializers.CharField(source='product.title', read_only=True)
    product_obj = ProductViewSerializer(source='product', read_only=True)
    class Meta:
        model = OrderItem
        fields = ['id',
                  'product',
                  'product_obj',
                  'quantity',
                  'unit_price'
                  ]


class CheckoutSerializer(serializers.ModelSerializer):
    order_item_order = ProductItemCheckoutSerializer(many=True, required=True)
    coupon_status = serializers.BooleanField(write_only=True, required=False)
    delivery_address_obj = serializers.SerializerMethodField('get_delivery_address')

    class Meta:
        model = Order
        fields = ['id', 'product_count', 'total_price', 'coupon', 'coupon_status',
                  'coupon_discount_amount', 'vat_amount', 'vat_percentage', 'payment_type', 'order_item_order', 'delivery_address',
                  'comment', 'delivery_address_obj']

    def get_delivery_address(self, obj):
        delivery_address = DeliveryAddressSerializer(instance=obj.delivery_address, many=False)
        return delivery_address.data

    def create(self, validated_data):
        try:
            order_items = validated_data.pop('order_item_order')
        except KeyError:
            raise serializers.ValidationError('Order items are missing')

        payment_type = validated_data.get('payment_type')

        if payment_type == 'PG':
            order_instance = Order.objects.create(
                **validated_data, user=self.context['request'].user, payment_status='PAID', order_status='ON_PROCESS')
        else:
            order_instance = Order.objects.create(
                **validated_data, user=self.context['request'].user, payment_status='DUE', order_status='ON_PROCESS')


        if order_items:
            suborder_instance_count = 0
            for order_item in order_items:
                product = order_item['product']
                quantity = order_item['quantity']
                unit_price = order_item['unit_price']
                total_price = float(unit_price) * float(quantity)
                if int(quantity) > product.quantity:
                    raise ValidationError("Ordered quantity is greater than inventory")

                if suborder_instance_count == 0:
                    if payment_type == 'PG':
                        suborder_obj = SubOrder.objects.create(order=order_instance, user=self.context['request'].user, product_count=1,
                                            total_price=total_price, delivery_address=validated_data.get('delivery_address'),
                                            delivery_date=product.possible_delivery_date, payment_status='PAID',
                                                order_status='ON_PROCESS')
                    else:
                        suborder_obj = SubOrder.objects.create(order=order_instance, user=self.context['request'].user,
                                                product_count=1,
                                                total_price=total_price,
                                                delivery_address=validated_data.get('delivery_address'),
                                                delivery_date=product.possible_delivery_date, payment_status='DUE',
                                                order_status='ON_PROCESS')
                    OrderItem.objects.create(order=order_instance, suborder=suborder_obj, product=product, quantity=int(
                                     quantity), unit_price=unit_price, total_price=total_price)
                    suborder_instance_count += 1
                    if order_instance:
                        product_obj = Product.objects.filter(id=product.id)
                        inventory_obj = Inventory.objects.filter(product=product).latest('created_at')
                        update_quantity = int(inventory_obj.current_quantity) - int(quantity)
                        product_obj.update(quantity = update_quantity)
                        inventory_obj.current_quantity = update_quantity
                        inventory_obj.save()

                        # product sell count
                        sell_count = product_obj[0].sell_count + 1
                        product_obj.update(sell_count=sell_count)
                else:
                    suborder_objects = SubOrder.objects.all().order_by('-created_at')[:suborder_instance_count]
                    count = 0
                    for suborder_object in suborder_objects:
                        count += 1
                        if suborder_object.delivery_date.date() == product.possible_delivery_date and suborder_object.user == self.context['request'].user:
                            suborder_object.product_count += 1
                            suborder_object.total_price += decimal.Decimal(total_price)
                            suborder_object.save()
                            OrderItem.objects.create(order=order_instance, suborder=suborder_object, product=product,
                                                     quantity=int(
                                                         quantity), unit_price=unit_price, total_price=total_price)
                            if order_instance:
                                product_obj = Product.objects.filter(id=product.id)
                                inventory_obj = Inventory.objects.filter(product=product).latest('created_at')
                                update_quantity = int(inventory_obj.current_quantity) - int(quantity)
                                product_obj.update(quantity = update_quantity)
                                inventory_obj.current_quantity = update_quantity
                                inventory_obj.save()

                                # product sell count
                                sell_count = product_obj[0].sell_count + 1
                                product_obj.update(sell_count=sell_count)
                            break

                        if count == suborder_objects.count():
                            if payment_type == 'PG':
                                suborder_obj = SubOrder.objects.create(order=order_instance, user=self.context['request'].user,
                                                        product_count=1,
                                                        total_price=total_price,
                                                        delivery_address=validated_data.get('delivery_address'),
                                                        delivery_date=product.possible_delivery_date,
                                                        payment_status='PAID',
                                                        order_status='ON_PROCESS')
                            else:
                                suborder_obj = SubOrder.objects.create(order=order_instance, user=self.context['request'].user,
                                                        product_count=1,
                                                        total_price=total_price,
                                                        delivery_address=validated_data.get('delivery_address'),
                                                        delivery_date=product.possible_delivery_date,
                                                        payment_status='DUE',
                                                        order_status='ON_PROCESS')
                            OrderItem.objects.create(order=order_instance, suborder=suborder_obj, product=product,
                                                     quantity=int(
                                                         quantity), unit_price=unit_price, total_price=total_price)
                            suborder_instance_count += 1
                            if order_instance:
                                product_obj = Product.objects.filter(id=product.id)
                                inventory_obj = Inventory.objects.filter(product=product).latest('created_at')
                                update_quantity = int(inventory_obj.current_quantity) - int(quantity)
                                product_obj.update(quantity = update_quantity)
                                inventory_obj.current_quantity = update_quantity
                                inventory_obj.save()

                                # product sell count
                                sell_count = product_obj[0].sell_count + 1
                                product_obj.update(sell_count=sell_count)

        # apply coupon
        try:
            coupon_status = validated_data.pop('coupon_status')
        except KeyError:
            coupon_status = None

        if coupon_status == True:
            coupon = validated_data.pop('coupon')
            if coupon.usage_count != coupon.max_time:
                coupon_obj = Coupon.objects.filter(id=coupon.id)
                coupon_stat = CouponStat.objects.filter(
                    coupon=coupon.id, user=self.context['request'].user).exists()
                if not coupon_stat:
                    CouponStat.objects.create(
                        coupon=coupon, user=self.context['request'].user)
                    usage_count = int(coupon.usage_count)
                    coupon_obj.update(usage_count=usage_count + 1)
                else:
                    raise serializers.ValidationError("Usage limit exceeded")
            else:
                raise serializers.ValidationError("Usage limit exceeded")

        # send email to the user
        user = self.context['request'].user
        email = user.email
        if email:
            order_id = order_instance.order_id
            created_at = order_instance.created_at.strftime("%Y-%m-%d")
            payment_type = order_instance.payment_type
            sub_total = OrderItem.objects.filter(order=order_instance).aggregate(total=Sum('total_price'))['total'] or 0.0

            order_items = OrderItem.objects.filter(order=order_instance)
            subject = "Your order has been successfully placed."
            html_message = render_to_string('order_details.html',
                {
                    'email' : email,
                    'order_id': order_id,
                    'created_at': created_at,
                    'order_items': order_items,
                    'payment_type': payment_type,
                    'sub_total': sub_total if sub_total else 0.0,
                    'total': sub_total + 60.0 if sub_total  else 0.0
                })

            send_mail(
                subject=subject,
                message=None,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                html_message=html_message
            )

            return order_instance
        else:
            return order_instance


class CheckoutDetailsSerializer(serializers.ModelSerializer):
    user = CustomerProfileDetailSerializer(many=False, read_only=True)
    order_item_order = ProductItemCheckoutSerializer(many=True, read_only=True)
    delivery_address = DeliveryAddressSerializer(many=False, read_only=True)
    class Meta:
        model = Order
        fields = ['id', 'user', 'order_id', 'order_date', 'delivery_date', 'order_status', 'order_item_order', 'delivery_address', 'payment_type',
        'coupon_discount_amount', 'total_price', 'is_qc_passed']


class OrderUpdateSerializer(serializers.ModelSerializer):
    user = CustomerProfileDetailSerializer(many=False, read_only=True)
    order_item_suborder = ProductItemCheckoutSerializer(many=True, read_only=True)
    delivery_address = DeliveryAddressSerializer(many=False, read_only=True)
    class Meta:
        model = SubOrder
        fields = ['is_qc_passed', 'delivery_address', 'order_item_suborder', 'user']


class CustomerOrderListSerializer(serializers.ModelSerializer):
    user = CustomerProfileDetailSerializer(many=False, read_only=True)
    order_item_suborder = ProductItemCheckoutSerializer(many=True, read_only=True)
    delivery_address = DeliveryAddressListSerializer(many=False, read_only=True)
    order_status_value = serializers.CharField(
        source='get_order_status_display', read_only=True
    )
    payment_status_value = serializers.CharField(
        source='get_payment_status_display', read_only=True
    )
    order_number = serializers.CharField(source='order.order_id')
    class Meta:
        model = SubOrder
        fields = ['id', 'user', 'order_number', 'suborder_number', 'order_date', 'delivery_date', 'order_status', 'order_status_value', 'order_item_suborder', 'delivery_address', 'payment_type',
        'coupon_discount_amount', 'total_price', 'payment_status_value']


class AgentOrderListSerializer(serializers.ModelSerializer):
    order_status_value = serializers.CharField(
        source='get_order_status_display', read_only=True
    )
    user = CustomerProfileDetailSerializer(many=False, read_only=True)
    order_item_suborder = ProductItemCheckoutSerializer(many=True, read_only=True)
    delivery_address = DeliveryAddressSerializer(many=False, read_only=True)
    class Meta:
        model = SubOrder
        fields = ['id', 'user', 'order', 'suborder_number', 'order_date', 'delivery_date', 'order_status', 'order_status_value', 'order_item_suborder', 'delivery_address', 'payment_type',
        'coupon_discount_amount', 'total_price', 'is_qc_passed']


# Pickup Location
class PickupLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupLocation
        fields = ['address', 'division', 'district', 'upazilla']


class PickupLocationListSerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(source='district.name', read_only=True)
    division_name = serializers.CharField(source='division.name', read_only=True)
    upazilla_name = serializers.CharField(source='upazilla.name', read_only=True)

    class Meta:
        model = PickupLocation
        fields = ['id', 'address', 'division', 'division_name', 'district','district_name', 'upazilla','upazilla_name', 'created_at', 'status']



# Agent Pickup Location
class AgentPickupLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentPickupLocation
        fields = ['user', 'pickup_location']


class AgentPickupLocationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentPickupLocation
        fields = ['id', 'user', 'pickup_location', 'created_at']


QC_CHOICES =(
    ('NEUTRAL', 'Neutral'),
    ('PASS', 'Pass'),
    ('FAIL', 'Fail'),
)
class PickupLocationQcPassedInfoUpdateSerializer(serializers.ModelSerializer):
    pickup_location = serializers.IntegerField(required=False)
    is_qc_passed = serializers.ChoiceField(choices = QC_CHOICES, required=False)
    class Meta:
        model = User
        fields = ['id', 'pickup_location', 'is_qc_passed']

    def update(self, instance, validated_data):
        try:
            pickup_location = validated_data.pop('pickup_location')
        except:
            pickup_location = ''
        try:
            is_qc_passed = validated_data.pop('is_qc_passed')
        except:
            is_qc_passed = ''

        tomorrow = datetime.today() + timedelta(days=1)
        if pickup_location:
            OrderItem.objects.filter(product__user = instance.id, product__possible_productions_date = tomorrow).update(pickup_location=pickup_location)
        if is_qc_passed:
            OrderItem.objects.filter(product__user = instance.id, product__possible_productions_date = tomorrow).update(is_qc_passed=is_qc_passed)

        if Order.objects.filter(order_item_order__product__user=instance.id, order_item_order__product__possible_productions_date = tomorrow).exists():
            if is_qc_passed == 'PASS':
                Order.objects.filter(order_item_order__product__user=instance.id, order_item_order__product__possible_productions_date = tomorrow).update(order_status='ON_TRANSIT')
            if is_qc_passed == 'FAIL':
                Order.objects.filter(order_item_order__product__user=instance.id, order_item_order__product__possible_productions_date = tomorrow).update(order_status='CANCELED')
        if SubOrder.objects.filter(order_item_suborder__product__user=instance.id, order_item_suborder__product__possible_productions_date = tomorrow).exists():
            if is_qc_passed == 'PASS':
                SubOrder.objects.filter(order_item_suborder__product__user=instance.id, order_item_suborder__product__possible_productions_date = tomorrow).update(order_status='ON_TRANSIT')
            if is_qc_passed == 'FAIL':
                Order.objects.filter(order_item_order__product__user=instance.id, order_item_order__product__possible_productions_date = tomorrow).update(order_status='CANCELED')

        return super().update(instance, validated_data)


# payment method
class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerAccountInfo
        fields = ['id', 'account_type', 'account_number', 'account_holder', 'bank_name', 'brunch_name', 'Mobile_number',
                  'farmer']

    def create(self, validated_data):
        farmer_account_info = FarmerAccountInfo.objects.create(**validated_data, created_by=self.context['request'].user)
        return farmer_account_info


class QcPassSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id',
                  'is_qc_passed'
                ]


class SetPickupPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id',
                  'pickup_location'
                ]


class AgentMukamLocationSetupDataSerializer(serializers.ModelSerializer):
    product_unit_title = serializers.CharField(source='unit.title', read_only=True)
    whole_quantity = serializers.SerializerMethodField()
    class Meta:
        model = Product
        fields = ['id',
                  'title',
                  'whole_quantity',
                  'product_unit_title',
                  ]
    def get_whole_quantity(self, obj):
        try:
            return obj.whole_quantity
        except:
            return 0


class AgentOrderListForSetupPickupLocationSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField('get_products')
    pickup_location = serializers.SerializerMethodField()
    is_qc_passed = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ['id', 'full_name', 'phone_number', 'products', 'pickup_location', 'is_qc_passed']

    def get_products(self, obj):
        tomorrow = datetime.today() + timedelta(days=1)
        query = Product.objects.filter(Q(user = obj), Q(possible_productions_date=tomorrow), Q(order_item_product__isnull=False) ).annotate(whole_quantity=Sum('order_item_product__quantity', filter=Q(order_item_product__suborder__order_status='ON_PROCESS') | Q(order_item_product__suborder__order_status='ON_TRANSIT')))
        serializer = AgentMukamLocationSetupDataSerializer(instance=query, many=True)
        return serializer.data

    def get_pickup_location(self, obj):
        tomorrow = datetime.today() + timedelta(days=1)
        query = OrderItem.objects.filter(Q(product__user = obj), Q(product__possible_productions_date=tomorrow), Q(suborder__order_status='ON_PROCESS') | Q(suborder__order_status='ON_TRANSIT')).distinct('pickup_location')
        for i in query:
            if i.pickup_location:
                pickup_location = i.pickup_location.id
                return pickup_location

    def get_is_qc_passed(self, obj):
        tomorrow = datetime.today() + timedelta(days=1)
        query = OrderItem.objects.filter(Q(product__user = obj), Q(product__possible_productions_date=tomorrow), Q(suborder__order_status='ON_PROCESS') | Q(suborder__order_status='ON_TRANSIT')).distinct('is_qc_passed')
        for i in query:
            is_qc_passed = i.is_qc_passed
            return is_qc_passed


class PaymentDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerAccountInfo
        fields = ['id', 'account_type', 'account_number', 'account_holder', 'bank_name', 'brunch_name', 'Mobile_number',
                  'farmer', 'created_by']


class PaymentDetailsUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerAccountInfo
        fields = ['id', 'account_type', 'account_number', 'account_holder', 'bank_name', 'brunch_name', 'Mobile_number', 'farmer', 'created_by']
        read_only_fields = ['id', 'farmer', 'created_by']

    def update(self, instance, validated_data):
        instance.account_type = validated_data.get('account_type', instance.account_type)
        instance.account_number = validated_data.get('account_number', instance.account_number)
        instance.account_holder = validated_data.get('account_holder', instance.account_holder)
        instance.bank_name = validated_data.get('bank_name', instance.bank_name)
        instance.brunch_name = validated_data.get('brunch_name', instance.brunch_name)
        instance.Mobile_number = validated_data.get('Mobile_number', instance.Mobile_number)
        instance.save()
        return instance


class AdminOrderListByLocationSerializer(serializers.ModelSerializer):
    product_unit_title = serializers.CharField(source='unit.title', read_only=True)
    product_seller_title = serializers.CharField(source='user.full_name', read_only=True)
    product_seller_number = serializers.CharField(source='user.phone_number', read_only=True)
    whole_quantity = serializers.SerializerMethodField()
    agent_name = serializers.SerializerMethodField()
    agent_phone_number = serializers.SerializerMethodField()
    class Meta:
        model = Product
        fields = ['id',
                  'title',
                  'whole_quantity',
                  'product_unit_title',
                  'possible_productions_date',
                  'product_seller_title',
                  'product_seller_number',
                  'agent_name',
                  'agent_phone_number'
                  ]
    def get_whole_quantity(self, obj):
        try:
            return obj.whole_quantity
        except:
            return 0

    def get_agent_name(self, obj):
        agent_user_id = obj.user.agent_user_id
        if agent_user_id:
            agent_user = User.objects.get(id=agent_user_id)
            return agent_user.full_name
        else:
            return None

    def get_agent_phone_number(self, obj):
        agent_user_id = obj.user.agent_user_id
        if agent_user_id:
            agent_user = User.objects.get(id=agent_user_id)
            return agent_user.phone_number
        else:
            return None


class AdminOrdersListByPickupPointsListSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField('get_products')

    class Meta:
        model = PickupLocation
        fields = [
            'id', 'address', 'products'
        ]

    def get_products(self, obj):
        today = datetime.today()
        query = Product.objects.filter(Q(possible_productions_date=today), Q(order_item_product__pickup_location=obj), Q(order_item_product__is_qc_passed='PASS')).annotate(whole_quantity=Sum('order_item_product__quantity',  filter=Q(order_item_product__pickup_location=obj, order_item_product__is_qc_passed='PASS')))
        serializer = AdminOrderListByLocationSerializer(instance=query, many=True)
        return serializer.data

class ProductItemSerializer(serializers.ModelSerializer):
    product_title = serializers.SerializerMethodField('get_product_title')
    class Meta:
        model = OrderItem
        fields = ['id', 'product','product_title', 'quantity', 'unit_price', 'total_price', 'is_qc_passed','payment_status']

    def get_product_title(self, obj):
        return obj.product.title


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['full_name','gender','address','phone_number' ]


class FarmerPaymentListSerializer(serializers.ModelSerializer):
    farmer_account_info = serializers.SerializerMethodField('get_farmer_account_info')
    order_items = serializers.SerializerMethodField('get_order_items')
    farmer = serializers.SerializerMethodField('get_farmer')
    agent_name = serializers.SerializerMethodField('get_agent_name')

    class Meta:
        model = PaymentHistory
        fields = ['id','farmer', 'farmer_account_info', 'order_items', 'amount', 'status', 'date', 'agent_name']

    def get_farmer_account_info(self, obj):
        serializer = PaymentDetailsSerializer(instance=obj.farmer_account_info, many=False)
        return serializer.data

    def get_order_items(self, obj):
        serializer = ProductItemSerializer(instance=obj.order_items, many=True)

        return serializer.data
    
    def get_farmer(self, obj):
        serializer = UserSerializer(instance=obj.farmer, many=False)
        return serializer.data

    def get_agent_name(self, obj):
        agent_user_id = obj.farmer.id
        if agent_user_id:
            farmer_obj = User.objects.get(id=agent_user_id)
            agent_user = User.objects.get(id=farmer_obj.agent_user_id)
            return agent_user.full_name
        else:
            return None


class FarmerPaymentStatusUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = PaymentHistory
        fields = ['status']


class AdminOrderListSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(source='order.order_id', read_only=True)
    delivery_location = serializers.SerializerMethodField('get_delivery_location')
    order_items = serializers.SerializerMethodField('get_order_items')
    class Meta:
        model = SubOrder
        fields = ['id', 'order_id', 'suborder_number', 'delivery_location', 'delivery_date', 'order_items', 'order_status']

    def get_delivery_location(self, obj):
        delivery_address = DeliveryAddressSerializer(instance=obj.delivery_address, many=False)
        return delivery_address.data

    def get_order_items(self, obj):
        try:
            queryset = OrderItem.objects.filter(suborder=obj.id, is_qc_passed='PASS')
            serializer = ProductItemSerializer(instance=queryset, many=True, context={
                                                'request': self.context['request']})
            return serializer.data
        except:
            return []


ORDER_CHOICES =(
    ('ON_PROCESS', 'On Process'),
    ('CANCELED', 'Canceled'),
    ('ON_TRANSIT', 'On Transit'),
    ('DELIVERED', 'Delivered'),
)
class OrderStatusSerializer(serializers.ModelSerializer):
    order_status = serializers.ChoiceField(choices = ORDER_CHOICES, required=False)
    class Meta:
        model = SubOrder
        fields = ['id', 'order_status']

    def update(self, instance, validated_data):
        try:
            order_status = validated_data.pop('order_status')
        except:
            order_status = ''
        if order_status == 'DELIVERED':
            validated_data.update({"payment_status": 'PAID', "order_status": order_status})
        else:
            validated_data.update({"order_status": order_status})
        return super().update(instance, validated_data)


class FarmerInfoListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'full_name','phone_number']


def first_date_of_current_month(year, month):
        first_date = datetime(year, month, 1)
        return first_date.strftime("%Y-%m-%d")


def last_date_of_month(year, month):
    if month == 12:
        last_date = datetime(year, month, 31)
    else:
        last_date = datetime(year, month + 1, 1) + timedelta(days=-1)
    return last_date.strftime("%Y-%m-%d")

class SalesOfAnAgentSerializer(serializers.ModelSerializer):
    farmers = serializers.SerializerMethodField('get_farmer')
    total_sale = serializers.SerializerMethodField('get_total_sale')
    class Meta:
        model = User
        fields = ['id', 'full_name', 'phone_number', 'farmers', 'total_sale']

    def get_farmer(self, obj):
        try:
            queryset = User.objects.filter(agent_user_id=obj.id)
            serializer = FarmerInfoListSerializer(instance=queryset, many=True, context={
                                                'request': self.context['request']})
            return serializer.data
        except:
            return []

    def get_total_sale(self, obj):
        request = self.context.get("request")
        this_week = request.GET.get('this_week')
        this_month = request.GET.get('this_month')

        if this_week:
            today_date = datetime.today().date()
            today = today_date.strftime("%d/%m/%Y")
            dt = datetime.strptime(str(today), '%d/%m/%Y')
            week_start = dt - (timedelta(days=dt.weekday()) + timedelta(days=2))
            week_end = week_start + timedelta(days=6)
            total_amount = OrderItem.objects.filter(product__user__agent_user_id=obj.id, suborder__payment_status='PAID', created_at__range=(week_start,week_end)).aggregate(total=Sum('total_price'))['total'] or 0
        elif this_month:
            current_year = date.today().year
            current_month = date.today().month
            first = first_date_of_current_month(current_year, current_month)
            last = last_date_of_month(current_year, current_month)
            total_amount = OrderItem.objects.filter(product__user__agent_user_id=obj.id, suborder__payment_status='PAID', created_at__range=(first,last)).aggregate(total=Sum('total_price'))['total'] or 0
        else:
            total_amount = OrderItem.objects.filter(product__user__agent_user_id=obj.id, suborder__payment_status='PAID').aggregate(total=Sum('total_price'))['total'] or 0

        return total_amount


class FarmerOwnPaymentListSerializer(serializers.ModelSerializer):
    order_items = serializers.SerializerMethodField('get_order_items')

    class Meta:
        model = PaymentHistory
        fields = ['id', 'amount', 'status', 'date', 'order_items']

    def get_order_items(self, obj):
        serializer = ProductItemSerializer(instance=obj.order_items, many=True)
        return serializer.data


class FarmerProductionProductsSerializer(serializers.ModelSerializer):
    quantity = serializers.SerializerMethodField('get_quantity')
    unit = serializers.CharField(source='unit.title')
    date = serializers.SerializerMethodField('get_date')
    class Meta:
        model = Product
        fields = ['id', 'title', 'quantity', 'unit', 'date']

    def get_quantity(self, obj):
        try:
            quantity = 0
            order_items = OrderItem.objects.filter(product=obj.id, is_qc_passed='NEUTRAL')
            for order_item in order_items:
                quantity += order_item.quantity
            return quantity
        except:
            return 0

    def get_date(self, obj):
        today = datetime.today().date()
        return today
    

class AdminCouponSerializer(serializers.ModelSerializer):
    amount = serializers.FloatField(required=True)
    class Meta:
        model = Coupon
        fields = [  'id',
                    'code',
                    'coupon_title',
                    'min_shopping',
                    'amount',
                    'max_time',
                    'start_time',
                    'end_time',
                    'is_active'
                ]
        read_only_fields = ['id', 'usage_count']