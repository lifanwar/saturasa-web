"""Orders admin configuration."""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from apps.orders.models import Order, OrderItem, OrderTimeline, CustomerAnalytics, MenuOrderLog, OrderItemAddon, AddonOrderLog
from decimal import Decimal
# from .analytics import MenuAnalytics



class OrderItemInline(admin.TabularInline):
    """Inline untuk OrderItem di Order admin."""
    model = OrderItem
    extra = 0
    fields = ['menu_item', 'quantity', 'price_amount', 'price_currency', 'subtotal_amount', 'addon_summary', 'notes']
    readonly_fields = ['subtotal_amount', 'addon_summary']
    
    def addon_summary(self, obj):
        """Display ringkasan addon untuk item ini."""
        if obj and obj.pk:
            addons = obj.addons.all()
            if addons:
                addon_list = []
                for addon in addons:
                    addon_list.append(f"• {addon.name} ({addon.type}) x{addon.quantity} = Rp {addon.subtotal:,.0f}")
                return format_html('<br>'.join(addon_list))
            return "-"
        return "-"
    addon_summary.short_description = 'Addons'



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
        try:
            amount = Decimal(str(obj.total_amount))
        except (ValueError, TypeError, AttributeError):
            amount = Decimal('0')

        if obj.total_currency == 'IDR':
            formatted = f'Rp {amount:,.0f}'
        else:
            formatted = f'{obj.total_currency} {amount:,.2f}'

        return format_html('<strong>{}</strong>', formatted)

    total_display.short_description = 'Total'
    total_display.admin_order_field = 'total_amount'
    
    actions = ['mark_as_confirmed', 'mark_as_preparing', 'mark_as_ready', 'mark_as_completed', 'mark_as_cancelled']

    def mark_as_confirmed(self, request, queryset):
        """Confirm orders and RESERVE stock."""
        from django.db import transaction

        success = 0
        failed = []

        for order in queryset.filter(status='PENDING'):
            try:
                with transaction.atomic():
                    # Check & Reserve stock
                    stock_ok = True
                    errors = []

                    for item in order.items.select_related('menu_item'):
                        menu = item.menu_item
                        if not menu.is_unlimited_stock:
                            if menu.available_stock < item.quantity:
                                stock_ok = False
                                errors.append(f"{menu.name} (need {item.quantity}, available {menu.available_stock})")

                    if not stock_ok:
                        failed.append(f"{order.order_number}: {', '.join(errors)}")
                        continue
                    
                    # Reserve stock (not deduct yet)
                    for item in order.items.select_related('menu_item'):
                        if not item.menu_item.is_unlimited_stock:
                            item.menu_item.reserve_stock(item.quantity)

                    # Update order
                    order.status = 'CONFIRMED'
                    order.save()

                    OrderTimeline.objects.create(
                        order=order,
                        status='CONFIRMED',
                        note='Order confirmed, stock reserved',
                        created_by=request.user
                    )
                    success += 1
            except Exception as e:
                failed.append(f"{order.order_number}: {str(e)}")

        if success:
            self.message_user(request, f'✅ {success} order(s) confirmed, stock reserved', level='SUCCESS')
        if failed:
            self.message_user(request, f'❌ Failed: {"; ".join(failed)}', level='ERROR')

    mark_as_confirmed.short_description = '✅ Confirm orders (reserve stock)'

    def mark_as_preparing(self, request, queryset):
        """Mark as preparing and DEDUCT stock."""
        from django.db import transaction

        success = 0
        failed = []

        for order in queryset.filter(status='CONFIRMED'):
            try:
                with transaction.atomic():
                    # Check stock (seharusnya sudah reserved)
                    stock_ok = True
                    errors = []

                    for item in order.items.select_related('menu_item'):
                        menu = item.menu_item
                        if not menu.is_unlimited_stock:
                            if menu.stock_quantity < item.quantity:
                                stock_ok = False
                                errors.append(f"{menu.name} (need {item.quantity}, have {menu.stock_quantity})")

                    if not stock_ok:
                        failed.append(f"{order.order_number}: {', '.join(errors)}")
                        continue
                    
                    # Deduct stock (release reserved and reduce total)
                    for item in order.items.select_related('menu_item'):
                        if not item.menu_item.is_unlimited_stock:
                            item.menu_item.deduct_stock(item.quantity)

                    # Update order
                    order.status = 'PREPARING'
                    order.save()

                    OrderTimeline.objects.create(
                        order=order,
                        status='PREPARING',
                        note='Preparation started, stock deducted',
                        created_by=request.user
                    )
                    success += 1
            except Exception as e:
                failed.append(f"{order.order_number}: {str(e)}")

        if success:
            self.message_user(request, f'👨‍🍳 {success} order(s) preparing, stock deducted', level='SUCCESS')
        if failed:
            self.message_user(request, f'❌ Failed: {"; ".join(failed)}', level='ERROR')

    mark_as_preparing.short_description = '👨‍🍳 Mark as Preparing (deduct stock)'

    def mark_as_ready(self, request, queryset):
        """Mark as ready (no stock action)."""
        count = 0
        for order in queryset.filter(status='PREPARING'):
            order.status = 'READY'
            order.save()

            OrderTimeline.objects.create(
                order=order,
                status='READY',
                note='Order ready',
                created_by=request.user
            )
            count += 1

        self.message_user(request, f'🔔 {count} order(s) ready')
    mark_as_ready.short_description = '🔔 Mark as Ready'

    def mark_as_completed(self, request, queryset):
        """Mark as completed (no stock action)."""
        count = 0
        for order in queryset.filter(status__in=['READY', 'PREPARING']):
            order.status = 'COMPLETED'
            order.save()

            OrderTimeline.objects.create(
                order=order,
                status='COMPLETED',
                note='Order completed',
                created_by=request.user
            )
            count += 1

        self.message_user(request, f'✔️ {count} order(s) completed')
    mark_as_completed.short_description = '✔️ Mark as Completed'

    def mark_as_cancelled(self, request, queryset):
        """Cancel orders and release/restore stock."""
        from django.db import transaction
        
        count = 0
        for order in queryset.filter(status__in=['PENDING', 'CONFIRMED', 'PREPARING']):
            with transaction.atomic():
                # Determine stock action based on status
                if order.status == 'CONFIRMED':
                    # Release reserved stock
                    for item in order.items.select_related('menu_item'):
                        if not item.menu_item.is_unlimited_stock:
                            item.menu_item.release_stock(item.quantity)
                    note = 'Order cancelled, reserved stock released'
                
                elif order.status == 'PREPARING':
                    # Restore deducted stock (add back to stock_quantity)
                    for item in order.items.select_related('menu_item'):
                        menu = item.menu_item
                        if not menu.is_unlimited_stock:
                            menu.stock_quantity += item.quantity
                            menu.save(update_fields=['stock_quantity'])
                    note = 'Order cancelled, deducted stock restored'
                
                else:  # PENDING
                    note = 'Order cancelled'
                
                # Update order
                order.status = 'CANCELLED'
                order.save()
                
                OrderTimeline.objects.create(
                    order=order,
                    status='CANCELLED',
                    note=note,
                    created_by=request.user
                )
                count += 1
        
        self.message_user(request, f'❌ {count} order(s) cancelled')
    mark_as_cancelled.short_description = '❌ Cancel orders'
    



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

