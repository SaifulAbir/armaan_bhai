from django.urls import path
from .apis import *

urlpatterns = [
    path('admin/create/product/', ProductCreateAPIView.as_view(), name='create_product'),
    path('customer/product/list/', CustomerProductListAPI.as_view(), name='product_list'),
    path('admin/farmer-product-list/<int:fid>/', FarmerProductListAPI.as_view()),
    path('admin/product/view/<str:slug>/', ProductViewAPI.as_view(), name='product_view'),
    path('admin/product/update/<str:slug>/', ProductUpdateAPIView.as_view(), name='product_view'),
    path('customer/category/list/', CategoryListAPIView.as_view(), name='product_list'),
    path('admin/unit/list/', UnitListAPIView.as_view(), name='unit_list'),
    path('customer/sub-category-list/<int:cid>/', SubCategoryListAPIView.as_view()),
]