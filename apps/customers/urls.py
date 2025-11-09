# apps/customers/urls.py

from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('register-member/', views.register_member, name='register_member'),
]
