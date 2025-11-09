# apps/customers/forms.py

from django import forms
from .models import Customer

class MemberProfileForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone_number', 'date_of_birth']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Nama lengkap Anda',
                'required': True,
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': '08123456789',
                'required': True,
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'date',
                'required': True,
            }),
        }
        labels = {
            'name': 'Nama Lengkap',
            'phone_number': 'Nomor Telepon',
            'date_of_birth': 'Tanggal Lahir',
        }
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        
        # Check if phone already exists (excluding current user if editing)
        existing = Customer.objects.filter(phone_number=phone)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        
        if existing.exists():
            raise forms.ValidationError('Nomor telepon ini sudah terdaftar')
        
        # Validate format
        if not phone.isdigit():
            raise forms.ValidationError('Nomor telepon hanya boleh berisi angka')
        
        if len(phone) < 10 or len(phone) > 15:
            raise forms.ValidationError('Nomor telepon harus 10-15 digit')
        
        return phone
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if len(name) < 3:
            raise forms.ValidationError('Nama minimal 3 karakter')
        return name
