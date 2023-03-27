from django.urls import path
from .apis import *

urlpatterns = [
    # agent and farmer product create
    path('admin/create/product/', ProductCreateAPIView.as_view(), name='create_product'),
    # customer product list
    path('customer/product/list/', CustomerProductListAPI.as_view(), name='product_list'),
    path('admin/farmer-product-list/<int:fid>/', FarmerProductListAPI.as_view()),
    # agent product list
    path('agent/product-list/', AgentProductListAPI.as_view()),
    path('admin/product/view/<str:slug>/', ProductViewAPI.as_view(), name='product_view'),
    path('customer/product/view/<str:slug>/', CustomerProductViewAPI.as_view(), name='customer_product_view'),
    path('admin/product/update/<str:slug>/', ProductUpdateAPIView.as_view(), name='product_view'),
    path('admin/product/publish-or-unpublish/<str:slug>/', PublishProductUpdateAPIView.as_view(), name='product_publish'),
    path('customer/category/list/', CategoryListAPIView.as_view(), name='product_list'),
    path('admin/unit/list/', UnitListAPIView.as_view(), name='unit_list'),
    path('customer/sub-category-list/<int:cid>/', SubCategoryListAPIView.as_view()),

    path('customer/best-selling-product-list/', CustomerBestSellingProductListAPI.as_view()),
]