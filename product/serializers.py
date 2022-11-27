from rest_framework import serializers
from product.models import Product, Category, SubCategory, Units, Inventory, ProductImage, ProductionStep
from user.models import User


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
            'thumbnail',
            'price_per_unit',
            'full_description',
            'quantity',
            'possible_productions_date',
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

        if not self.context['request'].user.user_type == 'FARMER':
            raise serializers.ValidationError("Product only will be uploaded by farmers")

        #create product
        product_instance = Product.objects.create(**validated_data, user=self.context['request'].user)

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
            print(production_steps)
            for step in production_steps:
                ProductionStep.objects.create(
                    product=product_instance, image=step['image'], step_date=step['step_date'], step=step['step'])
        return product_instance





