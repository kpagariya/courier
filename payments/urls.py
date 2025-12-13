"""
URL patterns for payments app
"""
from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('method/<str:order_id>/', views.payment_method_view, name='payment_method'),
    path('history/', views.payment_history_view, name='payment_history'),
    
    # Stripe URLs
    path('stripe/pay/<str:order_id>/', views.stripe_payment_view, name='stripe_payment'),
    path('stripe/success/<str:order_id>/', views.stripe_payment_success, name='stripe_success'),
    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
    
    # PayPal URLs
    path('paypal/pay/<str:order_id>/', views.paypal_payment_view, name='paypal_payment'),
    path('paypal/execute/<str:order_id>/', views.paypal_execute_view, name='paypal_execute'),
]

