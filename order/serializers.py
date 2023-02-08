from rest_framework import serializers
from order.models import DeliveryAddress, OrderItem, Order, CouponStat, Coupon, PickupLocation, AgentPickupLocation
from product.models import Inventory, Product
from user.serializers import CustomerProfileDetailSerializer


class DeliveryAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAddress
        fields = ['id', 'user', 'name', 'address', 'phone', 'email', 'city']

    def create(self, validated_data):
        address_instance = DeliveryAddress.objects.create(**validated_data, user=self.context['request'].user)
        return address_instance


class ProductItemCheckoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id',
                  'product',
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
            for order_item in order_items:
                product = order_item['product']
                quantity = order_item['quantity']
                unit_price = order_item['unit_price']
                total_price = float(unit_price) * float(quantity)
                OrderItem.objects.create(order=order_instance, product=product, quantity=int(
                    quantity), unit_price=unit_price, total_price=total_price)

                # update inventory
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
        'coupon_discount_amount', 'total_price']


class CustomerOrderListSerializer(serializers.ModelSerializer):
    user = CustomerProfileDetailSerializer(many=False, read_only=True)
    order_item_order = ProductItemCheckoutSerializer(many=True, read_only=True)
    delivery_address = DeliveryAddressSerializer(many=False, read_only=True)
    class Meta:
        model = Order
        fields = ['id', 'user', 'order_id', 'order_date', 'delivery_date', 'order_status', 'order_item_order', 'delivery_address', 'payment_type',
        'coupon_discount_amount', 'total_price']


class AgentOrderListSerializer(serializers.ModelSerializer):
    user = CustomerProfileDetailSerializer(many=False, read_only=True)
    order_item_order = ProductItemCheckoutSerializer(many=True, read_only=True)
    delivery_address = DeliveryAddressSerializer(many=False, read_only=True)
    class Meta:
        model = Order
        fields = ['id', 'user', 'order_id', 'order_date', 'delivery_date', 'order_status', 'order_item_order', 'delivery_address', 'payment_type',
        'coupon_discount_amount', 'total_price']


# Pickup Location
class PickupLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupLocation
        fields = ['address', 'division', 'district', 'upazilla']


class PickupLocationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupLocation
        fields = ['id', 'address', 'division', 'district', 'upazilla', 'created_at']


# Agent Pickup Location
class AgentPickupLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentPickupLocation
        fields = ['user', 'pickup_location']


class AgentPickupLocationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentPickupLocation
        fields = ['id', 'user', 'pickup_location', 'created_at']