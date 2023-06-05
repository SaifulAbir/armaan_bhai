import datetime
from django.utils import timezone
from datetime import date

from django.db.models import Sum, F
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response

from home.models import TotalVisit
from home.serializers import CategoryListSerializer
from order.models import Order, PaymentHistory, OrderItem, SubOrder
from product.models import Category, Product
from product.serializers import ProductListSerializer
from user.models import User, District, Upazilla
from user.serializers import UserProfileDetailSerializer


class HomeDataAPIView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        product_categories = Category.objects.all()
        product_category_serializer = CategoryListSerializer(product_categories, many=True, context={"request": request})
        if TotalVisit.objects.all().exists():
            total_visitor = TotalVisit.objects.first()
            total_visitor.visitor += 1
            total_visitor.save()
        else:
            total_visitor = TotalVisit.objects.create(visitor=1)
        return Response({
            "product_categories": product_category_serializer.data,
        })


class AdminDashboardDataAPIView(APIView):

    def get(self, request):
        if self.request.user.is_superuser == True:
            
            # total farmer
            if User.objects.filter(user_type="FARMER").exists():
                total_farmer = User.objects.filter(user_type="FARMER").count()
            else:
                total_farmer = 0

            # total agent
            if User.objects.filter(user_type="AGENT").exists():
                total_agent = User.objects.filter(user_type="AGENT").count()
            else:
                total_agent = 0

            # total district
            if District.objects.all().exists():
                total_district = District.objects.all().count()
            else:
                total_district = 0

            # total upazilla
            if Upazilla.objects.all().exists():
                total_upazilla = Upazilla.objects.all().count()
            else:
                total_upazilla = 0

            # total product
            if Product.objects.all().exists():
                total_product = Product.objects.all().count()
            else:
                total_product = 0

            # total visitor
            if TotalVisit.objects.all().exists():
                total_visitor = TotalVisit.objects.first().visitor
            else:
                total_visitor = 0

            # Top selling products
            if Product.objects.filter(status='PUBLISH').exists():
                products = Product.objects.filter(status='PUBLISH').order_by('-sell_count')[:5]
                top_selling_products = ProductListSerializer(products, many=True, context={"request": request})
            else:
                top_selling_products = None

            # admin list
            if User.objects.filter(user_type="ADMIN").exists():
                users = User.objects.filter(user_type='ADMIN')[:10]
                admin_list = UserProfileDetailSerializer(users, many=True, context={"request": request})
            else:
                admin_list = None

            # total sales this month
            # if Order.objects.all().exists():
            today = datetime.datetime.now()
            total_sales = OrderItem.objects.filter(suborder__order_status='DELIVERED', suborder__payment_status='PAID', suborder__order_date__month=today.month).aggregate(total = Sum('total_price'))['total'] or 0
            # else:
            #     total_sales = None

            # total sale amount

            # total_sale_amount = OrderItem.objects.filter(suborder__payment_status='PAID').aggregate(total=Sum('total_price'))['total'] or 0
            total_sale_amount = OrderItem.objects.filter(suborder__order_status='DELIVERED', suborder__payment_status='PAID').aggregate(total=Sum( ('total_price') ))['total'] or 0
            total_sale_amount = round(total_sale_amount, 2)

            # total sale amount this month
            current_month = timezone.now().month
            start_of_month = date(year=timezone.now().year, month=current_month, day=1)
            end_of_month = start_of_month.replace(day=28) + datetime.timedelta(days=4)
            end_of_month = end_of_month - datetime.timedelta(days=end_of_month.day)
            # total_sale_amount_of_this_month = OrderItem.objects.filter(suborder__payment_status='PAID', created_at__gte=start_of_month, created_at__lte=end_of_month).aggregate(total=Sum('total_price'))['total'] or 0
            total_sale_amount_of_this_month = OrderItem.objects.filter(suborder__order_status='DELIVERED', suborder__payment_status='PAID', suborder__created_at__gte=start_of_month, suborder__created_at__lte=end_of_month).aggregate(total=Sum( ('total_price')))['total'] or 0
            total_sale_amount_of_this_month = round(total_sale_amount_of_this_month, 2)


            return Response({
                "total_farmer": total_farmer,
                "total_agent": total_agent,
                "total_visitor": total_visitor,
                "total_district": total_district,
                "total_upazilla": total_upazilla,
                "total_product": total_product,
                "total_sales_this_month": total_sales if total_sales else 0,
                "admin_list": admin_list.data if admin_list else "No Admin",
                "top_selling_products": top_selling_products.data if top_selling_products else "No Product",
                "total_sale_amount": total_sale_amount,
                "total_sale_amount_of_this_month": total_sale_amount_of_this_month
            })
        elif self.request.user.user_type == "AGENT":
            # Top selling products
            if Product.objects.filter(user__agent_user_id=self.request.user.id, status='PUBLISH').exists():
                products = Product.objects.filter(user__agent_user_id=self.request.user.id, status='PUBLISH').order_by('-sell_count')[:5]
                top_selling_products = ProductListSerializer(products, many=True, context={"request": request})
            else:
                top_selling_products = None

            # total farmer
            if User.objects.filter(agent_user_id=self.request.user.id, user_type="FARMER").exists():
                total_farmer = User.objects.filter(agent_user_id=self.request.user.id, user_type="FARMER").count()
            else:
                total_farmer = 0

            # total sales this month
            if Order.objects.filter(order_item_order__product__user__agent_user_id=self.request.user.id).exists():
                today = datetime.datetime.now()
                total_sales = Order.objects.filter(order_item_order__product__user__agent_user_id=self.request.user.id, order_date__month=today.month).aggregate(
                    total_sales_this_month=Sum('total_price'))
            else:
                total_sales = 0

            # total delivered order
            if SubOrder.objects.filter(order_item_suborder__product__user__agent_user_id=self.request.user.id).exists():
                total_delivered_order = SubOrder.objects.filter(
                    order_item_suborder__product__user__agent_user_id=self.request.user.id,
                    order_status="DELIVERED").count()
            else:
                total_delivered_order = 0
            # if Order.objects.filter(order_item_order__product__user__agent_user_id=self.request.user.id).exists():
            #     total_delivered_order = Order.objects.filter(
            #         order_item_order__product__user__agent_user_id=self.request.user.id, order_status="DELIVERED").count()
            # else:
            #     total_delivered_order = 0

            # Top published products
            if Product.objects.filter(user__agent_user_id=self.request.user.id, status='PUBLISH').exists():
                total_published_product = Product.objects.filter(user__agent_user_id=self.request.user.id,
                                                  status='PUBLISH').count()
            else:
                total_published_product = 0

            # Top unpublished products
            if Product.objects.filter(user__agent_user_id=self.request.user.id, status='UNPUBLISH').exists():
                total_unpublished_product = Product.objects.filter(user__agent_user_id=self.request.user.id,
                                                  status='UNPUBLISH').count()
            else:
                total_unpublished_product = 0

            # total sale amount
            # total_sale_amount = OrderItem.objects.filter(product__user__agent_user_id=self.request.user.id,suborder__payment_status='PAID').aggregate(total=Sum('total_price'))['total'] or 0
            total_sale_amount = OrderItem.objects.filter(product__user__agent_user_id=self.request.user.id, suborder__order_status='DELIVERED',  suborder__payment_status='PAID').aggregate(total=Sum( F('product__price_per_unit') * F('quantity') ))['total'] or 0

            # total sale amount this month
            current_month = timezone.now().month
            start_of_month = date(year=timezone.now().year, month=current_month, day=1)
            end_of_month = start_of_month.replace(day=28) + datetime.timedelta(days=4)
            end_of_month = end_of_month - datetime.timedelta(days=end_of_month.day)
            # total_sale_amount_of_this_month = OrderItem.objects.filter(product__user__agent_user_id=self.request.user.id, suborder__payment_status='PAID', created_at__gte=start_of_month, created_at__lte=end_of_month).aggregate(total=Sum('total_price'))['total'] or 0
            total_sale_amount_of_this_month = OrderItem.objects.filter(product__user__agent_user_id=self.request.user.id, suborder__order_status='DELIVERED', suborder__payment_status='PAID', created_at__gte=start_of_month, created_at__lte=end_of_month).aggregate(total=Sum( F('product__price_per_unit') * F('quantity') ))['total'] or 0


            return Response({
                "total_farmer": total_farmer,
                "total_delivered_order": total_delivered_order,
                "total_published_product": total_published_product,
                "total_unpublished_product": total_unpublished_product,
                "total_sales_this_month": total_sales if total_sales else 0,
                "top_selling_products": top_selling_products.data if top_selling_products else "No Product",
                "total_sale_amount": total_sale_amount,
                "total_sale_amount_of_this_month": total_sale_amount_of_this_month
            })
        elif self.request.user.user_type == "FARMER":
            # Top selling products
            if Product.objects.filter(user=self.request.user, status='PUBLISH').exists():
                products = Product.objects.filter(user=self.request.user, status='PUBLISH').order_by('-sell_count')[:5]
                top_selling_products = ProductListSerializer(products, many=True, context={"request": request})
            else:
                top_selling_products = None

            # total sales this month
            if Order.objects.filter(order_item_order__product__user=self.request.user).exists():
                today = datetime.datetime.now()
                total_sales = Order.objects.filter(order_item_order__product__user=self.request.user, order_date__month=today.month).aggregate(
                    total_sales_this_month=Sum('total_price'))
            else:
                total_sales = None

            # total delivered order
            if SubOrder.objects.filter(order_item_suborder__product__user=self.request.user).exists():
                total_delivered_order = SubOrder.objects.filter(
                    order_item_suborder__product__user=self.request.user, order_status="DELIVERED").count()
            else:
                total_delivered_order = 0

            # Top published products
            if Product.objects.filter(user=self.request.user, status='PUBLISH').exists():
                total_published_product = Product.objects.filter(user=self.request.user,
                                                  status='PUBLISH').count()
            else:
                total_published_product = 0

            # Top unpublished products
            if Product.objects.filter(user=self.request.user, status='UNPUBLISH').exists():
                total_unpublished_product = Product.objects.filter(user=self.request.user,
                                                  status='UNPUBLISH').count()
            else:
                total_unpublished_product = 0

            # total sale amount
            total_sale_amount = OrderItem.objects.filter(product__user=self.request.user.id,suborder__payment_status='PAID').aggregate(total=Sum( F('product__price_per_unit') * F('quantity') ))['total'] or 0

            # total sale amount this month
            current_month = timezone.now().month
            start_of_month = date(year=timezone.now().year, month=current_month, day=1)
            end_of_month = start_of_month.replace(day=28) + datetime.timedelta(days=4)
            end_of_month = end_of_month - datetime.timedelta(days=end_of_month.day)
            total_sale_amount_of_this_month = OrderItem.objects.filter(product__user=self.request.user.id, suborder__payment_status='PAID', created_at__gte=start_of_month, created_at__lte=end_of_month).aggregate(total=Sum( F('product__price_per_unit') * F('quantity') ))['total'] or 0

            return Response({
                "total_delivered_order": total_delivered_order,
                "total_published_product": total_published_product,
                "total_unpublished_product": total_unpublished_product,
                "total_sales_this_month": total_sales if total_sales else 0,
                "top_selling_products": top_selling_products.data if top_selling_products else "No Product",
                "total_sale_amount": total_sale_amount,
                "total_sale_amount_of_this_month": total_sale_amount_of_this_month
            })
        else:
            raise ValidationError({"msg": 'You can not see dashboard data, because you are not authorized!'})