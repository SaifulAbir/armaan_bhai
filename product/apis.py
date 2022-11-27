from rest_framework.generics import CreateAPIView
from product.serializers import ProductCreateSerializer


class ProductCreateAPIView(CreateAPIView):
    serializer_class = ProductCreateSerializer

    def post(self, request, *args, **kwargs):
        return super(ProductCreateAPIView, self).post(request, *args, **kwargs)
        
