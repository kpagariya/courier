"""
Tests for core app
"""
from django.test import TestCase, Client
from django.urls import reverse


class CoreViewTests(TestCase):
    """Test cases for core views"""
    
    def setUp(self):
        self.client = Client()
    
    def test_home_page_loads(self):
        """Test that home page loads successfully"""
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/home.html')
    
    def test_services_page_loads(self):
        """Test that services page loads successfully"""
        response = self.client.get(reverse('core:services'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/services.html')
    
    def test_contact_page_loads(self):
        """Test that contact page loads successfully"""
        response = self.client.get(reverse('core:contact'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/contact.html')
    
    def test_terms_page_loads(self):
        """Test that terms page loads successfully"""
        response = self.client.get(reverse('core:terms'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/terms.html')

