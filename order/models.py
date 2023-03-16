from django.db import models
# Create your models here.
from django.db.models.signals import pre_save
from django.utils import timezone
from armaan_bhai.models import AbstractTimeStamp
from order.utils import unique_order_id_generator_for_order, unique_order_id_generator_for_suborder
from product.models import Product
from user.models import User, Division, District, Upazilla
from django.utils import timezone
from django.core.validators import MinValueValidator


class DeliveryAddress(AbstractTimeStamp):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(
        max_length=100, null=False, blank=False, default='')
    address = models.CharField(
        max_length=100, null=False, blank=False, default='')
    phone = models.CharField(max_length=255, null=True, blank=True, default='')
    email = models.CharField(max_length=255, null=True, blank=True, default='')
    division = models.ForeignKey(Division, on_delete=models.PROTECT)
    district = models.ForeignKey(District, on_delete=models.PROTECT)
    upazilla = models.ForeignKey(Upazilla, on_delete=models.PROTECT)
    default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'DeliveryAddress'
        verbose_name_plural = 'DeliveryAddresses'
        db_table = 'delivery_addresses'

    def __str__(self):
        return f"{self.name}"

#
# class PaymentType(AbstractTimeStamp):
#     type_name = models.CharField(max_length=50)
#     note = models.TextField(null=True, blank=True, default='')
#     status = models.BooleanField(default=True)
#
#     class Meta:
#         verbose_name = 'PaymentType'
#         verbose_name_plural = 'PaymentTypes'
#         db_table = 'payment_types'
#
#     def __str__(self):
#         return f"{self.type_name}"


class Setting(AbstractTimeStamp):
    vat = models.FloatField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = 'Setting'
        verbose_name_plural = 'Settings'
        db_table = 'settings'

    def __str__(self):
        return f"{self.vat}"


class Coupon(AbstractTimeStamp):
    code = models.CharField(max_length=15)
    coupon_title = models.CharField(max_length=255, null=False, blank=False)
    min_shopping = models.IntegerField(default=0, null=True, blank=True)
    amount = models.FloatField(
        max_length=255, null=True, blank=True, default=0, help_text="Amount Coupon")
    max_time = models.IntegerField(default=0, null=False, blank=False)
    usage_count = models.IntegerField(default=0, null=True, blank=True)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Coupon'
        verbose_name_plural = 'Coupons'
        db_table = 'coupons'

    def __str__(self):
        return self.code


class Order(AbstractTimeStamp):
    ORDER_CHOICES = [
        ('ON_PROCESS', 'On Process'),
        ('CANCELED', 'Canceled'),
        ('ON_TRANSIT', 'On Transit'),
        ('DELIVERED', 'Delivered'),
    ]

    PAYMENT_STATUSES = [
        ('DUE', 'Due'),
        ('PAID', 'Paid'),
        ('REFUNDED', 'Refunded'),
    ]

    PAYMENT_TYPES = [
        ('COD', 'Cash on Delivery'),
        ('PG', 'Payment Gateway'),
    ]

    QC_TYPES = [
        ('NEUTRAL', 'Neutral'),
        ('PASS', 'Pass'),
        ('FAIL', 'Fail'),
    ]

    order_id = models.SlugField(null=False, blank=False, allow_unicode=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT,
                             related_name='order_user', blank=True, null=True)
    product_count = models.IntegerField()
    farmer = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='order_farmer', blank=True, null=True)
    total_price = models.DecimalField(max_digits=19, decimal_places=2)
    refund = models.BooleanField(default=False)
    order_date = models.DateField(auto_now_add=True)
    coupon = models.ForeignKey(
        Coupon, on_delete=models.SET_NULL, blank=True, null=True)
    coupon_discount_amount = models.FloatField(
        max_length=255, null=True, blank=True)
    coupon_status = models.BooleanField(default=False)
    vat_amount = models.FloatField(max_length=255, null=True, blank=True)
    vat_percentage = models.FloatField(max_length=255, null=True, blank=True)
    # shipping_cost = models.FloatField(max_length=255, null=True, blank=True)
    # shipping_class = models.ForeignKey(
    #     ShippingClass, on_delete=models.SET_NULL, blank=True, null=True)
    payment_status = models.CharField(
        max_length=20, null=False, blank=False, choices=PAYMENT_STATUSES, default=PAYMENT_STATUSES[0][0])
    payment_type = models.CharField(
        max_length=20, null=False, blank=False, choices=PAYMENT_STATUSES, default=PAYMENT_TYPES[0][0])
    cash_on_delivery = models.BooleanField(default=False)
    order_status = models.CharField(
        max_length=20, null=False, blank=False, choices=ORDER_CHOICES, default=ORDER_CHOICES[0][0])
    delivery_address = models.ForeignKey(
        DeliveryAddress, on_delete=models.CASCADE)
    # delivery_agent = models.CharField(max_length=100, null=True, blank=True)
    delivery_date = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    is_qc_passed = models.CharField(
        max_length=20, choices=QC_TYPES, default=QC_TYPES[0][0])
    pickup_request = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        db_table = 'orders'

    def __str__(self):
        return self.order_id


