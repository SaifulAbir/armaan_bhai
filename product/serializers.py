from rest_framework import serializers
from product.models import Product, Category, SubCategory, Units, Inventory, ProductImage, ProductionStep, Offer, OfferProduct
from user.models import User, Division, District, Upazilla
from order.models import Setting
from user.serializers import FarmerListSerializer, FarmerListForBestSellingSerializer
from rest_framework.exceptions import ValidationError
from django.db.models import Sum
from django.utils import timezone




class ProductionStepSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductionStep
        fields = ['id',
                  'step',
                  'image',
                  'step_date',
                  ]

class ProductionStepSerializerForProductUpdate(serializers.ModelSerializer):
    image = serializers.FileField(required=False)

    class Meta:
        model = ProductionStep
        fields = ['id',
                  'step',
                  'image',
                  'step_date',
                  ]


class ProductImageSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductImage
        fields = ['id',
                  'file',
                  'product',
                  'is_active',
                  ]


class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'title', 'is_active', 'logo']


class SubCategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = ['id', 'title', 'category', 'logo']


class DivisionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Division
        fields = ['id', 'name']


class DistrictListSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ['id', 'name', 'division']


class UpazillaListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Upazilla
        fields = ['id', 'name', 'district']


class UnitListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Units
        fields = ['id', 'title', 'is_active']


class ProductCreateSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False)
    production_steps = ProductionStepSerializer(many=True, required=False)
    product_images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'title',
            'category',
            'sub_category',
            'unit',
            'product_images',
            'images',
            'user',
            'thumbnail',
            'price_per_unit',
            'full_description',
            'quantity',
            'possible_productions_date',
            'possible_delivery_date',
            'production_steps'
        ]

    def create(self, validated_data):
        # product images
        try:
            product_images = validated_data.pop('images')
        except:
            product_images = None

        # production steps
        try:
            production_steps = validated_data.pop('production_steps')
        except:
            production_steps = None

        # get vat from settings 
        vat_value = 0
        vat_values = Setting.objects.filter(is_active=True).order_by('id')[:1]
        for vat_v in vat_values:
            vat_value = vat_v.vat


        # create product
        if not (self.context['request'].user.user_type == 'FARMER' or self.context['request'].user.user_type == 'AGENT' or self.context['request'].user.user_type == 'ADMIN' ):
            raise serializers.ValidationError("Product only will be uploaded by agent or farmer or admin")
        else:
            if self.context['request'].user.user_type == 'FARMER':
                product_instance = Product.objects.create(**validated_data, user=self.context['request'].user, vat=vat_value, created_by=self.context['request'].user )
            else:
                product_instance = Product.objects.create(**validated_data, vat=vat_value, created_by=self.context['request'].user)

        # old logic 
        # if not (self.context['request'].user.user_type == 'FARMER' or self.context['request'].user.user_type == 'AGENT'):
        #     raise serializers.ValidationError("Product only will be uploaded by agent or farmer")
        # elif self.context['request'].user.user_type == 'FARMER':
        #     product_instance = Product.objects.create(**validated_data, user=self.context['request'].user)
        # else:
        #     farmer = validated_data.get('user')
        #     if farmer:
        #         product_instance = Product.objects.create(**validated_data)
        #     else:
        #         raise serializers.ValidationError("Farmer id is missing")

        # product inventory
        try:
            quantity = validated_data["quantity"]
        except:
            quantity = None
        if quantity:
            Product.objects.filter(id=product_instance.id).update(total_quantity=quantity)
            # create inventory
            Inventory.objects.create(product=product_instance, initial_quantity=quantity,
                                     current_quantity=quantity)

        # update status and sell_price_per_unit
        Product.objects.filter(id=product_instance.id).update(status='PUBLISH')
        try:
            price_per_unit = validated_data["price_per_unit"]
        except:
            price_per_unit = None
        if price_per_unit:
            Product.objects.filter(id=product_instance.id).update(price_per_unit=price_per_unit, sell_price_per_unit=price_per_unit)

        # product_images
        if product_images:
            for image in product_images:
                ProductImage.objects.create(
                    product=product_instance, file=image)

        # production steps
        if production_steps:
            for step in production_steps:
                ProductionStep.objects.create(
                    product=product_instance, image=step['image'], step_date=step['step_date'], step=step['step'])
        return product_instance


