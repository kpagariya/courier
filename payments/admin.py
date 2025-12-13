"""
Admin configuration for payments app
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin interface for Payment model"""
    
    list_display = (
        'transaction_id', 'order', 'customer_name', 'amount',
        'payment_method', 'status_badge', 'created_at'
    )
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = (
        'transaction_id', 'order__order_id', 'customer__email',
        'stripe_payment_intent_id', 'paypal_order_id'
    )
    readonly_fields = ('transaction_id', 'created_at', 'updated_at', 'completed_at')
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('transaction_id', 'order', 'customer', 'status')
        }),
        ('Amount Details', {
            'fields': ('amount', 'currency', 'payment_method')
        }),
        ('Gateway Information', {
            'fields': ('stripe_payment_intent_id', 'paypal_order_id')
        }),
        ('Additional Information', {
            'fields': ('description', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
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
            'PENDING': '#ffc107',
            'PROCESSING': '#17a2b8',
            'COMPLETED': '#28a745',
            'FAILED': '#dc3545',
            'REFUNDED': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