def pre_save_order(sender, instance, *args, **kwargs):
    if not instance.order_id:
        instance.order_id = 'ar-' + \
            str(unique_order_id_generator_for_order(instance))


pre_save.connect(pre_save_order, sender=Order)


class PickupLocation(AbstractTimeStamp):
    address = models.TextField()
    division = models.ForeignKey(Division, on_delete=models.PROTECT)
    district = models.ForeignKey(District, on_delete=models.PROTECT)
    upazilla = models.ForeignKey(Upazilla, on_delete=models.PROTECT)
    status = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'PickupLocation'
        verbose_name_plural = 'PickupLocations'
        db_table = 'pickup_locations'

    def __str__(self):
        return self.address


class AgentPickupLocation(AbstractTimeStamp):
    user = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='agent_pickup_location')
    pickup_location = models.ForeignKey(
        PickupLocation, on_delete=models.PROTECT, related_name='pickup_location_agent')
    status = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'AgentPickupLocation'
        verbose_name_plural = 'AgentPickupLocations'
        db_table = 'agent_pickup_locations'

    def __str__(self):
        return self.pickup_location.address


class SubOrder(AbstractTimeStamp):
    ORDER_CHOICES = [
        ('ON_PROCESS', 'On Process'),
        ('CANCELED', 'Canceled'),
        ('ON_TRANSIT', 'On Transit'),
        ('DELIVERED', 'Delivered'),
    ]

    PAYMENT_STATUSES = [
        ('DUE', 'Due'),
        ('PAID', 'Paid'),
        ('REFUNDED', 'Refunded'),
    ]

    PAYMENT_TYPES = [
        ('COD', 'Cash on Delivery'),
        ('PG', 'Payment Gateway'),
    ]

    QC_TYPES = [
        ('NEUTRAL', 'Neutral'),
        ('PASS', 'Pass'),
        ('FAIL', 'Fail'),
    ]

    order = models.ForeignKey(Order, on_delete=models.PROTECT,
                              related_name='order_suborder', blank=True, null=True)
    suborder_number = models.SlugField(
        null=False, blank=False, allow_unicode=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT,
                             related_name='suborder_user', blank=True, null=True)
    product_count = models.IntegerField()
    farmer = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='suborder_farmer', blank=True, null=True)
    total_price = models.DecimalField(max_digits=19, decimal_places=2)
    refund = models.BooleanField(default=False)
    order_date = models.DateField(auto_now_add=True)
    coupon = models.ForeignKey(
        Coupon, on_delete=models.SET_NULL, blank=True, null=True)
    coupon_discount_amount = models.FloatField(
        max_length=255, null=True, blank=True)
    coupon_status = models.BooleanField(default=False)
    vat_amount = models.FloatField(max_length=255, null=True, blank=True)
    vat_percentage = models.FloatField(max_length=255, null=True, blank=True)
    # shipping_cost = models.FloatField(max_length=255, null=True, blank=True)
    # shipping_class = models.ForeignKey(
    #     ShippingClass, on_delete=models.SET_NULL, blank=True, null=True)
    payment_status = models.CharField(
        max_length=20, null=False, blank=False, choices=PAYMENT_STATUSES, default=PAYMENT_STATUSES[0][0])
    payment_type = models.CharField(
        max_length=20, null=False, blank=False, choices=PAYMENT_STATUSES, default=PAYMENT_TYPES[0][0])
    cash_on_delivery = models.BooleanField(default=False)
    order_status = models.CharField(
        max_length=20, null=False, blank=False, choices=ORDER_CHOICES, default=ORDER_CHOICES[0][0])
    delivery_address = models.ForeignKey(
        DeliveryAddress, on_delete=models.CASCADE)
    # delivery_agent = models.CharField(max_length=100, null=True, blank=True)
    delivery_date = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    is_qc_passed = models.CharField(
        max_length=20, choices=QC_TYPES, default=QC_TYPES[0][0])
    pickup_request = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Sub Order'
        verbose_name_plural = 'Sub Orders'
        db_table = 'sub_orders'

    def __str__(self):
        return self.suborder_number


