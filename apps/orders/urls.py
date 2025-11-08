"""Order URLs."""
from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout_view, name='checkout'),
    path('checkout/confirm/', views.checkout_confirm, name='checkout_confirm'),
    path('success/<str:order_number>/', views.order_success, name='order_success'),
]
