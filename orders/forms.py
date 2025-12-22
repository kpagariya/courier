"""
Forms for order management
"""
from django import forms
from .models import Order, OrderConcern, DeliverySpeedOption, DeliveryType


class OrderForm(forms.ModelForm):
    """Form for creating courier orders"""
    
    delivery_speed = forms.ChoiceField(
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Delivery Type'
    )
    
    is_oversize = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Oversize Item',
        help_text='Check if item is too large for a standard car (e.g., longer than 1m or bulky dimensions)'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Try new DeliveryType model first, fallback to legacy
        delivery_types = DeliveryType.objects.filter(is_active=True).order_by('display_order')
        if delivery_types.exists():
            self.fields['delivery_speed'].choices = [(dt.code, dt.name) for dt in delivery_types]
            self.fields['delivery_speed'].initial = delivery_types.first().code
        else:
            # Fallback to legacy DeliverySpeedOption
            speed_options = DeliverySpeedOption.objects.filter(is_active=True).order_by('order')
            self.fields['delivery_speed'].choices = [(opt.code, opt.name) for opt in speed_options]
            if speed_options.exists():
                self.fields['delivery_speed'].initial = speed_options.first().code
    
    class Meta:
        model = Order
        fields = [
            'parcel_type', 'delivery_speed', 'is_oversize', 'pickup_address', 'delivery_address', 'parcel_weight',
            'quantity', 'description', 'parcel_image', 'customer_proposed_price'
        ]
        widgets = {
            'parcel_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'pickup_address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter full pickup address including street, city, and postal code',
                'id': 'pickup-address'
            }),
            'delivery_address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter full delivery address including street, city, and postal code',
                'id': 'delivery-address'
            }),
            'parcel_weight': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Weight in kg',
                'step': '0.01',
                'min': '0.01'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Number of parcels',
                'min': '1'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any additional notes or special instructions (optional)'
            }),
            'parcel_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'required': True
            }),
            'customer_proposed_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your counter-offer (optional)',
                'step': '0.01',
                'min': '0'
            })
        }
        labels = {
            'parcel_type': 'Parcel Type',
            'delivery_speed': 'Delivery Speed',
            'pickup_address': 'Pickup Address',
            'delivery_address': 'Delivery Address',
            'parcel_weight': 'Parcel Weight (kg)',
            'quantity': 'Number of Parcels',
            'description': 'Additional Notes',
            'parcel_image': 'Parcel Image (Required)',
            'customer_proposed_price': 'Your Preferred Price (NZD)'
        }
    
    def clean_parcel_weight(self):
        """Validate parcel weight"""
        weight = self.cleaned_data.get('parcel_weight')
        if weight and weight <= 0:
            raise forms.ValidationError('Weight must be greater than 0')
        if weight and weight > 1000:
            raise forms.ValidationError('Weight cannot exceed 1000 kg')
        return weight
    
    def clean_quantity(self):
        """Validate quantity"""
        quantity = self.cleaned_data.get('quantity')
        if quantity and quantity <= 0:
            raise forms.ValidationError('Quantity must be at least 1')
        if quantity and quantity > 100:
            raise forms.ValidationError('Quantity cannot exceed 100')
        return quantity
    
    def clean_parcel_image(self):
        """Validate parcel image is provided"""
        image = self.cleaned_data.get('parcel_image')
        if not image:
            raise forms.ValidationError('Parcel image is required. Please upload a photo of your parcel.')
        return image


class OrderConcernForm(forms.ModelForm):
    """Form for raising concerns about orders"""
    
    class Meta:
        model = OrderConcern
        fields = ['concern_type', 'subject', 'description', 'concern_image']
        widgets = {
            'concern_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief subject of your concern'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe your concern in detail'
            }),
            'concern_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
        labels = {
            'concern_type': 'Type of Concern',
            'subject': 'Subject',
            'description': 'Description',
            'concern_image': 'Photo of Issue (Optional)'
        }

