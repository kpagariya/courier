"""
Tests for payments app
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from orders.models import Order
from payments.models import Payment

User = get_user_model()


class PaymentModelTests(TestCase):
    """Test cases for Payment model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )
        self.order = Order.objects.create(
            customer=self.user,
            pickup_address='123 Test St',
            delivery_address='456 Main St',
            parcel_weight=5.0,
            quantity=1,
            length=30,
            width=20,
            height=10,
            courier_amount=50.00,
            status='ACCEPTED'
        )
    
    def test_create_payment(self):
        """Test creating a payment"""
        payment = Payment.objects.create(
            transaction_id='TXN-TEST123',
            order=self.order,
            customer=self.user,
            amount=50.00,
            currency='NZD',
            payment_method='STRIPE',
            status='PENDING'
        )
        self.assertEqual(payment.amount, 50.00)
        self.assertEqual(payment.order, self.order)
        self.assertEqual(payment.status, 'PENDING')

