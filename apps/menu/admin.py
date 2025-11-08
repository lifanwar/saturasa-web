"""Menu admin configuration."""
from django.contrib import admin
from django.utils.html import format_html
from .models import Category, MenuItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin untuk Category model."""
    
    list_display = ['name', 'slug', 'display_order', 'item_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['display_order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Display', {
            'fields': ('display_order', 'is_active')
        }),
        ('System', {
            'fields': ('restaurant_id',),
            'classes': ('collapse',)
        }),
    )
    
    def item_count(self, obj):
        """Tampilkan jumlah menu items dalam kategori."""
        count = obj.items.count()
        return format_html('<strong>{}</strong> items', count)
    item_count.short_description = 'Menu Items'


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    """Admin untuk MenuItem model."""
    
    list_display = ['name', 'category', 'price_display', 'stock_status', 'availability_badge', 'best_seller_badge', 'created_at']
    list_filter = ['category', 'is_available', 'is_best_seller', 'is_new', 'price_currency', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['category', 'display_order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'name', 'slug', 'description', 'image')
        }),
        ('Pricing', {
            'fields': ('price_amount', 'price_currency')
        }),
        ('Stock Management', {
            'fields': ('stock_quantity', 'stock_unit', 'is_unlimited_stock', 'low_stock_threshold'),
            'description': 'Update stock quantity manually setiap hari'
        }),
        ('Availability & Flags', {
            'fields': ('is_available', 'is_best_seller', 'is_new')
        }),
        ('Display & Preparation', {
            'fields': ('display_order', 'preparation_time')
        }),
        ('System', {
            'fields': ('restaurant_id',),
            'classes': ('collapse',)
        }),
    )
    
    def price_display(self, obj):
        """Format harga dengan currency."""
        return obj.get_price_display()
    price_display.short_description = 'Price'
    price_display.admin_order_field = 'price_amount'
    
    def stock_status(self, obj):
        """Tampilkan status stok dengan warna."""
        if obj.is_unlimited_stock:
            return format_html('<span style="color: green;">♾️ Unlimited</span>')
        elif obj.is_out_of_stock():
            return format_html('<span style="color: red;">❌ Out of Stock</span>')
        elif obj.is_low_stock():
            return format_html('<span style="color: orange;">⚠️ Low ({}/{})</span>', obj.stock_quantity, obj.low_stock_threshold)
        else:
            return format_html('<span style="color: green;">✅ {}</span>', obj.stock_quantity)
    stock_status.short_description = 'Stock Status'
    
    def availability_badge(self, obj):
        """Badge untuk availability."""
        if obj.is_available:
            return format_html('<span style="background: green; color: white; padding: 3px 10px; border-radius: 3px;">Available</span>')
        return format_html('<span style="background: red; color: white; padding: 3px 10px; border-radius: 3px;">Unavailable</span>')
    availability_badge.short_description = 'Status'
    
    def best_seller_badge(self, obj):
        """Badge untuk best seller."""
        badges = []
        if obj.is_best_seller:
            badges.append('🌟 Best Seller')
        if obj.is_new:
            badges.append('🆕 New')
        return ' '.join(badges) if badges else '-'
    best_seller_badge.short_description = 'Badges'
    
    actions = ['mark_as_best_seller', 'mark_as_available', 'mark_as_unavailable']
    
    def mark_as_best_seller(self, request, queryset):
        """Bulk action: tandai sebagai best seller."""
        updated = queryset.update(is_best_seller=True)
        self.message_user(request, f'{updated} items marked as best seller.')
    mark_as_best_seller.short_description = 'Mark selected as Best Seller'
    
    def mark_as_available(self, request, queryset):
        """Bulk action: set available."""
        updated = queryset.update(is_available=True)
        self.message_user(request, f'{updated} items marked as available.')
    mark_as_available.short_description = 'Mark selected as Available'
    
    def mark_as_unavailable(self, request, queryset):
        """Bulk action: set unavailable."""
        updated = queryset.update(is_available=False)
        self.message_user(request, f'{updated} items marked as unavailable.')
    mark_as_unavailable.short_description = 'Mark selected as Unavailable'
