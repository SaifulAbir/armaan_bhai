from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.permissions import AllowAny
from armaan_bhai.pagination import ProductCustomPagination
from product.serializers import *


class ProductCreateAPIView(CreateAPIView):
    serializer_class = ProductCreateSerializer

    def post(self, request, *args, **kwargs):
        return super(ProductCreateAPIView, self).post(request, *args, **kwargs)


class ProductListAPI(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    pagination_class = ProductCustomPagination

    def get_queryset(self):
        queryset = Product.objects.filter().order_by('-created_at')
        return queryset


class ProductViewAPI(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductViewSerializer
    lookup_field = 'slug'
    lookup_url_kwarg = "slug"

    def get_object(self):
        slug = self.kwargs['slug']
        query = Product.objects.get(slug=slug)
        return query


class ProductUpdateAPIView(UpdateAPIView):
    serializer_class = ProductUpdateSerializer
    lookup_field = 'slug'
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        slug = self.kwargs['slug']
        query = Product.objects.filter(slug=slug)
        return query
