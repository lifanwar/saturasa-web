"""Order signals for auto-populate analytics."""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from apps.orders.models import Order, MenuOrderLog, AddonOrderLog

@receiver(post_save, sender=Order)
def log_completed_order(sender, instance, created, **kwargs):
    """Auto-create MenuOrderLog and AddonOrderLog when order COMPLETED."""
    # Only trigger when status is COMPLETED
    if instance.status != 'COMPLETED':
        return
    # Prevent duplicate logs (idempotent)
    if MenuOrderLog.objects.filter(order_number=instance.order_number).exists():
        return
    completed_at = instance.updated_at or timezone.now()
    for item in instance.items.select_related('menu_item', 'menu_item__category'):
        # Log utama (MenuOrderLog)
        MenuOrderLog.objects.create(
            order_number=instance.order_number,
            order_type=instance.order_type,
            order_channel=instance.order_channel,
            menu_item_id=item.menu_item.id,
            menu_item_name=item.menu_item.name,
            category_name=item.menu_item.category.name if item.menu_item.category else "",
            quantity=item.quantity,
            price_amount=item.price_amount,
            price_currency=item.price_currency,
            subtotal_amount=item.subtotal_amount,
            completed_at=completed_at,
            completed_date=completed_at.date(),
            completed_year_month=completed_at.strftime('%Y-%m'),
            completed_year=completed_at.year,
        )
        # Log Addon (AddonOrderLog)
        # Pastikan ada model OrderItemAddon yang menyimpan addons untuk item ini
        for addon in item.addons.all():
            AddonOrderLog.objects.create(
                order_number=instance.order_number,
                order_type=instance.order_type,
                order_channel=instance.order_channel,
                menu_item_id=item.menu_item.id,
                menu_item_name=item.menu_item.name,
                addon_id=addon.menu_addon.id,
                addon_name=addon.name,
                addon_type=addon.type,
                quantity=addon.quantity,
                price_amount=addon.price_amount,
                price_currency=addon.price_currency,
                subtotal_amount=addon.price_amount * addon.quantity,
                completed_at=completed_at,
                completed_date=completed_at.date(),
                completed_year_month=completed_at.strftime('%Y-%m'),
                completed_year=completed_at.year,
            )
