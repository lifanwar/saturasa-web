"""Order signals for auto-populate analytics."""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Order, MenuOrderLog


@receiver(post_save, sender=Order)
def log_completed_order(sender, instance, created, **kwargs):
    """Auto-create MenuOrderLog entries when order COMPLETED."""
    
    # Only trigger when status is COMPLETED
    if instance.status != 'COMPLETED':
        return
    
    # Prevent duplicate logs (idempotent)
    if MenuOrderLog.objects.filter(order_number=instance.order_number).exists():
        return
    
    # Get completion timestamp
    completed_at = instance.updated_at or timezone.now()
    
    # Create log entry for each OrderItem
    for item in instance.items.select_related('menu_item', 'menu_item__category'):
        MenuOrderLog.objects.create(
            # Order context
            order_number=instance.order_number,
            order_type=instance.order_type,
            order_channel=instance.order_channel,
            
            # Menu info (snapshot)
            menu_item_id=item.menu_item.id,
            menu_item_name=item.menu_item.name,
            category_name=item.menu_item.category.name,
            
            # Transaction details
            quantity=item.quantity,
            price_amount=item.price_amount,
            price_currency=item.price_currency,
            subtotal_amount=item.subtotal_amount,
            
            # Time dimensions (pre-computed)
            completed_at=completed_at,
            completed_date=completed_at.date(),
            completed_year_month=completed_at.strftime('%Y-%m'),
            completed_year=completed_at.year,
        )
