from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.permissions import AllowAny
from armaan_bhai.pagination import ProductCustomPagination
from product.serializers import *
from django.db.models import Q
from django.utils import timezone
from product.models import *
from datetime import datetime


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
        district = request.GET.get('district')
        price = request.GET.get('price')
        delivery_start_date = request.GET.get('delivery_start_date')
        delivery_end_date = request.GET.get('delivery_end_date')

        today = timezone.now().date()

        queryset = Product.objects.filter(status="PUBLISH", possible_productions_date__gt=today).order_by('-created_at')

        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(full_description__icontains=query)
            )
            # if queryset.count() == 0:
            #     title_matches = [(product, fuzz.ratio(query, product.title)) for product in Product.objects.all()]
            #     title_matches.sort(key=lambda x: x[1], reverse=True)
            #     top_match = title_matches[0][0]
            #     queryset = Product.objects.filter(title__icontains=top_match.title)

        if category:
            queryset = queryset.filter(category__id=category)

        if sub_category:
            queryset = queryset.filter(sub_category__id=sub_category)

        if status:
            queryset = queryset.filter(status=status)

        if district:
            queryset = queryset.filter(user__district=district)

        if price:
            queryset = queryset.filter(sell_price_per_unit__range=(0,price))

        if delivery_start_date and delivery_end_date:
            queryset = queryset.filter(possible_delivery_date__range=(delivery_start_date,delivery_end_date))

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        # Serialize the products
        serializer = self.get_serializer(page, many=True)

        # Get the category
        category = self.request.GET.get('sub_category_id')
        category_logo = None
        category_logo_url = None

        if category:
            try:
                category_obj = SubCategory.objects.get(id=category)
                category_logo = category_obj.logo.url
                # Create the full URL for the logo
                category_logo_url = request.build_absolute_uri(category_logo)
            except SubCategory.DoesNotExist:
                pass

        # Get the paginated response
        response = self.get_paginated_response(serializer.data)

        # Add category logo URL to the response
        if category_logo_url:
            response.data['logo'] = category_logo_url

        return response

class FarmerProductListAPI(ListAPIView):
    serializer_class = ProductListSerializer
    pagination_class = ProductCustomPagination
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
        request = self.request
        status = request.GET.get('status')
        own_product = request.GET.get('own_product')
        user = self.request.user
        if own_product is not None:
            return Product.objects.filter(user=user).order_by('-created_at')
        if user.user_type == "AGENT":
            queryset = Product.objects.filter(user__agent_user_id=user.id).order_by('-created_at')
        elif user.user_type == "FARMER":
            queryset = Product.objects.filter(user=user).order_by('-created_at')
        else:
            queryset = Product.objects.all().order_by('-created_at')

        if status:
            queryset = queryset.filter(status=status)
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


