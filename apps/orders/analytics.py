"""Analytics helper functions."""
from django.db.models import Sum, Count, Avg
from datetime import datetime, timedelta
from .models import MenuOrderLog


class MenuAnalytics:
    """Helper class untuk menu analytics queries."""
    
    @staticmethod
    def best_sellers(period='monthly', year_month=None, limit=10):
        """Get best sellers by period.
        
        Args:
            period: 'daily', 'monthly', 'yearly'
            year_month: '2025-01' (for monthly), None for current
            limit: Top N items
        """
        queryset = MenuOrderLog.objects.all()
        
        if period == 'daily':
            today = datetime.now().date()
            queryset = queryset.filter(completed_date=today)
        elif period == 'monthly':
            if not year_month:
                year_month = datetime.now().strftime('%Y-%m')
            queryset = queryset.filter(completed_year_month=year_month)
        elif period == 'yearly':
            year = datetime.now().year
            queryset = queryset.filter(completed_year=year)
        
        return queryset.values(
            'menu_item_id', 'menu_item_name', 'category_name'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_orders=Count('order_number', distinct=True),
            total_revenue=Sum('subtotal_amount')
        ).order_by('-total_quantity')[:limit]
    
    @staticmethod
    def daily_revenue(date=None):
        """Get total revenue for specific date."""
        if not date:
            date = datetime.now().date()
        
        return MenuOrderLog.objects.filter(
            completed_date=date
        ).aggregate(
            total_orders=Count('order_number', distinct=True),
            total_items=Sum('quantity'),
            total_revenue=Sum('subtotal_amount')
        )
    
    @staticmethod
    def monthly_revenue(year_month=None):
        """Get total revenue for specific month."""
        if not year_month:
            year_month = datetime.now().strftime('%Y-%m')
        
        return MenuOrderLog.objects.filter(
            completed_year_month=year_month
        ).aggregate(
            total_orders=Count('order_number', distinct=True),
            total_items=Sum('quantity'),
            total_revenue=Sum('subtotal_amount')
        )
    
    @staticmethod
    def menu_performance(menu_item_id, days=30):
        """Get performance for specific menu item (last N days)."""
        start_date = datetime.now().date() - timedelta(days=days)
        
        return MenuOrderLog.objects.filter(
            menu_item_id=menu_item_id,
            completed_date__gte=start_date
        ).values('completed_date').annotate(
            daily_quantity=Sum('quantity'),
            daily_revenue=Sum('subtotal_amount')
        ).order_by('completed_date')
    
    @staticmethod
    def category_performance(year_month=None):
        """Get revenue breakdown by category."""
        if not year_month:
            year_month = datetime.now().strftime('%Y-%m')
        
        return MenuOrderLog.objects.filter(
            completed_year_month=year_month
        ).values('category_name').annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('subtotal_amount')
        ).order_by('-total_revenue')
    
    @staticmethod
    def update_best_seller_flags(year_month=None):
        """Update MenuItem.is_best_seller based on monthly performance."""
        from apps.menu.models import MenuItem
        
        if not year_month:
            year_month = datetime.now().strftime('%Y-%m')
        
        # Get top 10 menu this month
        top_menus = MenuOrderLog.objects.filter(
            completed_year_month=year_month
        ).values('menu_item_id').annotate(
            total_qty=Sum('quantity')
        ).order_by('-total_qty')[:10]
        
        # Reset all
        MenuItem.objects.update(is_best_seller=False)
        
        # Set top 10
        top_ids = [item['menu_item_id'] for item in top_menus]
        updated = MenuItem.objects.filter(id__in=top_ids).update(is_best_seller=True)
        
        return updated
