"""Customer models - Guest dan Member customer management."""
from django.db import models
from django.contrib.auth.models import User
from apps.core.models import TenantAwareModel


class Customer(TenantAwareModel):
    """
    Unified customer model untuk Guest dan Member.
    Phone number adalah unique identifier utama.
    """
    
    CUSTOMER_TYPE_CHOICES = [('GUEST', 'Guest Customer'), ('MEMBER', 'Member Customer')]
    
    # Identification
    phone_number = models.CharField(max_length=20, unique=True, db_index=True, help_text="Nomor telepon (unique identifier)")
    name = models.CharField(max_length=200)
    customer_type = models.CharField(max_length=10, choices=CUSTOMER_TYPE_CHOICES, default='GUEST')
    
    # Member-only fields (nullable untuk guest)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_profile', help_text="Link ke Django User (untuk member yang bisa login)")
    email = models.EmailField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['customer_type']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.phone_number}) - {self.customer_type}"
    
    def upgrade_to_member(self, user):
        """Upgrade guest customer menjadi member."""
        self.customer_type = 'MEMBER'
        self.user = user
        self.save()
