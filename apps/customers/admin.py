# apps/customers/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Customer

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'email_display', 'phone_number', 'date_of_birth', 'member_since', 'order_count']
    list_filter = ['created_at', 'date_of_birth']
    search_fields = ['name', 'phone_number', 'user__email']
    readonly_fields = ['user', 'created_at', 'updated_at']
    
    fieldsets = (
        ('User Account', {
            'fields': ('user',)
        }),
        ('Member Information', {
            'fields': ('name', 'phone_number', 'date_of_birth')
        }),
        ('System', {
            'fields': ('restaurant_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def email_display(self, obj):
        return obj.user.email
    email_display.short_description = 'Email'
    email_display.admin_order_field = 'user__email'
    
    def member_since(self, obj):
        return obj.created_at.strftime('%d %b %Y')
    member_since.short_description = 'Member Since'
    member_since.admin_order_field = 'created_at'
    
    def order_count(self, obj):
        count = obj.orders.count()  # ✅ Fixed - use .orders
        if count > 0:
            return format_html(
                '<strong style="color: green;">{} orders</strong>',
                count
            )
        return format_html('<span style="color: gray;">No orders</span>')
    order_count.short_description = 'Orders'
    
    def has_delete_model(self, request, obj=None):
        # Prevent delete if customer has orders
        if obj and obj.order_set.exists():
            return False
        return super().has_delete_model(request, obj)
