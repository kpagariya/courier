"""
Management command to set up Helpii pricing rules.

SIMPLIFIED PRICING STRUCTURE:
=============================

1. Same-Day Delivery (Auckland only):
   - Standard: $10 base + weight-based rates (km doesn't apply)
   - Overweight (>20kg): $10 + $100 flat = $110

2. 2-Hour Urgent Delivery:
   - $30 base + $5/km
   - Overweight surcharge: +$50

3. Overnight Delivery:
   - $10 base + $50 flat = $60 (km doesn't apply)

Usage:
    python manage.py setup_helpii_pricing
"""
from django.core.management.base import BaseCommand
from orders.models import DeliveryType, PricingRule


class Command(BaseCommand):
    help = 'Set up Helpii pricing rules for all delivery types'

    def handle(self, *args, **options):
        self.stdout.write('Setting up Helpii pricing rules...\n')
        
        # Clear existing rules for clean setup
        self.stdout.write('Clearing existing pricing rules...')
        PricingRule.objects.all().delete()
        
        # ============================================
        # 1. EXPRESS 2HR DELIVERY
        # $30 base + $5/km, +$50 overweight
        # ============================================
        express, created = DeliveryType.objects.update_or_create(
            code='EXPRESS_2HR',
            defaults={
                'name': 'Helpii Express (2 Hour Urgent)',
                'description': 'Guaranteed delivery within 2 hours. $30 base + $5/km. Conditions apply - traffic/weather delays may extend delivery time.',
                'base_price': 30.00,
                'max_coverage_km': 30.00,
                'requires_admin_approval': False,
                'is_active': True,
                'display_order': 1,
            }
        )
        self.stdout.write(f'  {"Created" if created else "Updated"} DeliveryType: {express.name}')
        
        # Express: Standard weight - $30 + $5/km
        PricingRule.objects.create(
            delivery_type=express,
            name='Express Standard',
            weight_category='ANY',
            weight_min=0,
            weight_max=20,
            is_oversize_rule=False,
            distance_threshold=None,
            is_short_trip=None,
            calculation_type='PER_KM',
            rate_per_km=5.00,
            oversize_surcharge=0,
            is_active=True,
            priority=10,
        )
        self.stdout.write('    + Express Standard (<=20kg): $30 + $5/km')
        
        # Express: Overweight (>20kg) - $30 + $5/km + $50 surcharge
        PricingRule.objects.create(
            delivery_type=express,
            name='Express Overweight',
            weight_category='HEAVY',
            weight_min=20.01,
            weight_max=None,
            is_oversize_rule=False,
            distance_threshold=None,
            is_short_trip=None,
            calculation_type='PER_KM',
            rate_per_km=5.00,
            oversize_surcharge=50.00,
            is_active=True,
            priority=5,
        )
        self.stdout.write('    + Express Overweight (>20kg): $30 + $5/km + $50 surcharge')
        
        # ============================================
        # 2. SAME DAY DELIVERY (Auckland only)
        # Distance doesn't apply
        # ============================================
        same_day, created = DeliveryType.objects.update_or_create(
            code='SAME_DAY',
            defaults={
                'name': 'Helpii Same Day',
                'description': 'Same day delivery within Auckland. Distance does not apply.',
                'base_price': 10.00,
                'max_coverage_km': None,
                'requires_admin_approval': False,
                'is_active': True,
                'display_order': 2,
            }
        )
        self.stdout.write(f'  {"Created" if created else "Updated"} DeliveryType: {same_day.name}')
        
        # Same Day: Small parcels (<=10kg) - $10 + $20 flat = $30
        PricingRule.objects.create(
            delivery_type=same_day,
            name='Same Day Small',
            weight_category='SMALL',
            weight_min=0,
            weight_max=10,
            is_oversize_rule=False,
            distance_threshold=None,
            is_short_trip=None,
            calculation_type='FLAT',
            flat_total=30.00,
            is_active=True,
            priority=10,
        )
        self.stdout.write('    + Same Day Small (<=10kg): Flat $30')
        
        # Same Day: Medium parcels (11-20kg) - $10 + $30 flat = $40
        PricingRule.objects.create(
            delivery_type=same_day,
            name='Same Day Medium',
            weight_category='MEDIUM',
            weight_min=10.01,
            weight_max=20,
            is_oversize_rule=False,
            distance_threshold=None,
            is_short_trip=None,
            calculation_type='FLAT',
            flat_total=40.00,
            is_active=True,
            priority=20,
        )
        self.stdout.write('    + Same Day Medium (11-20kg): Flat $40')
        
        # Same Day: Overweight (>20kg) - $10 + $100 flat = $110
        PricingRule.objects.create(
            delivery_type=same_day,
            name='Same Day Overweight',
            weight_category='HEAVY',
            weight_min=20.01,
            weight_max=None,
            is_oversize_rule=False,
            distance_threshold=None,
            is_short_trip=None,
            calculation_type='FLAT',
            flat_total=110.00,
            is_active=True,
            priority=30,
        )
        self.stdout.write('    + Same Day Overweight (>20kg): $10 + $100 = Flat $110')
        
        # Same Day: Oversize (bulky items <=20kg) - Flat $70
        PricingRule.objects.create(
            delivery_type=same_day,
            name='Same Day Oversize',
            weight_category='ANY',
            weight_min=0,
            weight_max=20,
            is_oversize_rule=True,
            distance_threshold=None,
            is_short_trip=None,
            calculation_type='FLAT',
            flat_total=70.00,
            is_active=True,
            priority=5,
        )
        self.stdout.write('    + Same Day Oversize (bulky, <=20kg): Flat $70')
        
        # ============================================
        # 3. OVERNIGHT DELIVERY
        # $10 base + $50 flat = $60 total (km doesn't apply)
        # ============================================
        overnight, created = DeliveryType.objects.update_or_create(
            code='OVERNIGHT',
            defaults={
                'name': 'Helpii Overnight',
                'description': 'Overnight delivery - picked up today, delivered tomorrow. Flat rate, distance does not apply.',
                'base_price': 10.00,
                'max_coverage_km': None,
                'requires_admin_approval': False,
                'is_active': True,
                'display_order': 3,
            }
        )
        self.stdout.write(f'  {"Created" if created else "Updated"} DeliveryType: {overnight.name}')
        
        # Overnight: All weights - $10 + $50 = $60 flat
        PricingRule.objects.create(
            delivery_type=overnight,
            name='Overnight Standard',
            weight_category='ANY',
            weight_min=0,
            weight_max=None,
            is_oversize_rule=False,
            distance_threshold=None,
            is_short_trip=None,
            calculation_type='FLAT',
            flat_total=60.00,
            is_active=True,
            priority=10,
        )
        self.stdout.write('    + Overnight (any weight): $10 + $50 = Flat $60')
        
        # Overnight: Oversize - Flat $70
        PricingRule.objects.create(
            delivery_type=overnight,
            name='Overnight Oversize',
            weight_category='ANY',
            weight_min=0,
            weight_max=None,
            is_oversize_rule=True,
            distance_threshold=None,
            is_short_trip=None,
            calculation_type='FLAT',
            flat_total=70.00,
            is_active=True,
            priority=5,
        )
        self.stdout.write('    + Overnight Oversize (bulky): Flat $70')
        
        # Summary
        self.stdout.write('\n' + self.style.SUCCESS('Helpii pricing setup complete!'))
        self.stdout.write('\n' + '='*50)
        self.stdout.write('PRICING SUMMARY:')
        self.stdout.write('='*50)
        self.stdout.write('\n2-HOUR EXPRESS:')
        self.stdout.write('  - Standard: $30 + $5/km')
        self.stdout.write('  - Overweight (>20kg): $30 + $5/km + $50')
        self.stdout.write('\nSAME DAY (Auckland, km N/A):')
        self.stdout.write('  - Small (<=10kg): $30 flat')
        self.stdout.write('  - Medium (11-20kg): $40 flat')
        self.stdout.write('  - Overweight (>20kg): $110 flat')
        self.stdout.write('  - Oversize (bulky): $70 flat')
        self.stdout.write('\nOVERNIGHT (km N/A):')
        self.stdout.write('  - Any weight: $60 flat')
        self.stdout.write('  - Oversize: $70 flat')
        self.stdout.write('='*50 + '\n')
        
        self.stdout.write(f'\nTotal Pricing Rules: {PricingRule.objects.count()}')
