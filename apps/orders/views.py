"""Order views."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from .models import Order, OrderItem, OrderTimeline
from .utils import generate_order_number
from apps.menu.models import MenuItem
import json


def checkout_view(request):
    """Show checkout page dengan cart items."""
    if request.method == 'POST':
        try:
            # Get cart data dari POST (hanya id + quantity)
            cart_data = json.loads(request.POST.get('cart_data', '[]'))
            
            if not cart_data:
                messages.error(request, 'Cart kosong!')
                return redirect('menu:menu_list')
            
            # Validate & build cart items dengan data dari DB
            cart_items = []
            total = 0
            currency = 'IDR'
            
            for item in cart_data:
                try:
                    menu_item = MenuItem.objects.get(
                        id=item['id'],
                        is_available=True
                    )
                    
                    quantity = int(item['quantity'])
                    if quantity <= 0:
                        continue
                    
                    subtotal = menu_item.price_amount * quantity
                    
                    cart_items.append({
                        'id': menu_item.id,
                        'name': menu_item.name,
                        'price': menu_item.price_amount,
                        'currency': menu_item.price_currency,
                        'quantity': quantity,
                        'subtotal': subtotal,
                    })
                    
                    total += subtotal
                    currency = menu_item.price_currency
                    
                except MenuItem.DoesNotExist:
                    continue
            
            if not cart_items:
                messages.error(request, 'Tidak ada item valid di cart!')
                return redirect('menu:menu_list')
            
            # Render checkout page dengan validated data
            context = {
                'cart_items': cart_items,
                'total': total,
                'currency': currency,
                'cart_data_json': json.dumps([{'id': item['id'], 'quantity': item['quantity']} for item in cart_items])
            }
            
            return render(request, 'orders/checkout.html', context)
        
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('menu:menu_list')
    
    # GET request - redirect ke menu
    return redirect('menu:menu_list')


def checkout_confirm(request):
    """Process order confirmation."""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Get form data
                customer_name = request.POST.get('customer_name', '').strip()
                order_type = request.POST.get('order_type')
                cart_data = json.loads(request.POST.get('cart_data', '[]'))
                
                # Validation
                if not customer_name:
                    messages.error(request, 'Nama wajib diisi!')
                    return redirect('menu:menu_list')
                
                if order_type not in ['DINE_IN', 'TAKEAWAY']:
                    messages.error(request, 'Tipe order tidak valid!')
                    return redirect('menu:menu_list')
                
                if not cart_data:
                    messages.error(request, 'Cart kosong!')
                    return redirect('menu:menu_list')
                
                # Create Order
                order = Order.objects.create(
                    order_number=generate_order_number(),
                    customer=None,
                    offline_customer_name=customer_name,
                    order_type=order_type,
                    order_channel='OFFLINE',
                    status='PENDING',
                    subtotal_amount=0,
                    subtotal_currency='IDR',
                    total_amount=0,
                    total_currency='IDR',
                )
                
                # Create Order Items dengan validasi
                subtotal = 0
                for item in cart_data:
                    try:
                        menu_item = MenuItem.objects.get(
                            id=item['id'],
                            is_available=True
                        )
                        
                        quantity = int(item['quantity'])
                        if quantity <= 0:
                            continue
                        
                        order_item = OrderItem.objects.create(
                            order=order,
                            menu_item=menu_item,
                            quantity=quantity,
                            price_amount=menu_item.price_amount,
                            price_currency=menu_item.price_currency,
                        )
                        
                        subtotal += order_item.subtotal_amount
                    
                    except MenuItem.DoesNotExist:
                        continue
                
                # Update order totals
                order.subtotal_amount = subtotal
                order.total_amount = subtotal
                order.save()
                
                # Create Timeline
                OrderTimeline.objects.create(
                    order=order,
                    status='PENDING',
                    note='Order created, waiting for admin confirmation'
                )
                
                messages.success(request, f'Order berhasil! Nomor: {order.order_number}')
                return redirect('orders:order_success', order_number=order.order_number)
        
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('menu:menu_list')
    
    return redirect('menu:menu_list')


def order_success(request, order_number):
    """Order success page."""
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, 'orders/order_success.html', {'order': order})
