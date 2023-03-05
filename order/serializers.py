import decimal

from rest_framework import serializers
from order.models import DeliveryAddress, OrderItem, Order, CouponStat, Coupon, PickupLocation, AgentPickupLocation, \
    FarmerAccountInfo, SubOrder
from product.models import Inventory, Product
from product.serializers import ProductViewSerializer
from user.models import User
from datetime import datetime, timedelta
from user.serializers import CustomerProfileDetailSerializer, DivisionSerializer, DistrictSerializer, UpazillaSerializer


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
    class Meta:
        model = OrderItem
        fields = ['id',
                  'product',
                  'product_title',
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
    delivery_address = DeliveryAddressSerializer(many=False, read_only=True)
    order_status_value = serializers.CharField(
        source='get_order_status_display', read_only=True
    )
    class Meta:
        model = SubOrder
        fields = ['id', 'user', 'order', 'suborder_number', 'order_date', 'delivery_date', 'order_status', 'order_status_value', 'order_item_suborder', 'delivery_address', 'payment_type',
        'coupon_discount_amount', 'total_price']


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


class PickupLocationQcPassedInfoUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'pickup_location', 'is_qc_passed']


# payment method
class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerAccountInfo
        fields = ['id', 'account_type', 'account_number', 'account_holder', 'bank_name', 'brunch_name', 'Mobile_number',
                  'farmer', 'created_by']

    def create(self, validated_data):
        farmer_account_info = FarmerAccountInfo.objects.create(**validated_data, user=self.context['request'].user)
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

class AgentOrderListForSetupPickupLocationSerializer(serializers.ModelSerializer):
    order_items = serializers.SerializerMethodField('get_order_items')
    pickup_location = serializers.SerializerMethodField('get_pickup_location')
    is_qc_passed = serializers.SerializerMethodField('get_is_qc_passed')
    class Meta:
        model = User
        fields = ['id', 'full_name', 'phone_number', 'order_items', 'pickup_location', 'is_qc_passed']

    def get_order_items(self, obj):
        tomorrow = datetime.today() + timedelta(days=1)
        # suborder__delivery_date__date
        query=OrderItem.objects.filter(product__user__id = obj.id, product__possible_productions_date=tomorrow, suborder__order_status='ON_PROCESS', suborder__is_qc_passed=False)
        serializer = ProductItemCheckoutSerializer(instance=query, many=True)
        return serializer.data

    def get_pickup_location(self, obj):
        tomorrow = datetime.today() + timedelta(days=1)
        query=OrderItem.objects.filter(product__user__id = obj.id, product__possible_productions_date=tomorrow, suborder__order_status='ON_PROCESS', suborder__is_qc_passed=False)
        serializer = SetPickupPointSerializer(instance=query, many=True)
        return serializer.data

    def get_is_qc_passed(self, obj):
        tomorrow = datetime.today() + timedelta(days=1)
        query=OrderItem.objects.filter(product__user__id = obj.id, product__possible_productions_date=tomorrow, suborder__order_status='ON_PROCESS', suborder__is_qc_passed=False)
        serializer = QcPassSerializer(instance=query, many=True)
        return serializer.data
    
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
