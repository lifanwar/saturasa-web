"""Order utility functions."""
import random
import string
from datetime import datetime


def generate_order_number():
    """
    Generate unique order number: ORD-XXXXX-YYYYMMDD-NNN
    Example: ORD-A1B2C-20250108-001
    """
    from apps.orders.models import Order
    
    # Random 5 character code (uppercase + digits)
    random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    
    # Current date
    today = datetime.now().date()
    today_str = today.strftime('%Y%m%d')
    
    # Count orders today
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    order_count = Order.objects.filter(
        created_at__range=(today_start, today_end)
    ).count() + 1
    
    # Format: ORD-AB12C-20250108-001
    order_number = f"ORD-{random_code}-{today_str}-{order_count:03d}"
    
    return order_number
