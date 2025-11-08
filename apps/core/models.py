"""Core models - Abstract base models."""
from django.db import models


class TenantAwareModel(models.Model):
    """Abstract base model dengan tenant support untuk future multi-tenancy."""
    
    restaurant_id = models.IntegerField(default=1, db_index=True, help_text="Tenant/Restaurant ID untuk multi-tenancy")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.__class__.__name__} #{self.pk}"
