"""Orders admin configuration."""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from .models import Order, OrderItem, OrderTimeline, CustomerAnalytics


class OrderItemInline(admin.TabularInline):
    """Inline untuk OrderItem di Order admin."""
    model = OrderItem
    extra = 0
    fields = ['menu_item', 'quantity', 'price_amount', 'price_currency', 'subtotal_amount', 'notes']
    readonly_fields = ['subtotal_amount']


class OrderTimelineInline(admin.TabularInline):
    """Inline untuk OrderTimeline di Order admin."""
    model = OrderTimeline
    extra = 0
    fields = ['status', 'note', 'created_by', 'created_at']
    readonly_fields = ['created_at']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin untuk Order model."""
    
    list_display = ['order_number', 'customer_info', 'channel_type_badge', 'status_badge', 'total_display', 'created_at']
    list_filter = ['status', 'order_channel', 'order_type', 'created_at']
    search_fields = ['order_number', 'customer__name', 'customer__phone_number', 'offline_customer_name']
    ordering = ['-created_at']
    inlines = [OrderItemInline, OrderTimelineInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'customer', 'offline_customer_name')
        }),
        ('Order Type', {
            'fields': ('order_channel', 'order_type', 'table_number')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Financial', {
            'fields': ('subtotal_amount', 'subtotal_currency', 'tax_amount', 'delivery_fee_amount', 'total_amount', 'total_currency')
        }),
        ('Delivery Information', {
            'fields': ('delivery_address',),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('customer_notes', 'admin_notes'),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('restaurant_id',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['order_number']
    
    def customer_info(self, obj):
        """Tampilkan info customer."""
        name = obj.customer_display_name
        if obj.customer:
            return format_html('<strong>{}</strong><br><small>{}</small>', name, obj.customer.phone_number)
        return format_html('<em>{}</em> (Walk-in)', name)
    customer_info.short_description = 'Customer'
    
    def channel_type_badge(self, obj):
        """Badge untuk channel dan type."""
        channel_color = 'blue' if obj.order_channel == 'ONLINE' else 'purple'
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 3px; margin-right: 5px;">{}</span>'
            '<span style="background: gray; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            channel_color, obj.order_channel, obj.order_type
        )
    channel_type_badge.short_description = 'Channel & Type'
    
    def status_badge(self, obj):
        """Badge untuk status dengan warna."""
        colors = {
            'PENDING': 'orange',
            'CONFIRMED': 'blue',
            'PREPARING': 'purple',
            'READY': 'green',
            'COMPLETED': 'darkgreen',
            'CANCELLED': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html('<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>', color, obj.status)
    status_badge.short_description = 'Status'
    
    def total_display(self, obj):
        """Tampilkan total dengan currency."""
        if obj.total_currency == 'IDR':
            return format_html('<strong>Rp {:,.0f}</strong>', obj.total_amount)
        return format_html('<strong>{} {:,.2f}</strong>', obj.total_currency, obj.total_amount)
    total_display.short_description = 'Total'
    total_display.admin_order_field = 'total_amount'
    
    actions = ['mark_as_confirmed', 'mark_as_preparing', 'mark_as_ready', 'mark_as_completed']
    
    def mark_as_confirmed(self, request, queryset):
        queryset.update(status='CONFIRMED')
        self.message_user(request, 'Orders marked as CONFIRMED.')
    mark_as_confirmed.short_description = 'Confirm selected orders'
    
    def mark_as_preparing(self, request, queryset):
        queryset.update(status='PREPARING')
        self.message_user(request, 'Orders marked as PREPARING.')
    mark_as_preparing.short_description = 'Mark as Preparing'
    
    def mark_as_ready(self, request, queryset):
        queryset.update(status='READY')
        self.message_user(request, 'Orders marked as READY.')
    mark_as_ready.short_description = 'Mark as Ready'
    
    def mark_as_completed(self, request, queryset):
        queryset.update(status='COMPLETED')
        self.message_user(request, 'Orders marked as COMPLETED.')
    mark_as_completed.short_description = 'Mark as Completed'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Admin untuk OrderItem model."""
    
    list_display = ['order', 'menu_item', 'quantity', 'price_display', 'subtotal_display']
    list_filter = ['order__status', 'created_at']
    search_fields = ['order__order_number', 'menu_item__name']
    ordering = ['-created_at']
    
    def price_display(self, obj):
        if obj.price_currency == 'IDR':
            return f"Rp {obj.price_amount:,.0f}"
        return f"{obj.price_currency} {obj.price_amount:,.2f}"
    price_display.short_description = 'Price'
    
    def subtotal_display(self, obj):
        if obj.subtotal_currency == 'IDR':
            return f"Rp {obj.subtotal_amount:,.0f}"
        return f"{obj.subtotal_currency} {obj.subtotal_amount:,.2f}"
    subtotal_display.short_description = 'Subtotal'


@admin.register(OrderTimeline)
class OrderTimelineAdmin(admin.ModelAdmin):
    """Admin untuk OrderTimeline model."""
    
    list_display = ['order', 'status', 'created_by', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order__order_number']
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        """Disable manual add (auto-created via signals)."""
        return False


@admin.register(CustomerAnalytics)
class CustomerAnalyticsAdmin(admin.ModelAdmin):
    """Admin untuk CustomerAnalytics model."""
    
    list_display = ['customer', 'total_orders', 'total_spent_display', 'average_order_display', 'last_order_date']
    list_filter = ['total_spent_currency', 'created_at']
    search_fields = ['customer__name', 'customer__phone_number']
    ordering = ['-total_spent_amount']
    
    readonly_fields = ['customer', 'total_orders', 'total_spent_amount', 'average_order_value', 'last_order_date']
    
    def total_spent_display(self, obj):
        if obj.total_spent_currency == 'IDR':
            return f"Rp {obj.total_spent_amount:,.0f}"
        return f"{obj.total_spent_currency} {obj.total_spent_amount:,.2f}"
    total_spent_display.short_description = 'Total Spent'
    
    def average_order_display(self, obj):
        if obj.total_spent_currency == 'IDR':
            return f"Rp {obj.average_order_value:,.0f}"
        return f"{obj.total_spent_currency} {obj.average_order_value:,.2f}"
    average_order_display.short_description = 'Avg Order Value'
    
    def has_add_permission(self, request):
        """Disable manual add (auto-created via signals)."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable delete."""
        return False