@admin.register(MenuOrderLog)
class MenuOrderLogAdmin(admin.ModelAdmin):
    """Admin untuk Menu Order Log."""
    
    list_display = ['order_number', 'menu_item_name', 'quantity', 'subtotal_display', 'completed_date', 'order_type']
    list_filter = ['completed_year_month', 'category_name', 'order_type', 'order_channel', 'completed_date']
    search_fields = ['order_number', 'menu_item_name']
    ordering = ['-completed_at']
    date_hierarchy = 'completed_date'
    
    fieldsets = (
        ('Order Info', {
            'fields': ('order_number', 'order_type', 'order_channel')
        }),
        ('Menu Info', {
            'fields': ('menu_item_id', 'menu_item_name', 'category_name')
        }),
        ('Transaction', {
            'fields': ('quantity', 'price_amount', 'price_currency', 'subtotal_amount')
        }),
        ('Time Dimensions', {
            'fields': ('completed_at', 'completed_date', 'completed_year_month', 'completed_year')
        }),
    )
    
    readonly_fields = [
        'order_number', 'order_type', 'order_channel',
        'menu_item_id', 'menu_item_name', 'category_name',
        'quantity', 'price_amount', 'price_currency', 'subtotal_amount',
        'completed_at', 'completed_date', 'completed_year_month', 'completed_year'
    ]
    
    def subtotal_display(self, obj):
        """Format subtotal dengan currency."""
        if obj.price_currency == 'IDR':
            return f"Rp {obj.subtotal_amount:,.0f}"
        return f"{obj.price_currency} {obj.subtotal_amount:,.2f}"
    subtotal_display.short_description = 'Subtotal'
    subtotal_display.admin_order_field = 'subtotal_amount'

    def has_add_permission(self, request):
        """Disable manual add (auto-created via signal)."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable edit (immutable log)."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow delete only for superuser (cleanup old data)."""
        return request.user.is_superuser

