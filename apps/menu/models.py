"""Menu models - Categories and menu items dengan multi-currency & stock support."""
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.text import slugify
from apps.core.models import TenantAwareModel


class Category(TenantAwareModel):
    """Kategori menu (Food, Drinks, Desserts, dll)."""
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, max_length=50)
    description = models.TextField(blank=True)
    display_order = models.IntegerField(default=0, help_text="Urutan tampilan (angka kecil tampil lebih dulu)")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['restaurant_id', 'is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class MenuItem(TenantAwareModel):
    """Menu item dengan multi-currency (IDR/EGP) dan stock management."""
    
    CURRENCY_CHOICES = [('IDR', 'Indonesian Rupiah'), ('EGP', 'Egyptian Pound')]
    STOCK_UNIT_CHOICES = [('portion', 'Portion'), ('piece', 'Piece'), ('kg', 'Kilogram'), ('liter', 'Liter')]
    
    # Relations
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='items')
    
    # Basic info
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=50)
    description = models.TextField()
    
    # Pricing
    price_amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    price_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='IDR')
    
    # Media
    image = models.ImageField(upload_to='menu_images/%Y/%m/', blank=True, null=True)
    
    # Stock
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)], help_text="Stok tersedia (update manual setiap hari)")
    stock_unit = models.CharField(max_length=20, choices=STOCK_UNIT_CHOICES, default='portion')
    is_unlimited_stock = models.BooleanField(default=False, help_text="Centang jika stok unlimited (tidak perlu tracking)")
    low_stock_threshold = models.IntegerField(default=5, validators=[MinValueValidator(0)], help_text="Alert jika stok dibawah angka ini")
    
    # Flags
    is_available = models.BooleanField(default=True, help_text="Tersedia untuk order (auto false jika stok habis)")
    is_best_seller = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    
    # Display
    display_order = models.IntegerField(default=0, help_text="Urutan tampilan dalam kategori")
    preparation_time = models.IntegerField(default=15, validators=[MinValueValidator(0)], help_text="Waktu persiapan (menit)")
    
    class Meta:
        verbose_name_plural = "Menu Items"
        ordering = ['category', 'display_order', 'name']
        indexes = [
            models.Index(fields=['category', 'is_available']),
            models.Index(fields=['is_best_seller']),
            models.Index(fields=['price_currency']),
            models.Index(fields=['stock_quantity']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.get_price_display()}"
    
    def get_price_display(self):
        """Format harga dengan currency."""
        if self.price_currency == 'IDR':
            return f"Rp {self.price_amount:,.0f}"
        elif self.price_currency == 'EGP':
            return f"EGP {self.price_amount:,.2f}"
        return f"{self.price_currency} {self.price_amount}"
    
    def is_low_stock(self):
        """Check apakah stok rendah."""
        if self.is_unlimited_stock:
            return False
        return self.stock_quantity <= self.low_stock_threshold
    
    def is_out_of_stock(self):
        """Check apakah stok habis."""
        if self.is_unlimited_stock:
            return False
        return self.stock_quantity == 0
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if self.is_out_of_stock():
            self.is_available = False
        super().save(*args, **kwargs)
