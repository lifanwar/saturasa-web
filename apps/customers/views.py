# apps/customers/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date
from .models import Customer
from .forms import MemberProfileForm

@login_required
def dashboard(request):
    """
    Dashboard utama - auto check apakah Customer exists
    """
    # Check if Customer exists for this logged-in user
    try:
        customer = Customer.objects.get(user=request.user)
        
        # Customer exists = member lengkap, show dashboard
        orders = customer.orders.all().order_by('-created_at')[:10]
        
        # Calculate age from date_of_birth
        today = date.today()
        dob = customer.date_of_birth
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        
        context = {
            'customer': customer,
            'orders': orders,
            'customer_age': age,  # NEW - pass age to template
        }
        return render(request, 'customers/dashboard.html', context)
        
    except Customer.DoesNotExist:
        # Customer not exists = perlu register sebagai member
        messages.info(request, 'Silakan lengkapi data Anda untuk menjadi member')
        return redirect('customers:register_member')


@login_required
def register_member(request):
    """
    Form untuk register member setelah login Google
    """
    # Double check - kalau sudah ada Customer, redirect ke dashboard
    if hasattr(request.user, 'customer'):
        messages.info(request, 'Anda sudah terdaftar sebagai member!')
        return redirect('customers:dashboard')
    
    if request.method == 'POST':
        form = MemberProfileForm(request.POST)
        if form.is_valid():
            # Create Customer linked to current user
            customer = form.save(commit=False)
            customer.user = request.user
            customer.save()
            
            messages.success(
                request, 
                f'Selamat {customer.name}! Anda sekarang terdaftar sebagai member.'
            )
            return redirect('customers:dashboard')
    else:
        # Pre-fill name from Google account
        initial_data = {
            'name': request.user.get_full_name() or request.user.email.split('@')[0]
        }
        form = MemberProfileForm(initial=initial_data)
    
    context = {
        'form': form,
        'user': request.user,
    }
    return render(request, 'customers/form_member.html', context)
