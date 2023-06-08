import decimal

from rest_framework import serializers
from order.models import DeliveryAddress, OrderItem, Order, CouponStat, Coupon, PickupLocation, AgentPickupLocation, \
    FarmerAccountInfo, SubOrder, PaymentHistory, Setting
from product.models import Inventory, Product
from product.serializers import ProductViewSerializer
from user.models import User, AgentFarmer
from datetime import datetime, timedelta
from user.serializers import CustomerProfileDetailSerializer, DivisionSerializer, DistrictSerializer, UpazillaSerializer
from django.utils import timezone
from django.db.models import Sum
from django.db.models import Q
from django.db.models.functions import Coalesce, Round
from rest_framework.exceptions import ValidationError
from datetime import date
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from decimal import Decimal
from itertools import groupby


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
                  'unit_price',
                  'commission'
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
        coupon = validated_data.get('coupon')
        coupon_status = validated_data.get('coupon_status')
        coupon_discount_amount = validated_data.get('coupon_discount_amount', 0.0)

        if payment_type == 'PG':
            order_instance = Order.objects.create(
                **validated_data, user=self.context['request'].user, payment_status='PAID', order_status='ON_PROCESS')
        else:
            order_instance = Order.objects.create(
                **validated_data, user=self.context['request'].user, payment_status='DUE', order_status='ON_PROCESS')

        # Calculate the delivery charge for the suborder
        delivery_charge = 0
        delivery_charges = Setting.objects.filter(is_active=True).order_by('id')[:1]
        for delivery_char in delivery_charges:
            delivery_charge = delivery_char.delivery_charge

            print(delivery_charge, "charge")

        if order_items:
            suborders = {}
            for order_item in order_items:
                product = order_item['product']
                quantity = order_item['quantity']
                unit_price = order_item['unit_price']
                try:
                    agent_commission = order_item['commission']
                except:
                    agent_commission = 0.0

                suborder_instance_count = 0
                total_discount_amount = validated_data.get('coupon_discount_amount', 0.0)
                num_suborders = len(order_items)
                sub_discount_amount = total_discount_amount / num_suborders
                print(sub_discount_amount)

                total_price = float(unit_price) * float(quantity)
                print(total_price,"price")
                if int(quantity) > product.quantity:
                    raise ValidationError("Ordered quantity is greater than inventory")

                suborder_key = product.possible_delivery_date  # Use product delivery date as suborder key
                suborder_obj = suborders.get(suborder_key)
                if not suborder_obj:
                    if payment_type == 'PG':
                        suborder_obj = SubOrder.objects.create(order=order_instance,
                                                               user=self.context['request'].user,
                                                               product_count=1,
                                                               total_price=total_price,
                                                               delivery_address=validated_data.get('delivery_address'),
                                                               delivery_date=product.possible_delivery_date,
                                                               payment_status='PAID',
                                                               delivery_charge=delivery_charge,
                                                               order_status='ON_PROCESS',
                                                               coupon=coupon,
                                                               coupon_discount_amount=coupon_discount_amount,
                                                               coupon_status=coupon_status,
                                                               divided_discount_amount=sub_discount_amount)
                    else:
                        suborder_obj = SubOrder.objects.create(order=order_instance,
                                                               user=self.context['request'].user,
                                                               product_count=1,
                                                               total_price=total_price,
                                                               delivery_address=validated_data.get('delivery_address'),
                                                               delivery_date=product.possible_delivery_date,
                                                               payment_status='DUE',
                                                               delivery_charge=delivery_charge,
                                                               order_status='ON_PROCESS',
                                                               coupon=coupon,
                                                               coupon_discount_amount=coupon_discount_amount,
                                                               coupon_status=coupon_status,
                                                               divided_discount_amount=sub_discount_amount)
                    suborders[suborder_key] = suborder_obj
                else:
                    suborder_obj.total_price += total_price
                    suborder_obj.product_count += 1
                    suborder_obj.save()
                OrderItem.objects.create(order=order_instance, suborder=suborder_obj, product=product,
                                         quantity=int(quantity), unit_price=unit_price, total_price=total_price, commission=agent_commission, commission_total=float(agent_commission)*float(quantity))

                if order_instance:
                    product_obj = Product.objects.filter(id=product.id)
                    inventory_obj = Inventory.objects.filter(product=product).latest('created_at')
                    update_quantity = int(inventory_obj.current_quantity) - int(quantity)
                    product_obj.update(quantity=update_quantity)
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
                        coupon=coupon, user=self.context['request'].user, order=order_instance)
                    usage_count = int(coupon.usage_count)
                    coupon_obj.update(usage_count=usage_count + 1)
                else:
                    raise serializers.ValidationError("Usage limit exceeded")
            else:
                raise serializers.ValidationError("Usage limit exceeded")
            return order_instance

        # send email to the user
        user = self.context['request'].user
        email = user.email
        if email:
            order_id = order_instance.order_id
            created_at = order_instance.created_at.strftime("%Y-%m-%d")
            payment_type = order_instance.payment_type
            sub_total = OrderItem.objects.filter(order=order_instance).aggregate(total=Sum('total_price'))[
                            'total'] or 0.0

            order_items = OrderItem.objects.filter(order=order_instance)
            subject = "Your order has been successfully placed."
            html_message = render_to_string('order_details.html',
                                            {
                                                'email': email,
                                                'order_id': order_id,
                                                'created_at': created_at,
                                                'order_items': order_items,
                                                'payment_type': payment_type,
                                                'sub_total': sub_total if sub_total else 0.0,
                                                'total': sub_total + 60.0 if sub_total else 0.0
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
    total_delivery_charges = serializers.SerializerMethodField('get_delivery_charges')
    total_price = serializers.SerializerMethodField('get_total_price')
    class Meta:
        model = Order
        fields = ['id', 'user', 'order_id', 'order_date', 'delivery_date', 'order_status', 'order_item_order', 'delivery_address', 'payment_type', 'coupon', 'coupon_discount_amount', 'coupon_status', 'total_price', 'is_qc_passed', 'total_delivery_charges']

    def get_delivery_charges(self, obj):
        suborders = SubOrder.objects.filter(order_id=obj.id)
        delivery_charges_sum = suborders.aggregate(Sum('delivery_charge'))['delivery_charge__sum'] or 0
        print(delivery_charges_sum, "Delivery Tanvir")
        return delivery_charges_sum
    def get_total_price(self, order):
        total_price = order.total_price or 0
        total_price += Decimal(self.get_delivery_charges(order))
        if order.coupon_discount_amount:
            total_price -= Decimal(order.coupon_discount_amount)
        return total_price


class OrderUpdateSerializer(serializers.ModelSerializer):
    user = CustomerProfileDetailSerializer(many=False, read_only=True)
    order_item_suborder = ProductItemCheckoutSerializer(many=True, read_only=True)
    delivery_address = DeliveryAddressSerializer(many=False, read_only=True)
    class Meta:
        model = SubOrder
        fields = ['is_qc_passed', 'delivery_address', 'order_item_suborder', 'user', 'order_status', 'payment_status']


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
    total_price = serializers.SerializerMethodField('get_total_price')
    farmer_total_price = serializers.SerializerMethodField('get_farmer_total_price')
    class Meta:
        model = SubOrder
        fields = ['id', 'user', 'order_number', 'suborder_number', 'order_date', 'delivery_date', 'order_status', 'order_status_value', 'order_item_suborder', 'delivery_address', 'payment_type',
        'coupon_discount_amount', 'total_price', 'payment_status', 'payment_status_value', 'delivery_charge', 'divided_discount_amount', 'farmer_total_price']

    def get_total_price(self, suborder):
        total_price = suborder.total_price + Decimal(suborder.delivery_charge)
        if suborder.divided_discount_amount:
            total_price -= Decimal(suborder.divided_discount_amount)
        return total_price

    def get_farmer_total_price(self, suborder):
        user = self.context['request'].user
        if user.is_authenticated:
            # Get the order items associated with the suborder and belong to the authenticated user
            order_items = suborder.order_item_suborder.filter(product__user=user)
            # Calculate the total price based on the order items' unit prices and quantities
            order_items_total = sum(item.product.price_per_unit * item.quantity for item in order_items)
            return Decimal(order_items_total)

        return suborder.total_price or Decimal('0')


class AgentOrderListSerializer(serializers.ModelSerializer):
    order_status_value = serializers.CharField(
        source='get_order_status_display', read_only=True
    )
    user = CustomerProfileDetailSerializer(many=False, read_only=True)
    # order_item_suborder = ProductItemCheckoutSerializer(many=True, read_only=True)
    delivery_address = DeliveryAddressSerializer(many=False, read_only=True)
    total_price = serializers.SerializerMethodField('get_total_price')
    farmer_total_price = serializers.SerializerMethodField('get_farmer_total_price')
    class Meta:
        model = SubOrder
        # fields = ['id', 'user', 'order', 'suborder_number', 'order_date', 'delivery_date', 'order_status', 'payment_status', 'order_status_value', 'order_item_suborder', 'delivery_address', 'payment_type',
        # 'coupon_discount_amount', 'total_price', 'is_qc_passed']
        fields = ['id', 'user', 'order', 'suborder_number', 'order_date', 'delivery_date', 'order_status', 'payment_status', 'order_status_value', 'delivery_address', 'payment_type', 'total_price', 'farmer_total_price']

    def get_total_price(self, suborder):
        total_price = suborder.total_price or Decimal('0')
        delivery_charge = suborder.delivery_charge or Decimal('0')

        total_price += Decimal(delivery_charge)

        if suborder.divided_discount_amount:
            total_price -= Decimal(suborder.divided_discount_amount)

        return total_price

    def get_farmer_total_price(self, suborder):
        user = self.context['request'].user
        if user.is_authenticated:
            # Get the order items associated with the suborder and belong to the authenticated user
            order_items = suborder.order_item_suborder.filter(product__user=user)
            # Calculate the total price based on the order items' unit prices and quantities
            order_items_total = sum(item.product.price_per_unit * item.quantity for item in order_items)
            return Decimal(order_items_total)

        return suborder.total_price or Decimal('0')


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
class PickupLocationInfoUpdateSerializer(serializers.ModelSerializer):
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
                SubOrder.objects.filter(order_item_suborder__product__user=instance.id, order_item_suborder__product__possible_productions_date = tomorrow).update(order_status='CANCELED')

        return super().update(instance, validated_data)
    

class QcPassedInfoUpdateSerializer(serializers.ModelSerializer):
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

        today = datetime.today()
        if pickup_location:
            OrderItem.objects.filter(product__user = instance.id, product__possible_productions_date = today).update(pickup_location=pickup_location)
        if is_qc_passed:
            OrderItem.objects.filter(product__user = instance.id, product__possible_productions_date = today).update(is_qc_passed=is_qc_passed)

        if Order.objects.filter(order_item_order__product__user=instance.id, order_item_order__product__possible_productions_date = today).exists():
            if is_qc_passed == 'PASS':
                Order.objects.filter(order_item_order__product__user=instance.id, order_item_order__product__possible_productions_date = today).update(order_status='ON_TRANSIT')
            if is_qc_passed == 'FAIL':
                Order.objects.filter(order_item_order__product__user=instance.id, order_item_order__product__possible_productions_date = today).update(order_status='CANCELED')
        if SubOrder.objects.filter(order_item_suborder__product__user=instance.id, order_item_suborder__product__possible_productions_date = today).exists():
            if is_qc_passed == 'PASS':
                SubOrder.objects.filter(order_item_suborder__product__user=instance.id, order_item_suborder__product__possible_productions_date = today).update(order_status='ON_TRANSIT')
            if is_qc_passed == 'FAIL':
                SubOrder.objects.filter(order_item_suborder__product__user=instance.id, order_item_suborder__product__possible_productions_date = today).update(order_status='CANCELED')

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
                  'commission'
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
        query = Product.objects.filter(Q(user = obj), Q(possible_productions_date=tomorrow), Q(order_item_product__isnull=False) ).annotate(whole_quantity=Sum('order_item_product__quantity', filter=Q(order_item_product__suborder__order_status='ON_PROCESS') | Q(order_item_product__suborder__order_status='ON_TRANSIT') | Q(order_item_product__suborder__order_status='CANCELED')))
        serializer = AgentMukamLocationSetupDataSerializer(instance=query, many=True)
        return serializer.data

    def get_pickup_location(self, obj):
        tomorrow = datetime.today() + timedelta(days=1)
        query = OrderItem.objects.filter(Q(product__user = obj), Q(product__possible_productions_date=tomorrow), Q(suborder__order_status='ON_PROCESS') | Q(suborder__order_status='ON_TRANSIT') | Q(suborder__order_status='CANCELED')).distinct('pickup_location')
        for i in query:
            if i.pickup_location:
                pickup_location = i.pickup_location.id
                return pickup_location

    def get_is_qc_passed(self, obj):
        tomorrow = datetime.today() + timedelta(days=1)
        query = OrderItem.objects.filter(Q(product__user = obj), Q(product__possible_productions_date=tomorrow), Q(suborder__order_status='ON_PROCESS') | Q(suborder__order_status='ON_TRANSIT') | Q(suborder__order_status='CANCELED')).distinct('is_qc_passed')
        for i in query:
            is_qc_passed = i.is_qc_passed
            return is_qc_passed
        

class AgentOrderListForSetupQcPassedSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField('get_products')
    pickup_location = serializers.SerializerMethodField()
    is_qc_passed = serializers.SerializerMethodField()
    location_title = serializers.SerializerMethodField('get_location_title')
    class Meta:
        model = User
        fields = ['id', 'full_name', 'phone_number', 'products', 'pickup_location', 'location_title', 'is_qc_passed']

    def get_products(self, obj):
        today = datetime.today()
        query = Product.objects.filter(Q(user = obj), Q(possible_productions_date=today), Q(order_item_product__isnull=False) ).annotate(whole_quantity=Sum('order_item_product__quantity', filter=Q(order_item_product__suborder__order_status='ON_PROCESS') | Q(order_item_product__suborder__order_status='ON_TRANSIT') | Q(order_item_product__suborder__order_status='CANCELED')))
        serializer = AgentMukamLocationSetupDataSerializer(instance=query, many=True)
        return serializer.data

    def get_pickup_location(self, obj):
        today = datetime.today()
        query = OrderItem.objects.filter(Q(product__user = obj), Q(product__possible_productions_date=today), Q(suborder__order_status='ON_PROCESS') | Q(suborder__order_status='ON_TRANSIT') | Q(suborder__order_status='CANCELED')).distinct('pickup_location')
        for i in query:
            if i.pickup_location:
                pickup_location = i.pickup_location.id
                return pickup_location
            
    def get_location_title(self, obj):
        today = datetime.today()
        query = OrderItem.objects.filter(Q(product__user = obj), Q(product__possible_productions_date=today), Q(suborder__order_status='ON_PROCESS') | Q(suborder__order_status='ON_TRANSIT') | Q(suborder__order_status='CANCELED')).distinct('pickup_location')
        for i in query:
            if i.pickup_location:
                pickup_location = i.pickup_location.address
                return pickup_location

    def get_is_qc_passed(self, obj):
        today = datetime.today()
        query = OrderItem.objects.filter(Q(product__user = obj), Q(product__possible_productions_date=today), Q(suborder__order_status='ON_PROCESS') | Q(suborder__order_status='ON_TRANSIT') | Q(suborder__order_status='CANCELED')).distinct('is_qc_passed')
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
    farmer_unit_price = serializers.SerializerMethodField('get_farmer_unit_price')
    class Meta:
        model = OrderItem
        fields = ['id', 'product','product_title', 'quantity', 'unit_price','farmer_unit_price', 'total_price', 'is_qc_passed','payment_status']

    def get_product_title(self, obj):
        return obj.product.title
    
    def get_farmer_unit_price(self, obj):
        return obj.product.price_per_unit


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
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

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
        elif start_date and end_date:
            total_amount = OrderItem.objects.filter(product__user__agent_user_id=obj.id, suborder__payment_status='PAID', created_at__range=(start_date,end_date)).aggregate(total=Sum('total_price'))['total'] or 0
        else:
            total_amount = OrderItem.objects.filter(product__user__agent_user_id=obj.id, suborder__payment_status='PAID').aggregate(total=Sum('total_price'))['total'] or 0

        return round(total_amount, 2)


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
    pickup_location = serializers.SerializerMethodField('get_pickup_location')
    pickup_location_address = serializers.SerializerMethodField('get_pickup_location_address')
    class Meta:
        model = Product
        fields = ['id', 'title', 'quantity', 'unit', 'date', 'pickup_location', 'pickup_location_address']

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


    def get_pickup_location(self, obj):
        query = OrderItem.objects.filter(Q(product=obj.id), Q(is_qc_passed='NEUTRAL')).order_by('id').distinct()
        for i in query:
            if i.pickup_location:
                pickup_location = i.pickup_location.id
                return pickup_location

    def get_pickup_location_address(self, obj):
        query = OrderItem.objects.filter(Q(product=obj.id), Q(is_qc_passed='NEUTRAL')).order_by('id').distinct()
        for i in query:
            if i.pickup_location:
                pickup_location_address = i.pickup_location.address
                return pickup_location_address

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

    def create(self, validated_data):
        code_get = validated_data.pop('code')
        if code_get:
            code_get_for_check = Coupon.objects.filter(code=code_get)
            if code_get_for_check:
                raise ValidationError('Code already exists')
            else:
                coupon_instance = Coupon.objects.create(**validated_data, code=code_get)
                return coupon_instance


class AdminCouponUpdateSerializer(serializers.ModelSerializer):
    amount = serializers.FloatField(required=True)
    code = serializers.CharField(required=False)
    coupon_title = serializers.CharField(required=False)
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


class ApplyCouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['id', 'code', 'coupon_title', 'min_shopping', 'amount', 'max_time', 'usage_count', 'start_time', 'end_time', 'is_active']


class WebsiteConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        fields = [
            'id',
            'vat',
            'delivery_charge',
            'is_active'
        ]


# Admin Farmers Payment Summary
class FarmersPaymentSummarySerializer(serializers.ModelSerializer):
    farmer_name = serializers.SerializerMethodField()
    # dates = serializers.SerializerMethodField()
    amounts = serializers.SerializerMethodField()
    products_paid = serializers.SerializerMethodField()
    sub_total_amount = serializers.SerializerMethodField()

    class Meta:
        model = PaymentHistory
        fields = ['farmer_name', 'amounts', 'products_paid', 'sub_total_amount']

    def get_farmer_name(self, obj):
        return obj.farmer_account_info.farmer.full_name

    def get_amounts(self, obj):
        queryset = PaymentHistory.objects.filter(farmer=obj.farmer, status='PAID')

        division_id = self.context['request'].query_params.get('division_id')
        district_id = self.context['request'].query_params.get('district_id')
        upazilla_id = self.context['request'].query_params.get('upazilla_id')
        farmer_name = self.context['request'].query_params.get('farmer_name')
        start_date = self.context['request'].query_params.get('start_date')
        end_date = self.context['request'].query_params.get('end_date')

        if division_id:
            queryset = queryset.filter(farmer__division_id=division_id)

        if district_id:
            queryset = queryset.filter(farmer__district_id=district_id)

        if upazilla_id:
            queryset = queryset.filter(farmer__upazilla_id=upazilla_id)

        if farmer_name:
            queryset = queryset.filter(Q(farmer_account_info__farmer__full_name=farmer_name) | Q(farmer_account_info__farmer__full_name=farmer_name.replace(' ', '')))

        if start_date and end_date:
            queryset = queryset.filter(date__range=(start_date, end_date))

        if not (division_id or district_id or upazilla_id or farmer_name or start_date or end_date):
            # Get the initial date range (last 7 days)
            initial_start_date = datetime.now().date() - timedelta(days=7)
            initial_end_date = datetime.now().date() + timedelta(days=1)

            # Apply the initial date range filter
            queryset = queryset.filter(date__range=(initial_start_date, initial_end_date))

        amounts = queryset.values('date').annotate(total_amount=Sum('amount'))
        return amounts

    # def get_products_paid(self, obj):
    #     # Assuming there is a many-to-many relationship between PaymentHistory and OrderItem
    #     products = obj.order_items.all().values_list('product__title', flat=True).distinct()
    #     return products

    def get_products_paid(self, obj):
        queryset = PaymentHistory.objects.filter(farmer=obj.farmer)

        division_id = self.context['request'].query_params.get('division_id')
        district_id = self.context['request'].query_params.get('district_id')
        upazilla_id = self.context['request'].query_params.get('upazilla_id')
        farmer_name = self.context['request'].query_params.get('farmer_name')
        start_date = self.context['request'].query_params.get('start_date')
        end_date = self.context['request'].query_params.get('end_date')

        if division_id:
            queryset = queryset.filter(farmer__division_id=division_id)

        if district_id:
            queryset = queryset.filter(farmer__district_id=district_id)

        if upazilla_id:
            queryset = queryset.filter(farmer__upazilla_id=upazilla_id)

        if farmer_name:
            queryset = queryset.filter(Q(farmer_account_info__farmer__full_name=farmer_name) | Q(
                farmer_account_info__farmer__full_name=farmer_name.replace(' ', '')))

        if start_date and end_date:
            queryset = queryset.filter(date__range=(start_date, end_date))

        if not (division_id or district_id or upazilla_id or farmer_name or start_date or end_date):
            # Get the initial date range (last 7 days)
            initial_start_date = datetime.now().date() - timedelta(days=7)
            initial_end_date = datetime.now().date() + timedelta(days=1)

            # Apply the initial date range filter
            queryset = queryset.filter(date__range=(initial_start_date, initial_end_date))

        products = queryset.values_list('order_items__product__title', flat=True).distinct()
        return products

    def get_sub_total_amount(self, obj):
        queryset = PaymentHistory.objects.filter(farmer_account_info=obj.farmer_account_info, status='PAID')

        division_id = self.context['request'].query_params.get('division_id')
        district_id = self.context['request'].query_params.get('district_id')
        upazilla_id = self.context['request'].query_params.get('upazilla_id')
        farmer_name = self.context['request'].query_params.get('farmer_name')
        start_date = self.context['request'].query_params.get('start_date')
        end_date = self.context['request'].query_params.get('end_date')

        if division_id:
            queryset = queryset.filter(farmer__division_id=division_id)

        if district_id:
            queryset = queryset.filter(farmer__district_id=district_id)

        if upazilla_id:
            queryset = queryset.filter(farmer__upazilla_id=upazilla_id)

        if farmer_name:
            queryset = queryset.filter(Q(farmer_account_info__farmer__full_name=farmer_name) | Q(farmer_account_info__farmer__full_name=farmer_name.replace(' ', '')))

        if start_date and end_date:
            queryset = queryset.filter(date__range=(start_date, end_date))

        if not (division_id or district_id or upazilla_id or farmer_name or start_date or end_date):
            # Get the initial date range (last 7 days)
            initial_start_date = datetime.now().date() - timedelta(days=7)
            initial_end_date = datetime.now().date() + timedelta(days=1)

            # Apply the initial date range filter
            queryset = queryset.filter(date__range=(initial_start_date, initial_end_date))

        sub_total_amount = queryset.aggregate(sum_amount=Sum('amount'))
        return sub_total_amount['sum_amount']


#admin coupon usage report

class CouponReportSerializer(serializers.ModelSerializer):
    coupon_name = serializers.CharField()
    usage_count = serializers.IntegerField()
    total_discount = serializers.FloatField()
    max_time_use = serializers.IntegerField()

    class Meta:
        model = Coupon
        fields = ['coupon_name', 'max_time_use', 'usage_count', 'total_discount']



# class FarmersPaymentSummarySerializer(serializers.ModelSerializer):
#     farmer_name = serializers.SerializerMethodField()
#     date = serializers.DateField()
#     products_paid = serializers.SerializerMethodField()
#     total_amount = serializers.SerializerMethodField()
#
#     class Meta:
#         model = PaymentHistory
#         fields = ['farmer_name', 'date', 'amount', 'products_paid', 'total_amount']
#
#     def get_farmer_name(self, obj):
#         return obj.farmer_account_info.farmer.full_name
#
#     def get_products_paid(self, obj):
#         # Assuming there is a many-to-many relationship between PaymentHistory and OrderItem
#         products = obj.order_items.all()
#         product_names = [product.product.title for product in products]
#         return product_names
#
#     def get_total_amount(self, obj):
#         total_amount = PaymentHistory.objects.filter(farmer_account_info=obj.farmer_account_info).aggregate(
#             sum_amount=Sum('amount'))
#         return total_amount['sum_amount']
#
#     def to_representation(self, instance):
#         representation = super().to_representation(instance)
#         datewise_payments = []
#         datewise_payment_fields = ['date', 'amount', 'products_paid']
#
#         for field in datewise_payment_fields:
#             if field in representation:
#                 del representation[field]
#
#         for key in representation:
#             if key.startswith('date_wise_payment'):
#                 datewise_payment = {
#                     'date': representation[key]['date'],
#                     'amount': representation[key]['amount'],
#                     'products_paid': representation[key]['products_paid'],
#                 }
#                 datewise_payments.append(datewise_payment)
#
#         return {
#             'farmer_name': representation['farmer_name'],
#             'date_wise_payment': datewise_payments,
#             'total_amount': representation['total_amount'],
#         }

# class FarmersPaymentSummarySerializer(serializers.ModelSerializer):
#     farmer_name = serializers.SerializerMethodField()
#     date = serializers.DateField()
#     products_paid = serializers.SerializerMethodField()
#     total_amount = serializers.SerializerMethodField()
#
#     class Meta:
#         model = PaymentHistory
#         fields = ['farmer_name', 'date', 'amount', 'products_paid', 'total_amount']
#
#     def get_farmer_name(self, obj):
#         return obj.farmer_account_info.farmer.full_name
#
#     def get_products_paid(self, obj):
#         # Assuming there is a many-to-many relationship between PaymentHistory and OrderItem
#         products = obj.order_items.all()
#         product_names = [product.product.title for product in
#                          products]
#         return product_names
#
#     def get_total_amount(self, obj):
#         total_amount = PaymentHistory.objects.filter(farmer_account_info=obj.farmer_account_info).aggregate(
#             sum_amount=Sum('amount'))
#         return total_amount['sum_amount']
#
#     def to_representation(self, instance):
#         representation = super().to_representation(instance)
#         date_wise_payment = {
#             'date': representation['date'],
#             'amount': representation['amount'],
#             'products_paid': representation['products_paid'],
#         }
#         return {
#             'farmer_name': representation['farmer_name'],
#             'date_wise_payment': date_wise_payment,
#             'total_amount': representation['total_amount'],
#         }

        # def create(self, validated_data):
        #     try:
        #         order_items = validated_data.pop('order_item_order')
        #     except KeyError:
        #         raise serializers.ValidationError('Order items are missing')
        #
        #     payment_type = validated_data.get('payment_type')
        #
        #     if payment_type == 'PG':
        #         order_instance = Order.objects.create(
        #             **validated_data, user=self.context['request'].user, payment_status='PAID',
        #             order_status='ON_PROCESS')
        #     else:
        #         order_instance = Order.objects.create(
        #             **validated_data, user=self.context['request'].user, payment_status='DUE',
        #             order_status='ON_PROCESS')
        #
        #     # Retrieve the relevant Setting object
        #     # setting = Setting.objects.get(is_active=True)
        #
        #     # Calculate the delivery charge for the suborder
        #     delivery_charge = 0
        #     delivery_charges = Setting.objects.filter(is_active=True).order_by('id')[:1]
        #     for delivery_char in delivery_charges:
        #         delivery_charge = delivery_char.delivery_charge
        #     print(delivery_charge)
        #     # print(delivery_charge)
        #
        #     if order_items:
        #         suborder_instance_count = 0
        #         total_discount_amount = validated_data.get('coupon_discount_amount', 0.0)
        #         num_suborders = len(order_items)
        #         sub_discount_amount = total_discount_amount / num_suborders
        #         print(sub_discount_amount)
        #
        #         for order_item in order_items:
        #             product = order_item['product']
        #             quantity = order_item['quantity']
        #             unit_price = order_item['unit_price']
        #             total_price = float(unit_price) * float(quantity)
        #
        #             if int(quantity) > product.quantity:
        #                 raise ValidationError("Ordered quantity is greater than inventory")
        #
        #             delivery_date = product.possible_delivery_date
        #
        #             # Check if there's an existing suborder with the same delivery date within the same order
        #             existing_suborder = SubOrder.objects.filter(
        #                 order=order_instance,
        #                 delivery_date=delivery_date
        #             ).first()
        #
        #             if existing_suborder:
        #                 # Add the order item to the existing suborder
        #                 existing_suborder.product_count += 1
        #                 existing_suborder.total_price += decimal.Decimal(total_price)
        #                 existing_suborder.save()
        #
        #             else:
        #                 # Create a new suborder for the unique delivery date
        #                 payment_status = 'PAID' if payment_type == 'PG' else 'DUE'
        #
        #                 suborder_obj = SubOrder.objects.create(
        #                     order=order_instance,
        #                     user=self.context['request'].user,
        #                     product_count=1,
        #                     total_price=total_price,
        #                     delivery_address=validated_data.get('delivery_address'),
        #                     delivery_date=delivery_date,
        #                     payment_status=payment_status,
        #                     order_status='ON_PROCESS',
        #                     delivery_charge=delivery_charge,
        #                     divided_discount_amount=sub_discount_amount
        #                 )
        #
        #                 OrderItem.objects.create(
        #                     order=order_instance,
        #                     suborder=suborder_obj,
        #                     product=product,
        #                     quantity=int(quantity),
        #                     unit_price=unit_price,
        #                     total_price=total_price
        #                 )
        #
        #                 # Update inventory, sell count, etc. (assuming order_instance exists)
        #                 product_obj = Product.objects.filter(id=product.id)
        #                 inventory_obj = Inventory.objects.filter(product=product).latest('created_at')
        #                 update_quantity = int(inventory_obj.current_quantity) - int(quantity)
        #                 product_obj.update(quantity=update_quantity)
        #                 inventory_obj.current_quantity = update_quantity
        #                 inventory_obj.save()
        #
        #                 sell_count = product_obj[0].sell_count + 1
        #                 product_obj.update(sell_count=sell_count)
        #
        #     # apply coupon
        #     try:
        #         coupon_status = validated_data.pop('coupon_status')
        #     except KeyError:
        #         coupon_status = None
        #
        #     if coupon_status == True:
        #         coupon = validated_data.pop('coupon')
        #         if coupon.usage_count != coupon.max_time:
        #             coupon_obj = Coupon.objects.filter(id=coupon.id)
        #             coupon_stat = CouponStat.objects.filter(
        #                 coupon=coupon.id, user=self.context['request'].user).exists()
        #             if not coupon_stat:
        #                 CouponStat.objects.create(
        #                     coupon=coupon, user=self.context['request'].user, order=order_instance)
        #                 usage_count = int(coupon.usage_count)
        #                 coupon_obj.update(usage_count=usage_count + 1)
        #             else:
        #                 raise serializers.ValidationError("Usage limit exceeded")
        #         else:
        #             raise serializers.ValidationError("Usage limit exceeded")
        #
        #     # send email to the user
        #     user = self.context['request'].user
        #     email = user.email
        #     if email:
        #         order_id = order_instance.order_id
        #         created_at = order_instance.created_at.strftime("%Y-%m-%d")
        #         payment_type = order_instance.payment_type
        #         sub_total = OrderItem.objects.filter(order=order_instance).aggregate(total=Sum('total_price'))[
        #                         'total'] or 0.0
        #
        #         order_items = OrderItem.objects.filter(order=order_instance)
        #         subject = "Your order has been successfully placed."
        #         html_message = render_to_string('order_details.html',
        #                                         {
        #                                             'email': email,
        #                                             'order_id': order_id,
        #                                             'created_at': created_at,
        #                                             'order_items': order_items,
        #                                             'payment_type': payment_type,
        #                                             'sub_total': sub_total if sub_total else 0.0,
        #                                             'total': sub_total + 60.0 if sub_total else 0.0
        #                                         })
        #
        #         send_mail(
        #             subject=subject,
        #             message=None,
        #             from_email=settings.EMAIL_HOST_USER,
        #             recipient_list=[email],
        #             html_message=html_message
        #         )
        #
        #         return order_instance
        #     else:
        #         return order_instance



class SellingRevenueReportSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    unit_title = serializers.CharField(source='product.unit.title', read_only=True)
    class Meta:
        model = OrderItem
        fields = ['id',
                  'product_title',
                  'quantity',
                  'unit_title'
                  ]

class AdminSellingRevenueReportSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='user.full_name', read_only=True)
    customer_phone = serializers.CharField(source='user.phone_number', read_only=True)
    products = serializers.SerializerMethodField('get_products')
    class Meta:
        model = SubOrder
        fields = ['id', 'customer_name', 'customer_phone', 'products', 'total_price', 'order_date']

    def get_products(self, obj):
        query = OrderItem.objects.filter(suborder = obj)
        serializer = SellingRevenueReportSerializer(instance=query, many=True)
        return serializer.data


class AdminAgentWiseSaleReportFarmerSerializer(serializers.ModelSerializer):
    commission_per_farmer = serializers.CharField(source='commission_total', read_only=True)
    commission_per_farmer = serializers.SerializerMethodField('get_commission_per_farmer')
    total_sale_amount = serializers.SerializerMethodField('get_total_sale_amount')
    class Meta:
        model = User
        fields = ['id', 'full_name', 'commission_per_farmer', 'total_sale_amount']

    def get_commission_per_farmer(self, obj):
        start_date = self.context['start_date']
        end_date = self.context['end_date']
        agent_id = self.context['agent_id']

        if start_date and end_date:
            filtered_queryset = OrderItem.objects.filter(product__user__agent_user_id=agent_id, suborder__payment_status='PAID', created_at__range=(start_date,end_date))
        else:
            filtered_queryset = OrderItem.objects.filter(product__user__agent_user_id=agent_id, suborder__payment_status='PAID')

        total_sum = filtered_queryset.aggregate(total=Sum('commission_total'))['total'] or 0
        return total_sum

    def get_total_sale_amount(self, obj):
        start_date = self.context['start_date']
        end_date = self.context['end_date']

        if start_date and end_date:
            filtered_queryset = OrderItem.objects.filter(product__user=obj.id, suborder__payment_status='PAID', created_at__range=(start_date,end_date))
        else:
            filtered_queryset = OrderItem.objects.filter(product__user=obj.id, suborder__payment_status='PAID')
        total_sum = filtered_queryset.aggregate(total=  Sum('total_price') )['total'] or 0
        return round(total_sum, 2)

class AdminAgentWiseSaleReportSerializer(serializers.ModelSerializer):
    farmers = serializers.SerializerMethodField('get_farmers')
    # total_product_sale = serializers.SerializerMethodField('get_total_product_sale')
    products = serializers.SerializerMethodField('get_products')
    total_commission = serializers.SerializerMethodField('get_total_commission')
    class Meta:
        model = User
        fields = ['id', 'full_name', 'phone_number', 'farmers',  'products', 'total_commission']

    def get_farmers(self, obj):
        start_date = self.context['request'].query_params.get('start_date')
        end_date = self.context['request'].query_params.get('end_date')

        query = User.objects.filter(user_type='FARMER', agent_user_id=obj.id, is_active=True, product_seller__order_item_product__isnull=False, product_seller__order_item_product__suborder__payment_status='PAID').distinct()
        serializer = AdminAgentWiseSaleReportFarmerSerializer(instance=query, many=True, context={
                                                'request': self.context['request'], 'start_date':start_date, 'end_date':end_date, 'agent_id':obj.id})
        return serializer.data

    def get_products(self, obj):
        start_date = self.context['request'].query_params.get('start_date')
        end_date = self.context['request'].query_params.get('end_date')

        if start_date and end_date:
            query = Product.objects.filter(user__agent_user_id = obj.id, order_item_product__isnull=False, order_item_product__suborder__payment_status='PAID' ).annotate(whole_quantity=Coalesce(Sum('order_item_product__quantity', filter=Q(order_item_product__suborder__order_status='DELIVERED', order_item_product__created_at__range=(start_date,end_date)) ), 0) )
        else:
            query = Product.objects.filter(user__agent_user_id = obj.id, order_item_product__isnull=False, order_item_product__suborder__payment_status='PAID' ).annotate(whole_quantity=Coalesce(Sum('order_item_product__quantity', filter=Q(order_item_product__suborder__order_status='DELIVERED')), 0) )
        serializer = AgentMukamLocationSetupDataSerializer(instance=query, many=True, context={
                                                'request': self.context['request']})
        return serializer.data

    def get_total_commission(self, obj):
        start_date = self.context['request'].query_params.get('start_date')
        end_date = self.context['request'].query_params.get('end_date')

        if start_date and end_date:
            filtered_queryset = OrderItem.objects.filter(product__user__agent_user_id=obj.id, suborder__payment_status='PAID', created_at__range=(start_date,end_date))
        else:
            filtered_queryset = OrderItem.objects.filter(product__user__agent_user_id=obj.id, suborder__payment_status='PAID')
        # print("agent_id2")
        # print(obj.id)
        total_sum = filtered_queryset.aggregate(total=Sum('commission_total'))['total'] or 0
        return total_sum

    # def get_total_product_sale(self, obj):
    #     data = OrderItem.objects.filter(product__user__agent_user_id=obj.id, suborder__payment_status='PAID').count()
    #     return data