class RelatedProductInfo(serializers.ModelSerializer):
    sell_price_per_unit = serializers.SerializerMethodField('get_sell_price_with_vat')
    class Meta:
        model = Product
        fields = [
            'id',
            'title',
            'slug',
            'category',
            'sub_category',
            'thumbnail',
            'sell_price_per_unit'
        ]

    def get_sell_price_with_vat(self, obj):
        vat = obj.vat / 100.0 if obj.vat else 0
        return round(obj.sell_price_per_unit * (1 + vat), 2)


class ProductListSerializer(serializers.ModelSerializer):
    production_steps = ProductionStepSerializer(many=True, read_only=True)
    product_images = ProductImageSerializer(many=True, read_only=True)
    user = FarmerListSerializer(many=False, read_only=True)
    category = CategoryListSerializer(many=False, read_only=True)
    sub_category = SubCategoryListSerializer(many=False, read_only=True)
    unit = UnitListSerializer(many=False, read_only=True)
    related_products = serializers.SerializerMethodField('get_related_products')
    sell_price_per_unit = serializers.SerializerMethodField('get_sell_price_with_vat')
    # offer_price = serializers.SerializerMethodField('get_sell_after_offer')

    class Meta:
        model = Product
        fields = [
            'id',
            'title',
            'slug',
            'category',
            'sub_category',
            'unit',
            'product_images',
            'thumbnail',
            'price_per_unit',
            'full_description',
            'quantity',
            'total_quantity',
            'user',
            'possible_productions_date',
            'possible_delivery_date',
            'production_steps',
            'sell_price_per_unit',
            'status',
            'sell_count',
            'created_at',
            'related_products'
        ]

    def get_related_products(self, obj):
        try:
            queryset = Product.objects.filter(
                sub_category=obj.sub_category.id, status='PUBLISH', quantity__gt = 0)
            serializer = RelatedProductInfo(instance=queryset, many=True, context={'request': self.context['request']})
            return serializer.data
        except:
            return []

    def get_sell_price_with_vat(self, obj):
        sell_price = obj.sell_price_per_unit

        # Check if there is an active offer for the product
        offer = OfferProduct.objects.filter(product=obj, offer__is_active=True, offer__end_date__gte=timezone.now()).first()

        if offer:
            discount_type = offer.offer.discount_price_type
            discount_value = offer.offer.discount_price

            if discount_type == 'per':
                offer_price = (1 - (discount_value / 100)) * sell_price
            elif discount_type == 'flat':
                offer_price = sell_price - discount_value
            else:
                offer_price = sell_price

            vat = obj.vat
            if vat is not None:
                sell_price_with_vat = offer_price * (1 + vat/100)
                return round(sell_price_with_vat, 2)
            else:
                return round(offer_price, 2)
        else:
            vat = obj.vat
            if vat is not None:
                sell_price_with_vat = sell_price * (1 + vat/100)
                return round(sell_price_with_vat, 2)
            else:
                return round(sell_price, 2)


    # def get_sell_price_with_vat(self, obj):
    #     vat = obj.vat  # assuming vat is defined in the Product model
    #     sell_price = obj.sell_price_per_unit
    #     if vat is not None:
    #         sell_price_with_vat = sell_price * (1 + vat / 100)
    #         return round(sell_price_with_vat, 2)
    #     else:
    #         return sell_price


