"""
Admin configuration for orders app
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Order, UserDelivery, PricingConfiguration, OrderConcern, PricingTier, DeliverySpeedOption, DeliveryType, PricingRule


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin interface for Order model"""
    
    list_display = (
        'order_id', 'customer_name', 'status_badge', 'auto_calculated_amount',
        'customer_proposed_price', 'courier_amount', 'is_paid', 'created_at', 'delivered_at'
    )
    list_filter = ('status', 'is_paid', 'created_at')
    search_fields = ('order_id', 'customer__email', 'customer__first_name', 'customer__last_name')
    readonly_fields = ('order_id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_id', 'customer', 'status')
        }),
        ('Parcel Details', {
            'fields': (
                'parcel_type', 'delivery_speed', 'is_oversize',
                'pickup_address', 'delivery_address', 
                'pickup_latitude', 'pickup_longitude', 'delivery_latitude', 'delivery_longitude',
                'distance_km', 'parcel_weight', 'quantity', 'length', 'width', 'height', 
                'description', 'parcel_image', 'delivery_proof_image'
            )
        }),
        ('Pricing & Payment', {
            'fields': ('auto_calculated_amount', 'customer_proposed_price', 'courier_amount', 'is_paid'),
            'description': 'Auto-calculated shows system estimate. Customer proposed is their counter-offer. Set final courier_amount.'
        }),
        ('Admin Information', {
            'fields': ('admin_notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'accepted_at', 'picked_at', 'delivered_at'),
            'classes': ('collapse',)
        }),
    )
    
    def customer_name(self, obj):
        """Display customer name"""
        return obj.customer.get_full_name()
    customer_name.short_description = 'Customer'
    
    def status_badge(self, obj):
        """Display status as colored badge"""
        colors = {
            'UNDER_REVIEW': '#ffc107',
            'ACCEPTED': '#17a2b8',
            'REJECTED': '#dc3545',
            'PICKED': '#007bff',
            'ON_THE_WAY': '#007bff',
            'DELIVERED': '#28a745',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def save_model(self, request, obj, form, change):
        """Update timestamps based on status changes and send emails"""
        from orders.utils import (
            send_order_accepted_email, send_order_rejected_email,
            send_order_picked_email, send_order_on_the_way_email,
            send_order_delivered_email, send_payment_confirmation_email
        )
        
        old_status = None
        old_is_paid = None
        
        if change:  # Editing existing order
            # Get the old status before changes
            old_obj = Order.objects.get(pk=obj.pk)
            old_status = old_obj.status
            old_is_paid = old_obj.is_paid
            
            # Update timestamps based on status changes
            if obj.status == 'ACCEPTED' and not obj.accepted_at:
                obj.accepted_at = timezone.now()
            elif obj.status == 'PICKED' and not obj.picked_at:
                obj.picked_at = timezone.now()
            elif obj.status == 'DELIVERED' and not obj.delivered_at:
                obj.delivered_at = timezone.now()
        
        super().save_model(request, obj, form, change)
        
        # Send emails after saving (only if status changed)
        if change and old_status != obj.status:
            try:
                if obj.status == 'ACCEPTED':
                    send_order_accepted_email(obj)
                elif obj.status == 'REJECTED':
                    send_order_rejected_email(obj)
                elif obj.status == 'PICKED':
                    send_order_picked_email(obj)
                elif obj.status == 'ON_THE_WAY':
                    send_order_on_the_way_email(obj)
                elif obj.status == 'DELIVERED':
                    send_order_delivered_email(obj)
            except Exception as e:
                print(f"Error sending status change email: {e}")
        
        # Send payment confirmation email
        if change and not old_is_paid and obj.is_paid:
            try:
                send_payment_confirmation_email(obj)
            except Exception as e:
                print(f"Error sending payment confirmation email: {e}")


@admin.register(UserDelivery)
class UserDeliveryAdmin(admin.ModelAdmin):
    """Admin interface for UserDelivery model"""
    
    list_display = ('order', 'customer', 'assigned_at')
    list_filter = ('assigned_at',)
    search_fields = ('order__order_id', 'customer__email')
    readonly_fields = ('assigned_at',)


@admin.register(PricingConfiguration)
class PricingConfigurationAdmin(admin.ModelAdmin):
    """Admin interface for Pricing Configuration"""
    
    list_display = ('base_price', 'price_per_km', 'price_per_kg', 'allow_customer_negotiation', 'updated_at')
    list_editable = ('allow_customer_negotiation',)  # Quick edit from list view
    readonly_fields = ('updated_at',)
    
    fieldsets = (
        ('Pricing Rates', {
            'fields': ('base_price', 'price_per_km', 'price_per_kg'),
            'description': 'Set the base pricing rates for delivery calculations'
        }),
        ('Customer Options', {
            'fields': ('allow_customer_negotiation',),
            'description': 'Enable/disable customer price negotiation feature. When enabled, customers can propose their own price during order creation.'
        }),
        ('System Information', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Only allow one pricing configuration
        return not PricingConfiguration.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PricingTier)
class PricingTierAdmin(admin.ModelAdmin):
    """Admin interface for Pricing Tiers"""
    
    list_display = ('name', 'weight_range', 'distance_threshold', 'rate_short', 'rate_long', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    list_filter = ('is_active',)
    ordering = ('order', 'weight_min')
    
    fieldsets = (
        ('Tier Information', {
            'fields': ('name', 'is_active', 'order'),
        }),
        ('Weight Range', {
            'fields': ('weight_min', 'weight_max'),
            'description': 'Define the weight range for this tier. Leave weight_max blank for "above X KG".'
        }),
        ('Distance-Based Pricing', {
            'fields': ('distance_threshold', 'price_per_km_short', 'price_per_km_long'),
            'description': 'Set different rates based on distance. If no threshold, same rate applies for all distances.'
        }),
    )
    
    def weight_range(self, obj):
        if obj.weight_max:
            return f"{obj.weight_min}-{obj.weight_max} KG"
        return f"{obj.weight_min}+ KG"
    weight_range.short_description = 'Weight Range'
    
    def rate_short(self, obj):
        if obj.distance_threshold:
            return f"${obj.price_per_km_short}/km (≤{obj.distance_threshold}km)"
        return f"${obj.price_per_km_short}/km"
    rate_short.short_description = 'Short Distance Rate'
    
    def rate_long(self, obj):
        if obj.price_per_km_long and obj.distance_threshold:
            return f"${obj.price_per_km_long}/km (>{obj.distance_threshold}km)"
        return "-"
    rate_long.short_description = 'Long Distance Rate'


@admin.register(DeliverySpeedOption)
class DeliverySpeedOptionAdmin(admin.ModelAdmin):
    """Admin interface for Delivery Speed Options"""
    
    list_display = ('name', 'code', 'adjustment_display', 'cutoff_time', 'requires_admin_approval', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    list_filter = ('is_active', 'requires_admin_approval', 'adjustment_type')
    ordering = ('order',)
    
    fieldsets = (
        ('Speed Option', {
            'fields': ('code', 'name', 'description', 'is_active', 'order'),
        }),
        ('Pricing Adjustment', {
            'fields': ('adjustment_type', 'adjustment_value'),
            'description': 'Define how this delivery speed affects pricing.'
        }),
        ('Requirements', {
            'fields': ('requires_admin_approval', 'cutoff_time'),
            'description': 'Set approval requirements and time restrictions.'
        }),
    )
    
    def adjustment_display(self, obj):
        if obj.adjustment_type == 'PER_KM':
            return f"+${obj.adjustment_value}/km"
        elif obj.adjustment_type == 'PERCENTAGE':
            return f"+{obj.adjustment_value}%"
        elif obj.adjustment_type == 'FIXED':
            return f"+${obj.adjustment_value}"
        return "-"
    adjustment_display.short_description = 'Price Adjustment'


@admin.register(OrderConcern)
class OrderConcernAdmin(admin.ModelAdmin):
    """Admin interface for Order Concerns"""
    
    list_display = ('id', 'order', 'customer_name', 'concern_type', 'status', 'created_at')
    list_filter = ('status', 'concern_type', 'created_at')
    search_fields = ('order__order_id', 'customer__email', 'subject', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Concern Information', {
            'fields': ('order', 'customer', 'concern_type', 'subject', 'description', 'concern_image')
        }),
        ('Status & Response', {
            'fields': ('status', 'admin_response', 'resolved_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def customer_name(self, obj):
        return obj.customer.get_full_name()
    customer_name.short_description = 'Customer'


@admin.register(DeliveryType)
class DeliveryTypeAdmin(admin.ModelAdmin):
    """Admin interface for Delivery Types (Express, Same Day, Overnight)"""
    
    list_display = ('name', 'code', 'base_price', 'max_coverage_km', 'requires_admin_approval', 'is_active', 'display_order')
    list_editable = ('is_active', 'display_order')
    list_filter = ('is_active', 'requires_admin_approval')
    ordering = ('display_order',)
    
    fieldsets = (
        ('Delivery Type', {
            'fields': ('code', 'name', 'description', 'is_active', 'display_order'),
        }),
        ('Pricing', {
            'fields': ('base_price', 'max_coverage_km'),
            'description': 'Base price applies to all pricing rules under this type.'
        }),
        ('Requirements', {
            'fields': ('requires_admin_approval',),
        }),
    )


@admin.register(PricingRule)
class PricingRuleAdmin(admin.ModelAdmin):
    """Admin interface for Pricing Rules"""
    
    list_display = ('name', 'delivery_type', 'weight_category', 'distance_condition', 'calculation_display', 'is_oversize_rule', 'is_active', 'priority')
    list_editable = ('is_active', 'priority')
    list_filter = ('delivery_type', 'weight_category', 'calculation_type', 'is_oversize_rule', 'is_active')
    ordering = ('delivery_type', 'priority')
    
    fieldsets = (
        ('Rule Information', {
            'fields': ('delivery_type', 'name', 'is_active', 'priority'),
            'description': 'Lower priority number = higher precedence when matching.'
        }),
        ('Weight Conditions', {
            'fields': ('weight_category', 'weight_min', 'weight_max'),
        }),
        ('Size Conditions', {
            'fields': ('is_oversize_rule',),
            'description': 'Check this for rules that apply to items too large for a standard car.'
        }),
        ('Distance Conditions', {
            'fields': ('distance_threshold', 'is_short_trip'),
            'description': 'Leave is_short_trip empty for "any distance" rules.'
        }),
        ('Calculation', {
            'fields': ('calculation_type', 'rate_per_km', 'max_price', 'flat_total', 'oversize_surcharge'),
            'description': '''
            PER_KM: base_price + rate_per_km × distance
            CAPPED: min(base_price + rate×km, max_price)
            FLAT: Just the flat_total amount
            '''
        }),
    )
    
    def distance_condition(self, obj):
        if obj.is_short_trip is None:
            return "Any distance"
        elif obj.is_short_trip:
            return f"≤{obj.distance_threshold}km"
        else:
            return f">{obj.distance_threshold}km"
    distance_condition.short_description = 'Distance'
    
    def calculation_display(self, obj):
        if obj.calculation_type == 'FLAT':
            return f"Flat ${obj.flat_total}"
        elif obj.calculation_type == 'CAPPED':
            return f"${obj.rate_per_km}/km (max ${obj.max_price})"
        else:
            return f"${obj.rate_per_km}/km"
    calculation_display.short_description = 'Calculation'

