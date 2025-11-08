"""Menu views."""
from django.shortcuts import render
from django.http import JsonResponse
from .models import Category, MenuItem
import json


def menu_list(request):
    """Main menu page - Load data dari database."""
    categories = Category.objects.filter(is_active=True)
    
    # Best sellers
    best_sellers = MenuItem.objects.filter(
        is_best_seller=True,
        is_available=True
    ).select_related('category')[:6]
    
    # All available menu items grouped by category
    menu_items = MenuItem.objects.filter(
        is_available=True
    ).select_related('category')
    
    context = {
        'categories': categories,
        'best_sellers': best_sellers,
        'menu_items': menu_items,
    }
    
    return render(request, 'menu/menu_list.html', context)


def menu_items_json(request):
    """API endpoint untuk Alpine.js - Return JSON."""
    category_slug = request.GET.get('category', 'all')
    
    queryset = MenuItem.objects.filter(is_available=True).select_related('category')
    
    if category_slug != 'all':
        queryset = queryset.filter(category__slug=category_slug)
    
    items = []
    for item in queryset:
        items.append({
            'id': item.id,
            'name': item.name,
            'description': item.description,
            'price': float(item.price_amount),
            'currency': item.price_currency,
            'image': item.image.url if item.image else 'https://picsum.photos/300/200',
            'is_best_seller': item.is_best_seller,
            'is_new': item.is_new,
            'category': item.category.slug,
        })
    
    return JsonResponse({'items': items})
