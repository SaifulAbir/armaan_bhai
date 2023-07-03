from django.urls import path
from .apis import *

urlpatterns = [
    # agent and farmer product create
    path('admin/create/product/', ProductCreateAPIView.as_view(), name='create_product'),
    # customer product list
    path('customer/product/list/', CustomerProductListAPI.as_view(), name='product_list'),
    path('customer/product/dropdown/list/', ProductListDropdownAPI.as_view(), name='product_list_dropdown'),
    path('admin/farmer-product-list/<int:fid>/', FarmerProductListAPI.as_view()),
    # agent product list
    path('agent/product-list/', AgentProductListAPI.as_view()),
    path('admin/product/view/<str:slug>/', ProductViewAPI.as_view(), name='product_view'),
    path('customer/product/view/<str:slug>/', CustomerProductViewAPI.as_view(), name='customer_product_view'),
    path('admin/product/update/<str:slug>/', ProductUpdateAPIView.as_view(), name='product_view'),
    path('admin/product/publish-or-unpublish/<str:slug>/', PublishProductUpdateAPIView.as_view(), name='product_publish'),
    path('customer/category/list/', CategoryListAPIView.as_view(), name='product_list'),
    path('customer/sub-category-list/<int:cid>/', SubCategoryListAPIView.as_view()),

    path('customer/best-selling-product-list/', CustomerBestSellingProductListAPI.as_view()),

    path('offer-products-all-list/', OfferProductsAllListAPIView.as_view()),

    path('admin/offers-list/', AdminOffersListAPIView.as_view()),
    path('admin/offer-create/', AdminOfferCreateAPIView.as_view()),
    path('admin/product-list-for-offer-create/', AdminProductListForOfferCreateAPI.as_view()),
    path('admin/offer-update/<int:id>/', AdminOfferUpdateAPIView.as_view()),
    path('admin/offer-update-details/<int:id>/', AdminOfferUpdateDetailsAPIView.as_view()),
    path('admin/offers-delete/<int:id>/', AdminOfferDeleteAPIView.as_view()),

    path('admin/category-create/', AdminCategoryCreateAPIView.as_view()),
    path('admin/sub-category-create/', AdminSubCategoryCreateAPIView.as_view()),
    path('admin/category-list/', AdminCategoryListAPIView.as_view()),
    path('admin/sub-category-list/<int:id>/', AdminSubCategoryListAPIView.as_view()),
    path('admin/category-update-details/<int:id>/', AdminCategoryUpdateDetailsAPIView.as_view()),
    path('admin/sub-category-update-details/<int:id>/', AdminSubCategoryUpdateDetailsAPIView.as_view()),
    path('admin/category-update/<int:id>/', AdminCategoryUpdateAPIView.as_view()),
    path('admin/sub-category-update/<int:id>/', AdminSubCategoryUpdateAPIView.as_view()),
    path('admin/category-delete/<int:id>/', AdminCategoryDeleteAPIView.as_view()),
    path('admin/sub-category-delete/<int:id>/', AdminSubCategoryDeleteAPIView.as_view()),

    path('admin/unit/list/', UnitListAPIView.as_view(), name='unit_list'),
    path('admin/unit-create/', AdminUnitCreateAPIView.as_view()),
    path('admin/unit-delete/<int:id>/', AdminUnitDeleteAPIView.as_view()),
]