class ProductViewSerializer(serializers.ModelSerializer):
    production_steps = ProductionStepSerializer(many=True, read_only=True)
    product_images = ProductImageSerializer(many=True, read_only=True)
    user = FarmerListSerializer(many=False, read_only=True)
    category_title = serializers.CharField(source="category.title", read_only=True)
    related_products = serializers.SerializerMethodField('get_related_products')
    sell_price_per_unit = serializers.SerializerMethodField('get_sell_price_with_vat')

    class Meta:
        model = Product
        fields = [
            'id',
            'title',
            'slug',
            'category',
            'category_title',
            'sub_category',
            'unit',
            'product_images',
            'thumbnail',
            'price_per_unit',
            'sell_price_per_unit',
            'full_description',
            'quantity',
            'total_quantity',
            'user',
            'possible_productions_date',
            'possible_delivery_date',
            'production_steps',
            'related_products',
            'vat'
        ]

    def get_sell_price_with_vat(self, obj):
        sell_price = obj.sell_price_per_unit

        # Check if there is an active offer for the product
        offer = OfferProduct.objects.filter(product=obj, offer__is_active=True,
                                            offer__end_date__gte=timezone.now()).first()

        if offer:
            discount_type = offer.offer.discount_price_type
            discount_value = offer.offer.discount_price

            if discount_type == 'per':
                offer_price = (1 - (discount_value / 100)) * sell_price
            elif discount_type == 'flat':
                offer_price = sell_price - discount_value
            else:
                offer_price = sell_price

            vat = obj.vat
            if vat is not None:
                sell_price_with_vat = offer_price * (1 + vat / 100)
                return round(sell_price_with_vat, 2)
            else:
                return round(offer_price, 2)
        else:
            vat = obj.vat
            if vat is not None:
                sell_price_with_vat = sell_price * (1 + vat / 100)
                return round(sell_price_with_vat, 2)
            else:
                return round(sell_price, 2)

    def get_related_products(self, obj):
        try:
            today = timezone.now().date()
            queryset = Product.objects.filter(
                sub_category=obj.sub_category.id, status='PUBLISH', quantity__gt = 0,
                possible_productions_date__gt=today).exclude(id=obj.id)
            serializer = RelatedProductInfo(instance=queryset, many=True, context={'request': self.context['request']})
            return serializer.data
        except:
            return []


class ProductUpdateSerializer(serializers.ModelSerializer):
    title = serializers.CharField(required=False)
    full_description = serializers.CharField(required=False)
    new_product_images = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False)
    deleted_product_images = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False)
    # production_steps = ProductionStepSerializer(many=True, required=False)
    production_steps = ProductionStepSerializerForProductUpdate(many=True, required=False)
    product_images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'title',
            'category',
            'sub_category',
            'unit',
            'new_product_images',
            'deleted_product_images',
            'product_images',
            'thumbnail',
            'price_per_unit',
            'sell_price_per_unit',
            'full_description',
            'quantity',
            'possible_productions_date',
            'possible_delivery_date',
            'production_steps',
            'vat'
        ]

    def update(self, instance, validated_data):
        # new product images
        try:
            new_product_images = validated_data.pop('new_product_images')
        except:
            new_product_images = None

        # deleted product images
        try:
            deleted_product_images = validated_data.pop('deleted_product_images')
        except:
            deleted_product_images = None

        # production steps
        try:
            production_steps = validated_data.pop('production_steps')
        except:
            production_steps = None

        if self.context['request'].user.user_type == 'CUSTOMER':
            raise serializers.ValidationError("Product only will be updated by farmers and agents")

        # product inventory
        try:
            quantity = validated_data["quantity"]
            print(quantity)
        except:
            quantity = None

        if quantity:
            last_inventory = Inventory.objects.filter(product=instance).last()
            initial_quantity = quantity - last_inventory.current_quantity
            Inventory.objects.create(initial_quantity=initial_quantity, current_quantity=quantity, product=instance)
            total_quantity = Inventory.objects.filter(product=instance).aggregate(total_quantity=Sum('initial_quantity'))
            validated_data.update({'total_quantity': total_quantity['total_quantity']})

        # price_per_unit & quantity validation
        price_per_unit = validated_data.get("price_per_unit", instance.price_per_unit)
        sell_price_per_unit = validated_data.get("sell_price_per_unit", instance.sell_price_per_unit)
        quantity = validated_data.get("quantity", instance.quantity)
        if price_per_unit < 0:
            raise serializers.ValidationError("Price per unit cannot be negative.")
        if sell_price_per_unit < 0:
            raise serializers.ValidationError("Sell Price per unit cannot be negative.")
        if quantity < 0:
            raise serializers.ValidationError("Quantity cannot be negative.")

        # new product_images
        if new_product_images:
            for image in new_product_images:
                ProductImage.objects.create(
                    product=instance, file=image)

        # deleted product_images
        if deleted_product_images:
            for image_id in deleted_product_images:
                ProductImage.objects.filter(id=image_id, product=instance).delete()

        # production steps
        if production_steps:
            for step in production_steps:
                try:
                    production_steps = ProductionStep.objects.get(product=instance, step=step['step'])
                    if step.get("image") is not None:
                        production_steps.image = step['image']
                    if step.get("step_date") is not None:
                        production_steps.step_date = step['step_date']
                    production_steps.save()
                except ProductionStep.DoesNotExist:
                    ProductionStep.objects.create(product=instance, step=step['step'], image=step['image'], step_date=step['step_date'])
                    
        return super().update(instance, validated_data)


class PublishProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = [
            'id',
            'sell_price_per_unit',
            'status'
        ]


class BestSellingProductListSerializer(serializers.ModelSerializer):
    sell_price_per_unit = serializers.SerializerMethodField('get_sell_price_with_vat')
    farmer = serializers.SerializerMethodField('get_farmer_info')

    class Meta:
        model = Product
        fields = [
            'id',
            'title',
            'slug',
            'thumbnail',
            'price_per_unit',
            'sell_price_per_unit',
            'quantity',
            'unit',
            'sell_count',
            'full_description',
            'farmer',
        ]

    def get_sell_price_with_vat(self, obj):
        vat = obj.vat  # assuming vat is defined in the Product model
        sell_price = obj.sell_price_per_unit
        if vat is not None:
            sell_price_with_vat = sell_price * (1 + vat / 100)
            return round(sell_price_with_vat, 2)
        else:
            return sell_price
        
    def get_farmer_info(self, obj):
        try:
            farmer = obj.user
            print(farmer)
            serializer = FarmerListForBestSellingSerializer(instance=farmer)
            return serializer.data
        except:
            return None


class AdminOfferProductsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferProduct
        fields = ['id',
                  'product',
                  ]


class AdminOfferSerializer(serializers.ModelSerializer):
    offer_products = AdminOfferProductsSerializer(many=True, required=False)
    existing_offer_products = serializers.SerializerMethodField(
        'get_existing_offer_products')
    start_date = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S", required=False)
    end_date = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S", required=False)

    class Meta:
        model = Offer
        read_only_field = ['id']
        fields = ['id',
                  'title',
                  'start_date',
                  'end_date',
                  'thumbnail',
                  'short_description',
                  'full_description',
                  'discount_price',
                  'discount_price_type',
                  'offer_products',
                  'existing_offer_products',
                  'is_active',
                  ]

    def get_existing_offer_products(self, obj):
        queryset = OfferProduct.objects.filter(offer=obj, is_active=True)
        serializer = AdminOfferProductsSerializer(instance=queryset, many=True)
        return serializer.data

    def create(self, validated_data):
        # offer_products
        try:
            offer_products = validated_data.pop('offer_products')
        except:
            offer_products = ''

        offer_instance = Offer.objects.create(**validated_data)

        try:
            # offer_products
            if offer_products:
                for offer_product in offer_products:
                    product = offer_product['product']
                    OfferProduct.objects.create(
                        offer=offer_instance, product=product)
            return offer_instance
        except:
            return offer_instance

    def update(self, instance, validated_data):
        # offer_products
        try:
            offer_products = validated_data.pop('offer_products')
        except:
            offer_products = ''

        try:
            # offer_products
            if offer_products:
                o_p = OfferProduct.objects.filter(offer=instance).exists()
                if o_p == True:
                    OfferProduct.objects.filter(offer=instance).delete()

                for offer_product in offer_products:
                    product = offer_product['product']
                    OfferProduct.objects.create(
                        offer=instance, product=product)
            else:
                o_p = OfferProduct.objects.filter(offer=instance).exists()
                if o_p == True:
                    OfferProduct.objects.filter(offer=instance).delete()

            validated_data.update({"updated_at": timezone.now()})
            return super().update(instance, validated_data)
        except:
            validated_data.update({"updated_at": timezone.now()})
            return super().update(instance, validated_data)


