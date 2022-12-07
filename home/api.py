from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from home.serializers import CategoryListSerializer
from product.models import Category


class HomeDataAPIView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        product_categories = Category.objects.all()
        product_category_serializer = CategoryListSerializer(product_categories, many=True, context={"request": request})
        return Response({
            "product_categories": product_category_serializer.data,
        })