from django.urls import path
from .api import HomeDataAPIView

urlpatterns = [
    path('customer/home-data/', HomeDataAPIView.as_view()),
]