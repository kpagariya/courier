"""
Tests for orders app
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from orders.models import Order

User = get_user_model()


class OrderModelTests(TestCase):
    """Test cases for Order model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )
    
    def test_create_order(self):
        """Test creating an order"""
        order = Order.objects.create(
            customer=self.user,
            pickup_address='123 Test St, Auckland',
            delivery_address='456 Main St, Wellington',
            parcel_weight=5.0,
            quantity=1,
            length=30,
            width=20,
            height=10
        )
        self.assertIsNotNone(order.order_id)
        self.assertEqual(order.customer, self.user)
        self.assertEqual(order.status, 'UNDER_REVIEW')
    
    def test_order_id_generation(self):
        """Test that order ID is automatically generated"""
        order = Order.objects.create(
            customer=self.user,
            pickup_address='123 Test St',
            delivery_address='456 Main St',
            parcel_weight=5.0,
            quantity=1,
            length=30,
            width=20,
            height=10
        )
        self.assertTrue(order.order_id.startswith('ORD-'))


class OrderViewTests(TestCase):
    """Test cases for order views"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )
        self.client.login(username='test@example.com', password='testpass123')
    
    def test_dashboard_requires_login(self):
        """Test that dashboard requires authentication"""
        self.client.logout()
        response = self.client.get(reverse('orders:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_dashboard_loads_for_authenticated_user(self):
        """Test that dashboard loads for authenticated user"""
        response = self.client.get(reverse('orders:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/dashboard.html')

