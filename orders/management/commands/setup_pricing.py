"""
Management command to setup pricing tiers and delivery speed options
"""
from django.core.management.base import BaseCommand
from orders.models import PricingTier, DeliverySpeedOption
from datetime import time


class Command(BaseCommand):
    help = 'Setup initial pricing tiers and delivery speed options'

    def handle(self, *args, **kwargs):
        self.stdout.write("=" * 60)
        self.stdout.write("SETTING UP PRICING TIERS AND DELIVERY SPEED OPTIONS")
        self.stdout.write("=" * 60)

        # Clear existing data
        self.stdout.write("\nClearing existing pricing tiers...")
        PricingTier.objects.all().delete()

        self.stdout.write("Clearing existing delivery speed options...")
        DeliverySpeedOption.objects.all().delete()

        # Create Pricing Tiers
        self.stdout.write("\nCreating pricing tiers...")

        # Tier 1: 1-10 KG
        tier1 = PricingTier.objects.create(
            name="Light Package (1-10 KG)",
            weight_min=1,
            weight_max=10,
            distance_threshold=10,
            price_per_km_short=5.00,  # $5/km for ≤10km
            price_per_km_long=3.00,   # $3/km for >10km
            is_active=True,
            order=1
        )
        self.stdout.write(self.style.SUCCESS(f"[OK] Created: {tier1}"))

        # Tier 2: 10-20 KG
        tier2 = PricingTier.objects.create(
            name="Medium Package (10-20 KG)",
            weight_min=10.01,
            weight_max=20,
            distance_threshold=10,
            price_per_km_short=9.00,  # $9/km for ≤10km
            price_per_km_long=7.00,   # $7/km for >10km
            is_active=True,
            order=2
        )
        self.stdout.write(self.style.SUCCESS(f"[OK] Created: {tier2}"))

        # Tier 3: Above 20 KG
        tier3 = PricingTier.objects.create(
            name="Heavy Package (Above 20 KG)",
            weight_min=20.01,
            weight_max=None,
            distance_threshold=None,
            price_per_km_short=10.00,  # $10/km for all distances
            price_per_km_long=None,
            is_active=True,
            order=3
        )
        self.stdout.write(self.style.SUCCESS(f"[OK] Created: {tier3}"))

        # Create Delivery Speed Options
        self.stdout.write("\nCreating delivery speed options...")

        # Option 1: Same Day Delivery
        same_day = DeliverySpeedOption.objects.create(
            code='SAME_DAY',
            name='Same Day Delivery (8AM-6PM)',
            description='Regular delivery if ordered before 1:00 PM',
            adjustment_type='PER_KM',
            adjustment_value=0.00,
            requires_admin_approval=False,
            cutoff_time=time(13, 0),
            is_active=True,
            order=1
        )
        self.stdout.write(self.style.SUCCESS(f"[OK] Created: {same_day}"))

        # Option 2: Overnight Delivery
        overnight = DeliverySpeedOption.objects.create(
            code='OVERNIGHT',
            name='Overnight Delivery',
            description='Delivery by next morning. Additional $1 per kilometer.',
            adjustment_type='PER_KM',
            adjustment_value=1.00,
            requires_admin_approval=False,
            cutoff_time=None,
            is_active=True,
            order=2
        )
        self.stdout.write(self.style.SUCCESS(f"[OK] Created: {overnight}"))

        # Option 3: 90 Minutes Express
        express_90 = DeliverySpeedOption.objects.create(
            code='EXPRESS_90MIN',
            name='90 Minutes Express',
            description='Ultra-fast delivery within 90 minutes. Requires admin approval.',
            adjustment_type='PER_KM',
            adjustment_value=0.00,
            requires_admin_approval=True,
            cutoff_time=None,
            is_active=True,
            order=3
        )
        self.stdout.write(self.style.SUCCESS(f"[OK] Created: {express_90}"))

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("SETUP COMPLETE!"))
        self.stdout.write("=" * 60)

        self.stdout.write("\nPricing Tiers Created:")
        self.stdout.write("1. Light Package (1-10 KG):")
        self.stdout.write("   - ≤10 km: $5/km")
        self.stdout.write("   - >10 km: $3/km")
        self.stdout.write("\n2. Medium Package (10-20 KG):")
        self.stdout.write("   - ≤10 km: $9/km")
        self.stdout.write("   - >10 km: $7/km")
        self.stdout.write("\n3. Heavy Package (Above 20 KG):")
        self.stdout.write("   - All distances: $10/km")

        self.stdout.write("\nDelivery Speed Options:")
        self.stdout.write("1. Same Day (8AM-6PM): Regular price (cutoff 1PM)")
        self.stdout.write("2. Overnight: +$1 per kilometer")
        self.stdout.write("3. 90 Minutes Express: Admin approval required")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("You can now manage these in the admin panel:")
        self.stdout.write("- Pricing Tiers: /admin/orders/pricingtier/")
        self.stdout.write("- Delivery Speeds: /admin/orders/deliveryspeedoption/")
        self.stdout.write("=" * 60)

