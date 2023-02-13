from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.permissions import AllowAny
from armaan_bhai.pagination import ProductCustomPagination
from product.serializers import *
from django.db.models import Q


class ProductCreateAPIView(CreateAPIView):
    serializer_class = ProductCreateSerializer

    def post(self, request, *args, **kwargs):
        return super(ProductCreateAPIView, self).post(request, *args, **kwargs)


class CustomerProductListAPI(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    pagination_class = ProductCustomPagination

    def get_queryset(self):
        request = self.request
        query = request.GET.get('search')
        category = request.GET.get('category_id')
        sub_category = request.GET.get('sub_category_id')
        status = request.GET.get('status')

        queryset = Product.objects.all().order_by('-created_at')

        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(full_description__icontains=query)
            )

        if category:
            queryset = queryset.filter(category__id=category)

        if sub_category:
            queryset = queryset.filter(sub_category__id=sub_category)

        if status:
            queryset = queryset.filter(status=status)

        return queryset


class FarmerProductListAPI(ListAPIView):
    serializer_class = ProductListSerializer
    lookup_field = 'fid'
    lookup_url_kwarg = "fid"

    def get_queryset(self):
        farmer_id = self.kwargs['fid']
        queryset = Product.objects.filter(user=farmer_id).order_by('-created_at')
        return queryset


class AgentProductListAPI(ListAPIView):
    serializer_class = ProductListSerializer
    pagination_class = ProductCustomPagination

    def get_queryset(self):
        user = self.request.user
        if user.user_type == "AGENT":
            queryset = Product.objects.filter(user__agent_user_id=user.id).order_by('-created_at')
        else:
            queryset = None
        return queryset


class ProductViewAPI(RetrieveAPIView):
    serializer_class = ProductViewSerializer
    lookup_field = 'slug'
    lookup_url_kwarg = "slug"

    def get_object(self):
        slug = self.kwargs['slug']
        query = Product.objects.get(slug=slug)
        return query


class CustomerProductViewAPI(RetrieveAPIView):
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


class PublishProductUpdateAPIView(UpdateAPIView):
    serializer_class = PublishProductSerializer
    lookup_field = 'slug'
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        slug = self.kwargs['slug']
        query = Product.objects.filter(slug=slug)
        return query


class CategoryListAPIView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CategoryListSerializer

    def get_queryset(self):
        queryset = Category.objects.filter(is_active=True)
        return queryset


class SubCategoryListAPIView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = SubCategoryListSerializer
    lookup_field = 'cid'
    lookup_url_kwarg = "cid"

    def get_queryset(self):
        cid = self.kwargs['cid']
        queryset = SubCategory.objects.filter(category=cid, is_active=True).order_by('-created_at')
        return queryset


class CategoryListAPIView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CategoryListSerializer

    def get_queryset(self):
        queryset = Category.objects.filter(is_active=True)
        return queryset


class UnitListAPIView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = UnitListSerializer

    def get_queryset(self):
        queryset = Units.objects.filter(is_active=True)
        return queryset