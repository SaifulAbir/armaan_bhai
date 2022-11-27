from django.urls import path
from .apis import *

urlpatterns = [
    path('create/product/', ProductCreateAPIView.as_view(), name='create_product'),
    path('product/list/', ProductListAPI.as_view(), name='product_list'),
]