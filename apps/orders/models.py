"""Order models - Order management dengan multi-currency dan analytics."""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from apps.core.models import TenantAwareModel


class Order(TenantAwareModel):
    """Order model untuk online dan offline orders."""
    
    ORDER_TYPE_CHOICES = [('DINE_IN', 'Dine In'), ('TAKEAWAY', 'Takeaway'), ('DELIVERY', 'Delivery')]
    ORDER_CHANNEL_CHOICES = [('ONLINE', 'Online'), ('OFFLINE', 'Offline')]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('PREPARING', 'Preparing'),
        ('READY', 'Ready'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    CURRENCY_CHOICES = [('IDR', 'Indonesian Rupiah'), ('EGP', 'Egyptian Pound')]
    
    # Order info
    order_number = models.CharField(max_length=50, unique=True, db_index=True)
    customer = models.ForeignKey('customers.Customer', on_delete=models.PROTECT, related_name='orders', null=True, blank=True, help_text="Link ke customer (null untuk offline walk-in)")
    offline_customer_name = models.CharField(max_length=200, blank=True, help_text="Nama customer untuk offline tanpa registrasi")
    
    # Order type & channel
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES)
    order_channel = models.CharField(max_length=10, choices=ORDER_CHANNEL_CHOICES)
    table_number = models.CharField(max_length=10, blank=True, help_text="Nomor meja (untuk Dine In)")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Financial (multi-currency)
    subtotal_amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    subtotal_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='IDR')
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    delivery_fee_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    total_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='IDR')
    
    # Delivery info
    delivery_address = models.TextField(blank=True)
    
    # Notes
    customer_notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['order_type', 'order_channel']),
            models.Index(fields=['customer']),
        ]
    
    def __str__(self):
        return f"{self.order_number} - {self.order_channel} {self.order_type}"
    
    @property
    def customer_display_name(self):
        """Get customer name dari customer atau offline_customer_name."""
        if self.customer:
            return self.customer.name
        return self.offline_customer_name or "Walk-in Customer"


class OrderItem(TenantAwareModel):
    """Item dalam order."""
    
    CURRENCY_CHOICES = [('IDR', 'Indonesian Rupiah'), ('EGP', 'Egyptian Pound')]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey('menu.MenuItem', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    
    # Price snapshot (saat order dibuat)
    price_amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)], help_text="Harga saat order dibuat (snapshot)")
    price_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='IDR')
    subtotal_amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    subtotal_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='IDR')
    
    notes = models.TextField(blank=True, help_text="Special request (e.g., 'extra spicy', 'no onion')")
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f"{self.menu_item.name} x{self.quantity}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate subtotal
        self.subtotal_amount = self.price_amount * self.quantity
        self.subtotal_currency = self.price_currency
        super().save(*args, **kwargs)


class OrderTimeline(TenantAwareModel):
    """Track status changes untuk analytics."""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='timeline')
    status = models.CharField(max_length=20)
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="User yang update status")
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['order', 'created_at']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.order.order_number} - {self.status} at {self.created_at}"


class CustomerAnalytics(TenantAwareModel):
    """Aggregated analytics data per customer."""
    
    customer = models.OneToOneField('customers.Customer', on_delete=models.CASCADE, related_name='analytics')
    
    # Aggregated data
    total_orders = models.IntegerField(default=0)
    total_spent_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_spent_currency = models.CharField(max_length=3, default='IDR')
    average_order_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_order_date = models.DateTimeField(null=True, blank=True)
    
    # Insights
    favorite_category = models.ForeignKey('menu.Category', on_delete=models.SET_NULL, null=True, blank=True, help_text="Kategori yang paling sering dipesan")
    
    class Meta:
        verbose_name_plural = "Customer Analytics"
        indexes = [
            models.Index(fields=['total_spent_amount']),
            models.Index(fields=['total_orders']),
        ]
    
    def __str__(self):
        return f"Analytics for {self.customer.name}"
