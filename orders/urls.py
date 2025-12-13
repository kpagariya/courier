"""
URL patterns for orders app
"""
from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Public URLs (no login required)
    path('track/', views.track_order_public_view, name='track_order'),
    
    # Customer URLs
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('create/', views.create_order_view, name='create_order'),
    path('my-orders/', views.order_list_view, name='order_list'),
    path('order/<str:order_id>/', views.order_detail_view, name='order_detail'),
    path('order/<str:order_id>/track/', views.track_order_view, name='track_order_detail'),
    path('order/<str:order_id>/reorder/', views.reorder_view, name='reorder'),
    
    # API Endpoints
    path('api/order/<str:order_id>/status/', views.check_order_status_api, name='check_order_status_api'),
    path('api/calculate-quote/', views.calculate_quote_api, name='calculate_quote_api'),
    
    # Test/Debug URLs
    path('test/auto-refresh/<str:order_id>/', views.test_auto_refresh_view, name='test_auto_refresh'),
    
    # Concern URLs
    path('order/<str:order_id>/raise-concern/', views.raise_concern_view, name='raise_concern'),
    path('concerns/', views.concern_list_view, name='concern_list'),
    path('concern/<int:concern_id>/', views.concern_detail_view, name='concern_detail'),
    
    # Admin URLs
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin/orders/', views.admin_order_list_view, name='admin_order_list'),
    path('admin/order/<str:order_id>/', views.admin_order_detail_view, name='admin_order_detail'),
    path('admin/concerns/', views.admin_concern_list_view, name='admin_concern_list'),
    path('admin/concern/<int:concern_id>/', views.admin_concern_detail_view, name='admin_concern_detail'),
]

