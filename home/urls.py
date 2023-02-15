from django.urls import path
from .api import HomeDataAPIView, AdminDashboardDataAPIView

urlpatterns = [
    path('customer/home-data/', HomeDataAPIView.as_view()),
    path('admin/dashboard-data/', AdminDashboardDataAPIView.as_view()),

]