import decimal

from rest_framework import serializers
from order.models import DeliveryAddress, OrderItem, Order, CouponStat, Coupon, PickupLocation, AgentPickupLocation, \
    FarmerAccountInfo, SubOrder, PaymentHistory
from product.models import Inventory, Product
from product.serializers import ProductViewSerializer
from user.models import User
from datetime import datetime, timedelta
from user.serializers import CustomerProfileDetailSerializer, DivisionSerializer, DistrictSerializer, UpazillaSerializer
from django.utils import timezone
from django.db.models import Sum
from django.db.models import Q


class DeliveryAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAddress
        fields = ['id', 'user', 'name', 'address', 'phone', 'email', 'district', 'division', 'upazilla']

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
    product_title = serializers.CharField(source='product.title', read_only=True)
    possible_production_date = serializers.CharField(source='product.possible_productions_date', read_only=True)
    product_obj = ProductViewSerializer(source='product', read_only=True)
    pickup_location_title = serializers.CharField(source='pickup_location.address', read_only=True)
    class Meta:
        model = OrderItem
        fields = ['id',
                  'product',
                  'product_obj',
                  'quantity',
                  'unit_price',
                  'pickup_location',
                  'pickup_location_title',
                  'is_qc_passed',
                  'possible_production_date'
                  ]
        queryset = OrderItem.objects.filter(is_qc_passed='PASS')


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

        # if order_items:
        #     for order_item in order_items:
        #         product = order_item['product']
        #         quantity = order_item['quantity']
        #         unit_price = order_item['unit_price']
        #         total_price = float(unit_price) * float(quantity)
        #         OrderItem.objects.create(order=order_instance, product=product, quantity=int(
        #             quantity), unit_price=unit_price, total_price=total_price)
        #
        #         # delivery date
        #         order_instance.delivery_date = product.possible_delivery_date
        #         order_instance.save()
        #
        #         # update inventory
        #         if order_instance:
        #             product_obj = Product.objects.filter(id=product.id)
        #             inventory_obj = Inventory.objects.filter(product=product).latest('created_at')
        #             update_quantity = int(inventory_obj.current_quantity) - int(quantity)
        #             product_obj.update(quantity = update_quantity)
        #             inventory_obj.current_quantity = update_quantity
        #             inventory_obj.save()
        #
        #             # product sell count
        #             sell_count = product_obj[0].sell_count + 1
        #             product_obj.update(sell_count=sell_count)

        if order_items:
            suborder_instance_count = 0
            for order_item in order_items:
                product = order_item['product']
                quantity = order_item['quantity']
                unit_price = order_item['unit_price']
                total_price = float(unit_price) * float(quantity)
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
    class Meta:
        model = SubOrder
        fields = ['id', 'user', 'order', 'suborder_number', 'order_date', 'delivery_date', 'order_status', 'order_status_value', 'order_item_suborder', 'delivery_address', 'payment_type',
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
        #     Order.objects.filter(id=instance.order.id).update(is_qc_passed=is_qc_passed)
            if is_qc_passed == 'PASS':
                Order.objects.filter(order_item_order__product__user=instance.id, order_item_order__product__possible_productions_date = tomorrow).update(order_status='ON_TRANSIT')
        if SubOrder.objects.filter(order_item_suborder__product__user=instance.id, order_item_suborder__product__possible_productions_date = tomorrow).exists():
        #     SubOrder.objects.filter(id=instance.suborder.id).update(is_qc_passed=is_qc_passed)
            if is_qc_passed == 'PASS':
                SubOrder.objects.filter(order_item_suborder__product__user=instance.id, order_item_suborder__product__possible_productions_date = tomorrow).update(order_status='ON_TRANSIT')

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
        query = Product.objects.filter(user = obj, possible_productions_date=tomorrow).annotate(whole_quantity=Sum('order_item_product__quantity', filter=Q(order_item_product__suborder__order_status='ON_PROCESS') | Q(order_item_product__suborder__order_status='ON_TRANSIT')))
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
    class Meta:
        model = Product
        fields = ['id',
                  'title',
                  'whole_quantity',
                  'product_unit_title',
                  'possible_productions_date',
                  'product_seller_title',
                  'product_seller_number'
                  ]
    def get_whole_quantity(self, obj):
        try:
            return obj.whole_quantity
        except:
            return 0


class AdminOrdersListByPickupPointsListSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField('get_products')
    # pickup_location = serializers.SerializerMethodField()
    is_qc_passed = serializers.SerializerMethodField()
    # farmer = serializers.SerializerMethodField('get_farmer')

    class Meta:
        model = PickupLocation
        fields = [
            'id', 'address', 'is_qc_passed', 'products'
        ]

    # def get_farmer(self, obj):
    #     serializer = UserSerializer(instance=obj.farmer, many=False)
    #     return serializer.data

    # def get_order_items(self, obj):
    #     serializer = ProductItemSerializer(instance=obj, many=True)
    #
    #     return serializer.data
    def get_products(self, obj):
        query = Product.objects.filter(possible_productions_date=datetime.today()).annotate(
            whole_quantity=Sum('order_item_product__quantity',
                               filter=Q(
                                   order_item_product__suborder__order_status='ON_TRANSIT')))
        serializer = AdminOrderListByLocationSerializer(instance=query, many=True)
        return serializer.data

    def get_is_qc_passed(self, obj):
        query = OrderItem.objects.filter(Q(pickup_location=obj),
                                         Q(product__possible_productions_date=datetime.today()),
                                         Q(suborder__order_status='ON_TRANSIT'), Q(is_qc_passed='PASS'))
        # print("dev")
        # print(query)
        for i in query:
            is_qc_passed = i.is_qc_passed
            return is_qc_passed

class ProductItemSerializer(serializers.ModelSerializer):
    product_title = serializers.SerializerMethodField('get_product_title')
    class Meta:
        model = OrderItem
        fields = ['id', 'product','product_title', 'quantity', 'unit_price', 'is_qc_passed']
    
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

    class Meta:
        model = PaymentHistory
        fields = ['id','farmer', 'farmer_account_info', 'order_items', 'amount', 'status', 'date']

    def get_farmer_account_info(self, obj):
        serializer = PaymentDetailsSerializer(instance=obj.farmer_account_info, many=False)
        return serializer.data

    def get_order_items(self, obj):
        serializer = ProductItemSerializer(instance=obj.order_items, many=True)

        return serializer.data
    
    def get_farmer(self, obj):
        serializer = UserSerializer(instance=obj.farmer, many=False)
        return serializer.data
