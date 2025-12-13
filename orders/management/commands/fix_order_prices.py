"""
Management command to recalculate auto_calculated_amount for orders
Usage: python manage.py fix_order_prices
"""
from django.core.management.base import BaseCommand
from orders.models import Order


class Command(BaseCommand):
    help = 'Recalculate auto_calculated_amount for all orders missing it'

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("FIXING ORDER PRICES"))
        self.stdout.write("=" * 60)
        
        # Get all orders where auto_calculated_amount is None but distance exists
        orders = Order.objects.filter(auto_calculated_amount__isnull=True, distance_km__isnull=False)
        
        self.stdout.write(f"\nFound {orders.count()} orders with missing auto_calculated_amount\n")
        
        fixed_count = 0
        failed_count = 0
        
        for order in orders:
            try:
                self.stdout.write(f"Processing {order.order_id}...")
                self.stdout.write(f"  Distance: {order.distance_km} km")
                self.stdout.write(f"  Weight: {order.parcel_weight} kg")
                
                # Calculate auto price
                auto_price = order.calculate_auto_price()
                
                if auto_price:
                    order.auto_calculated_amount = auto_price
                    order.save(update_fields=['auto_calculated_amount'])
                    self.stdout.write(self.style.SUCCESS(f"  [OK] Fixed! Auto price: ${auto_price}"))
                    fixed_count += 1
                else:
                    self.stdout.write(self.style.ERROR(f"  [ERROR] Calculation returned None"))
                    failed_count += 1
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  [ERROR] Error: {e}"))
                failed_count += 1
            
            self.stdout.write("")
        
        self.stdout.write("=" * 60)
        self.stdout.write(f"SUMMARY:")
        self.stdout.write(self.style.SUCCESS(f"  [OK] Fixed: {fixed_count} orders"))
        if failed_count > 0:
            self.stdout.write(self.style.ERROR(f"  [ERROR] Failed: {failed_count} orders"))
        self.stdout.write("=" * 60)

