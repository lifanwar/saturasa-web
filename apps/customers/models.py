"""Customer models - Guest dan Member customer management."""
from django.db import models
from django.contrib.auth.models import User
from apps.core.models import TenantAwareModel

class Customer(TenantAwareModel):
    """
    Model untuk MEMBER saja.
    Guest order tidak disimpan di sini, hanya di Order.offline_customer_name
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name='customer'
    )
    
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    date_of_birth = models.DateField()
    
    class Meta:
        verbose_name_plural = 'Customers'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.user.email})"