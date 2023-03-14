from rest_framework import serializers
from product.models import Product, Category, SubCategory, Units, Inventory, ProductImage, ProductionStep
from user.models import User, Division, District, Upazilla
from user.serializers import FarmerListSerializer


class ProductionStepSerializer(serializers.ModelSerializer):

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
    production_steps = ProductionStepSerializer(many=True, required=True)
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

        # create product
        if not (self.context['request'].user.user_type == 'FARMER' or self.context['request'].user.user_type == 'AGENT'):
            raise serializers.ValidationError("Product only will be uploaded by agent or farmer")
        elif self.context['request'].user.user_type == 'FARMER':
            product_instance = Product.objects.create(**validated_data, user=self.context['request'].user)
        else:
            farmer = validated_data.get('user')
            if farmer:
                product_instance = Product.objects.create(**validated_data)
            else:
                raise serializers.ValidationError("Farmer id is missing")

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


class ProductListSerializer(serializers.ModelSerializer):
    production_steps = ProductionStepSerializer(many=True, read_only=True)
    product_images = ProductImageSerializer(many=True, read_only=True)
    user = FarmerListSerializer(many=False, read_only=True)
    category = CategoryListSerializer(many=False, read_only=True)
    sub_category = SubCategoryListSerializer(many=False, read_only=True)
    unit = UnitListSerializer(many=False, read_only=True)

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
            'sell_count'
        ]


class ProductViewSerializer(serializers.ModelSerializer):
    production_steps = ProductionStepSerializer(many=True, read_only=True)
    product_images = ProductImageSerializer(many=True, read_only=True)
    user = FarmerListSerializer(many=False, read_only=True)
    category_title = serializers.CharField(source="category.title", read_only=True)

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
            'full_description',
            'quantity',
            'total_quantity',
            'user',
            'possible_productions_date',
            'possible_delivery_date',
            'production_steps'
        ]


class ProductUpdateSerializer(serializers.ModelSerializer):
    new_product_images = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False)
    deleted_product_images = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False)
    production_steps = ProductionStepSerializer(many=True, required=True)
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
            'full_description',
            'quantity',
            'possible_productions_date',
            'possible_delivery_date',
            'production_steps'
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
        except:
            quantity = None

        if quantity:
            last_inventory = Inventory.objects.filter(product=instance).last()
            initial_quantity = quantity - last_inventory.current_quantity
            Inventory.objects.create(initial_quantity=initial_quantity, current_quantity=quantity, product=instance)
            total_quantity = Inventory.objects.filter(product=instance).aggregate(total_quantity=sum('initial_quantity'))
            validated_data.update({"total_quantity": total_quantity})

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
                    production_steps.image = step['image']
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