class OrderItemAddonInline(admin.TabularInline):
    """Inline untuk OrderItemAddon di OrderItem admin."""
    model = OrderItemAddon
    extra = 0
    fields = ['menu_addon', 'name', 'type', 'quantity', 'price_amount', 'price_currency', 'subtotal_display']
    readonly_fields = ['subtotal_display']
    
    def subtotal_display(self, obj):
        """Display subtotal dengan format IDR."""
        if obj and obj.price_amount:
            return f"Rp {obj.subtotal:,.0f}"
        return "-"
    subtotal_display.short_description = 'Subtotal'


@admin.register(OrderItemAddon)
class OrderItemAddonAdmin(admin.ModelAdmin):
    """Admin untuk OrderItemAddon model."""
    
    list_display = ['order_item', 'name', 'type', 'quantity', 'price_display', 'subtotal_display', 'created_at']
    list_filter = ['type', 'created_at']
    search_fields = ['order_item__order__order_number', 'name', 'order_item__menu_item__name']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Order Item Info', {
            'fields': ('order_item', 'menu_addon')
        }),
        ('Addon Details (Snapshot)', {
            'fields': ('name', 'type', 'quantity', 'price_amount', 'price_currency')
        }),
        ('System', {
            'fields': ('restaurant_id',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['order_item', 'menu_addon', 'name', 'type', 'quantity', 'price_amount', 'price_currency']
    
    def price_display(self, obj):
        return f"Rp {obj.price_amount:,.0f}"
    price_display.short_description = 'Price'
    
    def subtotal_display(self, obj):
        return f"Rp {obj.subtotal:,.0f}"
    subtotal_display.short_description = 'Subtotal'
    
    def has_add_permission(self, request):
        """Disable manual add (created via checkout)."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable edit (immutable snapshot)."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow delete only for superuser."""
        return request.user.is_superuser

@admin.register(AddonOrderLog)
class AddonOrderLogAdmin(admin.ModelAdmin):
    """Admin untuk Addon Order Log."""
    
    list_display = ['order_number', 'menu_item_name', 'addon_name', 'addon_type', 'quantity', 'subtotal_display', 'completed_date']
    list_filter = ['completed_year_month', 'addon_type', 'order_type', 'order_channel', 'completed_date']
    search_fields = ['order_number', 'addon_name', 'menu_item_name']
    ordering = ['-completed_at']
    date_hierarchy = 'completed_date'
    
    fieldsets = (
        ('Order Info', {
            'fields': ('order_number', 'order_type', 'order_channel')
        }),
        ('Menu Info', {
            'fields': ('menu_item_id', 'menu_item_name')
        }),
        ('Addon Info', {
            'fields': ('addon_id', 'addon_name', 'addon_type')
        }),
        ('Transaction', {
            'fields': ('quantity', 'price_amount', 'price_currency', 'subtotal_amount')
        }),
        ('Time Dimensions', {
            'fields': ('completed_at', 'completed_date', 'completed_year_month', 'completed_year')
        }),
    )
    
    readonly_fields = [
        'order_number', 'order_type', 'order_channel',
        'menu_item_id', 'menu_item_name',
        'addon_id', 'addon_name', 'addon_type',
        'quantity', 'price_amount', 'price_currency', 'subtotal_amount',
        'completed_at', 'completed_date', 'completed_year_month', 'completed_year'
    ]
    
    def subtotal_display(self, obj):
        """Format subtotal dengan currency."""
        if obj.price_currency == 'IDR':
            return f"Rp {obj.subtotal_amount:,.0f}"
        return f"{obj.price_currency} {obj.subtotal_amount:,.2f}"
    subtotal_display.short_description = 'Subtotal'
    subtotal_display.admin_order_field = 'subtotal_amount'
    
    def has_add_permission(self, request):
        """Disable manual add (auto-created via signal)."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable edit (immutable log)."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow delete only for superuser (cleanup old data)."""
        return request.user.is_superuser