class CustomerBestSellingProductListAPI(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = BestSellingProductListSerializer

    def get_queryset(self):
        today = timezone.now().date()
        queryset = Product.objects.filter(status='PUBLISH', possible_productions_date__gt=today).order_by('-sell_count')

        return queryset
    

class AdminOffersListAPIView(ListAPIView):
    serializer_class = AdminOfferSerializer
    pagination_class = ProductCustomPagination

    def get_queryset(self):
        if self.request.user.user_type == "ADMIN" or self.request.user.user_type == "AGENT": 
            today_date = timezone.now().date()
            queryset = Offer.objects.filter(
                end_date__gte=today_date, is_active=True).order_by('-created_at')
            if queryset:
                return queryset
            else:
                raise ValidationError(
                    {"msg": 'Offers does not exist!'})
        else:
            raise ValidationError(
                {"msg": 'You can not view offers list, because you are not an Admin or an Agent!'})


class AdminOfferCreateAPIView(CreateAPIView):
    serializer_class = AdminOfferSerializer

    def post(self, request, *args, **kwargs):
        if self.request.user.user_type == "ADMIN" or self.request.user.user_type == "AGENT":
            return super(AdminOfferCreateAPIView, self).post(request, *args, **kwargs)
        else:
            raise ValidationError(
                {"msg": 'You can not create Offers, because you are not an Admin or an Agent!'})
        

class AdminOfferUpdateAPIView(UpdateAPIView):
    serializer_class = AdminOfferSerializer
    lookup_field = 'id'
    lookup_url_kwarg = "id"

    def get_queryset(self):
        id = self.kwargs['id']
        if self.request.user.user_type == "ADMIN" or self.request.user.user_type == "AGENT":
            query = Offer.objects.filter(id=id)
            if query:
                return query
            else:
                raise ValidationError(
                    {"msg": 'Offer does not exist!'})
        else:
            raise ValidationError(
                {"msg": 'You can not update Offer, because you are not an Admin or an Agent!'})


class AdminOfferUpdateDetailsAPIView(RetrieveAPIView):
    serializer_class = AdminOfferSerializer
    lookup_field = 'id'
    lookup_url_kwarg = "id"

    def get_queryset(self):
        id = self.kwargs['id']
        if self.request.user.user_type == "ADMIN" or self.request.user.user_type == "AGENT":
            query = Offer.objects.filter(id=id)
            if query:
                return query
            else:
                raise ValidationError(
                    {"msg": 'Offer does not exist!'})
        else:
            raise ValidationError(
                {"msg": 'You can not see Update details, because you are not an Admin or an Admin or an Agent!'})
        

class AdminOfferDeleteAPIView(ListAPIView):
    pagination_class = ProductCustomPagination
    serializer_class = AdminOfferSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'id'

    def get_queryset(self):
        id = self.kwargs['id']
        if self.request.user.user_type == "ADMIN" or self.request.user.user_type == "AGENT":
            offer_obj = Offer.objects.filter(id=id).exists()
            if offer_obj:
                Offer.objects.filter(id=id).update(is_active=False)
                queryset = Offer.objects.filter(
                    is_active=True).order_by('-created_at')
                return queryset
            else:
                raise ValidationError(
                    {"msg": 'Offer data Does not exist!'}
                )
        else:
            raise ValidationError(
                {"msg": 'You can not delete Offer data, because you are not an Admin or an Agent!'})


class OffersListAPIView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = AdminOfferSerializer

    def get_queryset(self):
        today_date = datetime.today()
        queryset = Offer.objects.filter(
            end_date__gte=today_date, is_active=True).order_by('-created_at')
        if queryset:
            return queryset
        else:
            raise ValidationError({"msg": "No offers available! "})
        

class OfferDetailsAPIView(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = AdminOfferSerializer
    lookup_field = 'id'
    lookup_url_kwarg = "id"

    def get_object(self):
        offer_id = self.kwargs['id']
        try:
            query = Offer.objects.get(id=offer_id)
            return query
        except:
            raise ValidationError({"details": "Offer doesn't exist!"})
        

class OfferProductsListAPIView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ProductListSerializer
    pagination_class = ProductCustomPagination
    lookup_field = 'id'
    lookup_url_kwarg = "id"

    def get_queryset(self):
        # work with dynamic pagination page_size
        try:
            pagination = self.kwargs['pagination']
        except:
            pagination = 10
        self.pagination_class.page_size = pagination

        id = self.kwargs['id']

        today = timezone.now().date()
        # queryset = Product.objects.filter(status="PUBLISH", possible_productions_date__gt=today).order_by('-created_at')

        products = []
        offer_obj = Offer.objects.get(id=id)
        offer_products = OfferProduct.objects.filter(offer=offer_obj)
        for offer_product in offer_products:
            products.append(offer_product.product.id)

        if products:
            queryset = Product.objects.filter(
                id__in=products, status='PUBLISH', possible_productions_date__gt=today).order_by('-created_at')
        else:
            queryset = []

        return queryset
    

class OfferProductsAllListAPIView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = OfferProductListSerializer

    def get_queryset(self):
        today = timezone.now().date()
        products = []
        offers = Offer.objects.filter(end_date__gt=today, is_active=True).order_by('-created_at')[:1]
        offer_products = OfferProduct.objects.filter(offer__in=offers)
        for offer_product in offer_products:
            products.append(offer_product.product.id)

        if products:
            queryset = Product.objects.filter(
                id__in=products, status='PUBLISH', possible_productions_date__gt=today).order_by('-created_at')
        else:
            queryset = []

        return queryset
    

class AdminProductListForOfferCreateAPI(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer

    def get_queryset(self):
        offer_id = self.request.GET.get('offer_id')
        today = timezone.now().date()
        product_list = [p.id for p in Product.objects.filter(
            status='PUBLISH', possible_productions_date__gt=today).order_by('-created_at')]

        active_offers_products_list = [p.product.id for p in OfferProduct.objects.filter(
            is_active=True, offer__is_active=True, offer__end_date__gte=datetime.today()
        )]

        offers_products_list = [p.product.id for p in
                                OfferProduct.objects.filter(offer=offer_id, is_active=True)] if offer_id else []

        list_joined = [i for i in product_list if
                       i not in active_offers_products_list] + (
            offers_products_list if offers_products_list else list())

        return Product.objects.filter(id__in=list_joined).order_by(
            '-created_at') if list_joined else []


class AdminCategoryListAPIView(ListAPIView):
    serializer_class = AdminCategorySerializer
    pagination_class = ProductCustomPagination

    def get_queryset(self):
        if self.request.user.user_type == "ADMIN":
            queryset = Category.objects.filter(is_active=True).order_by('-created_at')
            if queryset:
                return queryset
            else:
                raise ValidationError(
                    {"msg": 'Category does not exist!'})
        else:
            raise ValidationError(
                {"msg": 'You can not view Category list, because you are not an Admin!'})


class AdminSubCategoryListAPIView(ListAPIView):
    serializer_class = AdminSubCategorySerializer
    pagination_class = ProductCustomPagination

    def get_queryset(self):
        if self.request.user.user_type == "ADMIN":
            queryset = SubCategory.objects.filter(is_active=True).order_by('-created_at')
            if queryset:
                return queryset
            else:
                raise ValidationError(
                    {"msg": 'Sub Category does not exist!'})
        else:
            raise ValidationError(
                {"msg": 'You can not view Sub Category list, because you are not an Admin!'})
        

class AdminCategoryUpdateDetailsAPIView(RetrieveAPIView):
    serializer_class = AdminCategorySerializer
    lookup_field = 'id'
    lookup_url_kwarg = "id"

    def get_queryset(self):
        id = self.kwargs['id']
        if self.request.user.user_type == "ADMIN":
            query = Category.objects.filter(id=id)
            if query:
                return query
            else:
                raise ValidationError(
                    {"msg": 'Category does not exist!'})
        else:
            raise ValidationError(
                {"msg": 'You can not see Update details, because you are not an Admin!'})
        

class AdminSubCategoryUpdateDetailsAPIView(RetrieveAPIView):
    serializer_class = AdminSubCategorySerializer
    lookup_field = 'id'
    lookup_url_kwarg = "id"

    def get_queryset(self):
        id = self.kwargs['id']
        if self.request.user.user_type == "ADMIN":
            query = SubCategory.objects.filter(id=id)
            if query:
                return query
            else:
                raise ValidationError(
                    {"msg": 'Sub Category does not exist!'})
        else:
            raise ValidationError(
                {"msg": 'You can not see Update details, because you are not an Admin!'})
        

class AdminCategoryUpdateAPIView(UpdateAPIView):
    serializer_class = AdminCategorySerializer
    lookup_field = 'id'
    lookup_url_kwarg = "id"

    def get_queryset(self):
        id = self.kwargs['id']
        if self.request.user.user_type == "ADMIN":
            query = Category.objects.filter(id=id)
            if query:
                return query
            else:
                raise ValidationError(
                    {"msg": 'Category does not exist!'})
        else:
            raise ValidationError(
                {"msg": 'You can not update Category, because you are not an Admin!'})
        

class AdminSubCategoryUpdateAPIView(UpdateAPIView):
    serializer_class = AdminSubCategorySerializer
    lookup_field = 'id'
    lookup_url_kwarg = "id"

    def get_queryset(self):
        id = self.kwargs['id']
        if self.request.user.user_type == "ADMIN":
            query = SubCategory.objects.filter(id=id)
            if query:
                return query
            else:
                raise ValidationError(
                    {"msg": 'Sub Category does not exist!'})
        else:
            raise ValidationError(
                {"msg": 'You can not update Sub Category, because you are not an Admin!'})
        

class AdminCategoryDeleteAPIView(ListAPIView):
    pagination_class = ProductCustomPagination
    serializer_class = AdminCategorySerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'id'

    def get_queryset(self):
        id = self.kwargs['id']
        if self.request.user.user_type == "ADMIN":
            category_obj = Category.objects.filter(id=id).exists()
            if category_obj:
                Category.objects.filter(id=id).update(is_active=False)
                queryset = Category.objects.filter(
                    is_active=True).order_by('-created_at')
                return queryset
            else:
                raise ValidationError(
                    {"msg": 'Category data Does not exist!'}
                )
        else:
            raise ValidationError(
                {"msg": 'You can not delete Category data, because you are not an Admin!'})
        

class AdminSubCategoryDeleteAPIView(ListAPIView):
    pagination_class = ProductCustomPagination
    serializer_class = AdminSubCategorySerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'id'

    def get_queryset(self):
        id = self.kwargs['id']
        if self.request.user.user_type == "ADMIN":
            sub_category_obj = SubCategory.objects.filter(id=id).exists()
            if sub_category_obj:
                SubCategory.objects.filter(id=id).update(is_active=False)
                queryset = SubCategory.objects.filter(
                    is_active=True).order_by('-created_at')
                return queryset
            else:
                raise ValidationError(
                    {"msg": 'Sub Category data Does not exist!'}
                )
        else:
            raise ValidationError(
                {"msg": 'You can not delete Sub Category data, because you are not an Admin!'})