class AdminOfferUpdateDetailsSerializer(serializers.ModelSerializer):
    offer_products = serializers.SerializerMethodField(
        'get_offer_products')
    start_date = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S", required=False)
    end_date = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S", required=False)

    class Meta:
        model = Offer
        read_only_field = ['id']
        fields = ['id',
                  'title',
                  'start_date',
                  'end_date',
                  'thumbnail',
                  'short_description',
                  'full_description',
                  'discount_price',
                  'discount_price_type',
                  'offer_products',
                  ]

    def get_offer_products(self, obj):
        queryset = OfferProduct.objects.filter(offer=obj, is_active=True)
        serializer = AdminOfferProductsSerializer(instance=queryset, many=True)
        return serializer.data


class OfferInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = [
            'id',
            'title',
            'start_date',
            'end_date',
            'thumbnail',
            'discount_price',
            'discount_price_type',
            'short_description'
        ]

class OfferProductListSerializer(serializers.ModelSerializer):
    category = CategoryListSerializer(many=False, read_only=True)
    sub_category = SubCategoryListSerializer(many=False, read_only=True)
    unit = UnitListSerializer(many=False, read_only=True)
    sell_price_per_unit = serializers.SerializerMethodField('get_sell_price_with_vat')
    offer_details = serializers.SerializerMethodField('get_offer_details')
    previous_sell_price_per_unit = serializers.SerializerMethodField('get_previous_sell_price_with_vat')

    class Meta:
        model = Product
        fields = [
            'id',
            'title',
            'slug',
            'category',
            'sub_category',
            'unit',
            'thumbnail',
            'price_per_unit',
            'full_description',
            'quantity',
            'total_quantity',
            'possible_productions_date',
            'possible_delivery_date',
            'sell_price_per_unit',
            'status',
            'sell_count',
            'created_at',
            'offer_details',
            'previous_sell_price_per_unit'
        ]

    def get_offer_details(self, obj):
        try:
            today = timezone.now().date()
            queryset = Offer.objects.filter(end_date__gt=today, is_active=True).order_by('-created_at')[:1]
            serializer = OfferInfoSerializer(instance=queryset, many=True, context={'request': self.context['request']})
            return serializer.data
        except:
            return []

    def get_sell_price_with_vat(self, obj):
        sell_price = obj.sell_price_per_unit

        # Check if there is an active offer for the product
        offer = OfferProduct.objects.filter(product=obj, offer__is_active=True,
                                            offer__end_date__gte=timezone.now()).first()

        if offer:
            discount_type = offer.offer.discount_price_type
            discount_value = offer.offer.discount_price

            if discount_type == 'per':
                offer_price = (1 - (discount_value / 100)) * sell_price
            elif discount_type == 'flat':
                offer_price = sell_price - discount_value
            else:
                offer_price = sell_price

            vat = obj.vat
            if vat is not None:
                sell_price_with_vat = offer_price * (1 + vat / 100)
                return round(sell_price_with_vat, 2)
            else:
                return round(offer_price, 2)
        else:
            vat = obj.vat
            if vat is not None:
                sell_price_with_vat = sell_price * (1 + vat / 100)
                return round(sell_price_with_vat, 2)
            else:
                return round(sell_price, 2)

    def get_previous_sell_price_with_vat(self, obj):
        vat = obj.vat  # assuming vat is defined in the Product model
        sell_price = obj.sell_price_per_unit
        if vat is not None:
            sell_price_with_vat = sell_price * (1 + vat / 100)
            return round(sell_price_with_vat, 2)
        else:
            return sell_price
        

class AdminCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            'id',
            'title',
            'logo'
        ]


class AdminSubCategorySerializer(serializers.ModelSerializer):
    category_title = serializers.CharField(source='category.title', read_only=True)
    class Meta:
        model = SubCategory
        fields = [
            'id',
            'title',
            'logo',
            'category',
            'category_title'
        ]