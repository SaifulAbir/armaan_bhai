from django.contrib import admin
# Register your models here.
from order.models import *

admin.site.register(DeliveryAddress)
admin.site.register(Order)
admin.site.register(SubOrder)
admin.site.register(OrderItem)
