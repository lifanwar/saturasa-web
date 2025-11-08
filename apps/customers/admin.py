"""Customers admin configuration."""
from django.contrib import admin
from django.utils.html import format_html
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """Admin untuk Customer model."""
    
    list_display = ['name', 'phone_number', 'type_badge', 'email', 'order_count', 'created_at']
    list_filter = ['customer_type', 'created_at']
    search_fields = ['name', 'phone_number', 'email']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('phone_number', 'name', 'customer_type')
        }),
        ('Member Details', {
            'fields': ('user', 'email', 'date_of_birth'),
            'description': 'Fields ini hanya untuk Member customers'
        }),
        ('System', {
            'fields': ('restaurant_id',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['customer_type']  # Prevent manual type change
    
    def type_badge(self, obj):
        """Badge untuk customer type."""
        if obj.customer_type == 'MEMBER':
            return format_html('<span style="background: gold; color: black; padding: 3px 10px; border-radius: 3px;">👤 MEMBER</span>')
        return format_html('<span style="background: gray; color: white; padding: 3px 10px; border-radius: 3px;">👥 GUEST</span>')
    type_badge.short_description = 'Type'
    
    def order_count(self, obj):
        """Tampilkan jumlah order."""
        count = obj.orders.count()
        return format_html('<strong>{}</strong> orders', count)
    order_count.short_description = 'Total Orders'
    
    def has_delete_permission(self, request, obj=None):
        """Disable delete untuk customer yang punya orders."""
        if obj and obj.orders.exists():
            return False
        return super().has_delete_permission(request, obj)
