from django.db import models
from armaan_bhai.models import AbstractTimeStamp
from user.models import User
from .utils import unique_slug_generator
from django.db.models.signals import pre_save

# Create your models here.

class Category(AbstractTimeStamp):
    title = models.CharField(
        max_length=100, null=False, blank=False, default="", help_text="name")
    logo = models.ImageField(
        upload_to='category', blank=True, null=True)
    is_active = models.BooleanField(null=False, blank=False, default=True)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        db_table = 'category'

    def __str__(self):
        return 'id: ' + str(self.id) + ' title: ' + self.title

class SubCategory(AbstractTimeStamp):
    title = models.CharField(
        max_length=100, null=False, blank=False, default="", help_text="name")
    logo = models.ImageField(
        upload_to='sub_category', blank=True, null=True)
    is_active = models.BooleanField(null=False, blank=False, default=True)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name='sub_category_category')

    class Meta:
        verbose_name = 'SubCategory'
        verbose_name_plural = 'SubCategories'
        db_table = 'sub_category'

    def __str__(self):
        return 'id: ' + str(self.id) + ' title: ' + self.title

class Units(AbstractTimeStamp):
    title = models.CharField(
        max_length=100, null=False, blank=False, default="")
    is_active = models.BooleanField(null=False, blank=False, default=True)

    class Meta:
        verbose_name = 'Unit'
        verbose_name_plural = 'Units'
        db_table = 'units'

    def __str__(self):
        return self.title


class Product(AbstractTimeStamp):
    PRODUCT_STATUSES = [
        ('UNPUBLISH', 'UnPublish'),
        ('PUBLISH', 'Publish')
    ]
    title = models.CharField(max_length=800)
    slug = models.SlugField(
        null=False, allow_unicode=True, blank=True, max_length=255)
    category = models.ForeignKey(
        Category, related_name='product_category', blank=False, null=True, on_delete=models.PROTECT)
    sub_category = models.ForeignKey(
        SubCategory, related_name='product_sub_category', blank=True, null=True, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.PROTECT,
                               related_name='product_seller', blank=True, null=True)
    unit = models.ForeignKey(Units, related_name="product_unit",
                             blank=True, null=True, on_delete=models.PROTECT)
    full_description = models.TextField(null=False, blank=False)
    price_per_unit = models.FloatField(
        max_length=255, null=False, blank=False, default=0, help_text="Unit price")
    sell_price_per_unit = models.FloatField(
        max_length=255, null=False, blank=False, default=0, help_text="Unit price")
    quantity = models.IntegerField(null=True, blank=True, default=0)
    total_quantity = models.IntegerField(null=False, blank=False, default=0)
    thumbnail = models.FileField(upload_to='products', blank=True, null=True)
    possible_productions_date = models.DateField(
        null=True, blank=True, help_text="Possible production date")
    possible_delivery_date = models.DateField(
        null=True, blank=True, help_text="Possible delivery date")
    status = models.CharField(
        max_length=20, choices=PRODUCT_STATUSES, default=PRODUCT_STATUSES[0][0])
    sell_count = models.IntegerField(default=0)


    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        db_table = 'products'

    @property
    def average_rating(self):
        if hasattr(self, '_average_rating'):
            return self._average_rating
        return self.reviews.aggregate(Avg('rating'))

    def __str__(self):
        return self.title



class Inventory(AbstractTimeStamp):
    initial_quantity = models.IntegerField(null=True, blank=True, default=0)
    current_quantity = models.IntegerField(null=True, blank=True, default=0)  
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name='inventory_product')
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Inventory'
        verbose_name_plural = 'Inventories'
        db_table = 'inventory'

    def __str__(self):
        return self.product.title

class ProductImage(AbstractTimeStamp):
    def validate_file_extension(value):
        import os
        from django.core.exceptions import ValidationError
        ext = os.path.splitext(value.name)[1]
        valid_extensions = ['.jpg', '.png', '.jpeg']
        if not ext.lower() in valid_extensions:
            raise ValidationError('Unsupported file extension.')

    file = models.FileField(upload_to='products', validators=[
                            validate_file_extension])
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name='product_images')
    is_active = models.BooleanField(null=False, blank=False, default=True)

    class Meta:
        verbose_name = 'ProductImage'
        verbose_name_plural = 'ProductImages'
        db_table = 'product_image'

    def __str__(self):
        return self.product.title


class ProductionStep(AbstractTimeStamp):
    PRODUCTION_STEPS = [
        ('FIRST_STEP', 'First Step'),
        ('SECOND_STEP', 'Second Step'),
        ('THIRD_STEP', 'Third Step'),
        ('FOURTH_STEP', 'Fourth Step'), ]

    def validate_file_extension(value):
        import os
        from django.core.exceptions import ValidationError
        ext = os.path.splitext(value.name)[1]
        valid_extensions = ['.jpg', '.png', '.jpeg']
        if not ext.lower() in valid_extensions:
            raise ValidationError('Unsupported file extension.')
    step = models.CharField(max_length=200, choices=PRODUCTION_STEPS)
    image = models.FileField(upload_to='productions_step', validators=[
                            validate_file_extension])
    step_date = models.DateField(null=True, blank=True)
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name='production_steps')
    is_active = models.BooleanField(null=False, blank=False, default=True)

    class Meta:
        verbose_name = 'ProductionStep'
        verbose_name_plural = 'ProductionSteps'
        db_table = 'production_step'

    def __str__(self):
        return self.step


def pre_save_product(sender, instance, *args, **kwargs):
    if not instance.slug:
        instance.slug = unique_slug_generator(instance)

pre_save.connect(pre_save_product, sender=Product)