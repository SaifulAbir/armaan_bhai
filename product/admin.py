from django.contrib import admin
from product.models import *


admin.site.register(Category)
admin.site.register(SubCategory)
admin.site.register(Units)
admin.site.register(Product)
admin.site.register(Inventory)
admin.site.register(ProductImage)
admin.site.register(ProductionStep)