def pre_save_suborder(sender, instance, *args, **kwargs):
    if not instance.suborder_number:
        instance.suborder_number = 'ar-' + \
            str(unique_order_id_generator_for_suborder(instance))


pre_save.connect(pre_save_suborder, sender=SubOrder)


class OrderItem(AbstractTimeStamp):
    QC_TYPES = [
        ('NEUTRAL', 'Neutral'),
        ('PASS', 'Pass'),
        ('FAIL', 'Fail'),
    ]
    paymentStatus = [
        ('NONE', 'None'),
        ('DUE', 'Due'),
        ('PAID', 'Paid')
        
    ]

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='order_item_order', blank=True, null=True)
    suborder = models.ForeignKey(
        SubOrder, on_delete=models.CASCADE, related_name='order_item_suborder', blank=True, null=True)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, null=False, blank=False, related_name='order_item_product')
    quantity = models.IntegerField(default=1)
    unit_price = models.FloatField(
        max_length=255, null=False, blank=False, default=0)
    total_price = models.FloatField(
        max_length=255, null=False, blank=False, default=0)
    is_qc_passed = models.CharField(
        max_length=20, choices=QC_TYPES, default=QC_TYPES[0][0])
    pickup_location = models.ForeignKey(
        PickupLocation, on_delete=models.CASCADE, null=True, blank=True, related_name='order_item_pickup_location')
    agent = models.ForeignKey(User, on_delete=models.CASCADE,
                              related_name='order_item_agent', null=True, blank=True)
    payment_status = models.CharField(
        max_length=20, null=False, blank=False, choices=paymentStatus, default='NONE')
    

    @property
    def subtotal(self):
        total_item_price = self.quantity * self.product.price_per_unit
        return total_item_price

    class Meta:
        verbose_name = 'OrderItem'
        verbose_name_plural = 'OrderItems'
        db_table = 'order_items'

    def __str__(self):
        return f"{self.quantity} of {self.product.title}" + ' - ' + str(self.product.user.id)

    def get_total_item_price(self):
        return self.quantity * self.product.price_per_unit


class CouponStat(AbstractTimeStamp):
    coupon = models.ForeignKey(
        Coupon, on_delete=models.CASCADE, related_name='coupon')
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='coupon_stat_order')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='user')

    class Meta:
        verbose_name = 'CouponStat'
        verbose_name_plural = 'CouponStats'
        db_table = 'coupon_stats'

    def __str__(self):
        return f"{self.pk}"


class FarmerAccountInfo(AbstractTimeStamp):
    PAYMENT_CHOICES = [
        ('BANK_ACCOUNT', 'Bank Account'),
        ('MFS', 'Mobile Financial Services'),
    ]
    account_type = models.CharField(
        max_length=20, null=True, blank=True, choices=PAYMENT_CHOICES)
    account_number = models.CharField(max_length=100, null=True, blank=True)
    account_holder = models.CharField(max_length=100, null=True, blank=True)
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    brunch_name = models.CharField(max_length=100, null=True, blank=True)
    Mobile_number = models.CharField(max_length=100, null=True, blank=True)
    farmer = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='farmer_account_info')
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='agent_account_info')

    class Meta:
        verbose_name = 'Farmer Account Info'
        verbose_name_plural = 'Farmer Account Info'
        db_table = 'farmer_account_info'

    def __str__(self):
        return self.account_type


class PaymentHistory(models.Model):
    STATUS_CHOICES = [
        ('DUE', 'Due'),
        ('PAID', 'Paid'),
    ]
    farmer_account_info = models.ForeignKey(
        FarmerAccountInfo,
        on_delete=models.CASCADE,
        related_name='payments',
    )
    order_items = models.ManyToManyField(
        OrderItem,
        related_name='payments',
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    farmer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payments',
    )
    status = models.CharField(
        max_length=4,
        choices=STATUS_CHOICES,
        default='DUE',
    )
    date = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = 'Payment_history'
        verbose_name_plural = 'Payments_history'
        db_table = 'payments_history'
