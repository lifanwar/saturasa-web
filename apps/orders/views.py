"""Order views."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from apps.orders.models import Order, OrderItem, OrderTimeline, OrderItemAddon
from apps.menu.models import MenuAddon
from .utils import generate_order_number
from apps.menu.models import MenuItem
import json
from decimal import Decimal


def checkout_view(request):
    """Show checkout page dengan cart items + addons (IDR only)."""
    if request.method == 'POST':
        try:
            cart_data = json.loads(request.POST.get('cart_data', '[]'))
            
            if not cart_data:
                messages.error(request, 'Cart kosong!')
                return redirect('menu:menu_list')
            
            request.session['checkout_cart'] = cart_data
            if request.user.is_authenticated and hasattr(request.user, 'customer'):
                pass  # lanjut
            elif request.user.is_authenticated and not hasattr(request.user, 'customer'):
                request.session['checkout_redirect'] = True
                messages.warning(request, 'Anda harus mendaftar sebagai member untuk melanjutkan checkout.')
                return redirect('customers:register_member')
            
            cart_items = []
            total = 0

            for item in cart_data:
                try:
                    menu_item = MenuItem.objects.get(id=item['id'], is_available=True)
                    quantity = int(item['quantity'])
                    if quantity <= 0:
                        continue

                    if not menu_item.is_unlimited_stock:
                        if menu_item.is_out_of_stock():
                            messages.error(request, f'❌ {menu_item.name} sudah habis!')
                            return redirect('menu:menu_list')
                        if menu_item.available_stock < quantity:
                            messages.error(request, f'❌ Stock {menu_item.name} tidak cukup! Tersedia: {menu_item.available_stock} {menu_item.stock_unit}, Anda pesan: {quantity}.')
                            return redirect('menu:menu_list')

                    # === ADDONS LOGIC ===
                    addons_list = []
                    addons_total = 0
                    
                    addon_details = item.get('addon_details', [])
                    if addon_details:
                        addon_ids = [a['id'] for a in addon_details]
                        addons_objs = MenuAddon.objects.filter(id__in=addon_ids, is_active=True)
                        addons_map = {a.id: a for a in addons_objs}
                        for addon_data in addon_details:
                            addon_id = addon_data['id']
                            addon_qty = int(addon_data.get('quantity', 1))
                            if addon_id in addons_map:
                                addon = addons_map[addon_id]
                                addon_subtotal = addon.price * addon_qty
                                addons_total += addon_subtotal
                                addons_list.append({
                                    'id': addon.id,
                                    'name': addon.name,
                                    'type': addon.type,
                                    'price': addon.price,
                                    'quantity': addon_qty,
                                    'subtotal': addon_subtotal,
                                })
                    item_price = menu_item.price_amount + addons_total
                    subtotal = item_price * quantity
                    cart_items.append({
                        'id': menu_item.id,
                        'name': menu_item.name,
                        'price': menu_item.price_amount,
                        'quantity': quantity,
                        'addons': addons_list,
                        'addons_total': addons_total,
                        'item_price': item_price,
                        'subtotal': subtotal,
                    })
                    total += subtotal
                except MenuItem.DoesNotExist:
                    continue
            
            if not cart_items:
                messages.error(request, 'Tidak ada item valid di cart!')
                return redirect('menu:menu_list')

            cart_data_for_confirm = []
            for item in cart_items:
                cart_data_for_confirm.append({
                    'id': item['id'],
                    'quantity': item['quantity'],
                    'addon_details': [
                        {'id': a['id'], 'quantity': a['quantity']} 
                        for a in item['addons']
                    ]
                })
            context = {
                'cart_items': cart_items,
                'total': total,
                'cart_data_json': json.dumps(cart_data_for_confirm)
            }
            return render(request, 'orders/checkout.html', context)
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('menu:menu_list')
    return redirect('menu:menu_list')



def checkout_confirm(request):
    """Process order confirmation with security validation."""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                customer_name = request.POST.get('customer_name', '').strip()
                order_type = request.POST.get('order_type')

                cart_data_raw = request.POST.get('cart_data', '[]')
                if cart_data_raw == '[]' and 'checkout_cart' in request.session:
                    cart_data = request.session.get('checkout_cart')
                else:
                    cart_data = json.loads(cart_data_raw)
                
                customer = None
                if request.user.is_authenticated:
                    if hasattr(request.user, 'customer'):
                        customer = request.user.customer
                        customer_name = customer.name
                    else:
                        customer_name = request.user.get_full_name() or request.user.email.split('@')[0]
                
                # === VALIDATION ===
                if not customer_name:
                    messages.error(request, 'Nama wajib diisi!')
                    return redirect('menu:menu_list')
                
                if order_type not in ['DINE_IN', 'TAKEAWAY', 'DELIVERY']:
                    messages.error(request, 'Tipe order tidak valid!')
                    return redirect('menu:menu_list')
                
                if not cart_data or len(cart_data) == 0:
                    messages.error(request, 'Cart kosong!')
                    return redirect('menu:menu_list')
                
                # === SECURITY: Limit cart size ===
                if len(cart_data) > 50:  # Max 50 items per order
                    messages.error(request, 'Terlalu banyak item dalam cart!')
                    return redirect('menu:menu_list')
                
                # Create Order
                order = Order.objects.create(
                    order_number=generate_order_number(),
                    customer=customer, 
                    offline_customer_name=customer_name,
                    order_type=order_type,
                    order_channel='OFFLINE',
                    status='PENDING',
                    subtotal_amount=0,
                    subtotal_currency='IDR',
                    total_amount=0,
                    total_currency='IDR',
                )
                
                subtotal = Decimal('0')
                
                for item in cart_data:
                    try:
                        # === VALIDATE ITEM ===
                        menu_item = MenuItem.objects.get(
                            id=item['id'],
                            is_available=True
                        )
                        
                        quantity = int(item['quantity'])
                        
                        # === SECURITY: Validate quantity ===
                        if quantity <= 0:
                            continue
                        if quantity > 100:  # Max 100 per item
                            messages.error(request, f'Quantity {menu_item.name} terlalu besar (max 100)!')
                            order.delete()
                            return redirect('menu:menu_list')
                        
                        # Get base price FROM DATABASE (never trust frontend)
                        base_price = Decimal(str(menu_item.price_amount))
                        addons_total = Decimal('0')

                        # Create OrderItem
                        order_item = OrderItem.objects.create(
                            order=order,
                            menu_item=menu_item,
                            quantity=quantity,
                            price_amount=base_price,
                            price_currency='IDR',
                        )

                        # === VALIDATE & SAVE ADDONS ===
                        addon_details = item.get('addon_details', [])
                        
                        # Security: Limit addon count
                        if len(addon_details) > 20:
                            messages.error(request, 'Terlalu banyak addon per item!')
                            order.delete()
                            return redirect('menu:menu_list')
                        
                        for a in addon_details:
                            try:
                                addon = MenuAddon.objects.get(
                                    id=a['id'], 
                                    is_active=True
                                )
                                
                                addon_qty = int(a.get('quantity', 1))
                                
                                # === SECURITY: Validate addon quantity ===
                                if addon_qty <= 0:
                                    continue
                                if addon_qty > 50:  # Max 50 per addon
                                    messages.error(request, f'Quantity addon {addon.name} terlalu besar!')
                                    order.delete()
                                    return redirect('menu:menu_list')
                                
                                # Get addon price FROM DATABASE
                                addon_price = Decimal(str(addon.price))
                                addon_subtotal = addon_price * addon_qty
                                addons_total += addon_subtotal

                                OrderItemAddon.objects.create(
                                    order_item=order_item,
                                    menu_addon=addon,
                                    name=addon.name,
                                    type=addon.type,
                                    quantity=addon_qty,
                                    price_amount=addon_price,
                                    price_currency='IDR',
                                )
                            except (MenuAddon.DoesNotExist, ValueError, KeyError):
                                continue
                        
                        # Calculate subtotal: (base + addons) * quantity
                        item_subtotal = (base_price + addons_total) * quantity
                        order_item.subtotal_amount = item_subtotal
                        order_item.save()
                        
                        subtotal += item_subtotal
                        
                    except (MenuItem.DoesNotExist, ValueError, KeyError):
                        continue
                
                # === SECURITY: Final validation ===
                if subtotal <= 0:
                    messages.error(request, 'Total order tidak valid!')
                    order.delete()
                    return redirect('menu:menu_list')
                
                # Update totals
                order.subtotal_amount = subtotal
                order.total_amount = subtotal
                order.save()
                
                # Create Timeline
                OrderTimeline.objects.create(
                    order=order,
                    status='PENDING',
                    note='Order created, waiting admin confirmation'
                )
                
                # Clear session cart
                if 'checkout_cart' in request.session:
                    del request.session['checkout_cart']
                
                messages.success(request, f'Order berhasil! Nomor: {order.order_number}')
                return redirect('orders:order_success', order_number=order.order_number)
        
        except json.JSONDecodeError:
            messages.error(request, 'Data cart tidak valid!')
            return redirect('menu:menu_list')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('menu:menu_list')
    
    return redirect('menu:menu_list')



def order_success(request, order_number):
    """Order success page."""
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, 'orders/order_success.html', {'order': order})
