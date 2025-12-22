"""
Order and delivery models
"""
from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class Order(models.Model):
    """Model for courier orders"""
    
    STATUS_CHOICES = [
        ('UNDER_REVIEW', 'Under Review'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('PICKED', 'Picked'),
        ('ON_THE_WAY', 'On the Way'),
        ('DELIVERED', 'Delivered'),
    ]
    
    PARCEL_TYPE_CHOICES = [
        ('GENERAL', 'General Items'),
        ('FRAGILE', 'Fragile/Glass'),
        ('ELECTRONICS', 'Electronics'),
        ('DOCUMENTS', 'Documents'),
        ('FOOD', 'Food Items'),
        ('GIFT', 'Gift Items'),
        ('FOAM', 'Foam/Soft Items'),
        ('CLOTHING', 'Clothing'),
        ('BOOKS', 'Books/Media'),
        ('OTHER', 'Other'),
    ]
    
    # Order identification
    order_id = models.CharField(max_length=20, unique=True, editable=False)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    
    # Parcel details
    parcel_type = models.CharField(max_length=20, choices=PARCEL_TYPE_CHOICES, default='GENERAL', help_text='Type of parcel')
    delivery_speed = models.CharField(max_length=20, default='SAME_DAY', help_text='Delivery speed option')
    pickup_address = models.TextField(help_text='Full pickup address')
    pickup_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    pickup_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    delivery_address = models.TextField(help_text='Full delivery address')
    delivery_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    delivery_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    distance_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Distance in kilometers')
    parcel_weight = models.DecimalField(max_digits=10, decimal_places=2, help_text='Weight in kg')
    quantity = models.PositiveIntegerField(default=1, help_text='Number of parcels')
    parcel_image = models.ImageField(upload_to='parcels/%Y/%m/', help_text='Photo of the parcel (Required)')
    is_oversize = models.BooleanField(default=False, help_text='Item is too large for a standard car (e.g., >1m length, bulky)')
    
    # Additional information
    description = models.TextField(blank=True, help_text='Additional notes or description')
    
    # Status and pricing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UNDER_REVIEW')
    courier_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    auto_calculated_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Auto-calculated based on distance')
    customer_proposed_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Customer\'s counter-offer or preferred price')
    
    # Delivery proof
    delivery_proof_image = models.ImageField(upload_to='delivery_proof/%Y/%m/', null=True, blank=True, help_text='Photo taken at delivery (Admin only)')
    
    # Payment status
    is_paid = models.BooleanField(default=False)
    
    # Admin notes
    admin_notes = models.TextField(blank=True, help_text='Internal notes for admin')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    picked_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
    
    def __str__(self):
        return f"Order {self.order_id} - {self.customer.get_full_name()}"
    
    def save(self, *args, **kwargs):
        """Generate unique order ID on creation"""
        if not self.order_id:
            # Generate order ID like ORD-20251128-1, ORD-20251128-2, etc.
            from django.db import transaction
            
            date_str = timezone.now().strftime('%Y%m%d')
            
            # Use transaction to prevent race conditions
            with transaction.atomic():
                # Get today's date range
                today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = today_start + timezone.timedelta(days=1)
                
                # Find all orders for today with our prefix
                today_orders = Order.objects.filter(
                    created_at__gte=today_start,
                    created_at__lt=today_end,
                    order_id__startswith=f"ORD-{date_str}-"
                ).values_list('order_id', flat=True)
                
                if today_orders:
                    # Extract all numbers and find the maximum
                    order_numbers = []
                    for oid in today_orders:
                        try:
                            num = int(oid.split('-')[-1])
                            order_numbers.append(num)
                        except (ValueError, IndexError):
                            pass
                    
                    if order_numbers:
                        next_number = max(order_numbers) + 1
                    else:
                        next_number = 1
                else:
                    # First order of the day
                    next_number = 1
                
                self.order_id = f"ORD-{date_str}-{next_number}"
        
        super().save(*args, **kwargs)
    
    def get_status_display_class(self):
        """Return Bootstrap class for status badge"""
        status_classes = {
            'UNDER_REVIEW': 'warning',
            'ACCEPTED': 'info',
            'REJECTED': 'danger',
            'PICKED': 'primary',
            'ON_THE_WAY': 'purple',  # Custom purple color
            'DELIVERED': 'success',
        }
        return status_classes.get(self.status, 'secondary')
    
    def can_be_paid(self):
        """Check if order can be paid"""
        return (self.status == 'ACCEPTED' and 
                self.courier_amount and 
                not self.is_paid)
    
    
    def calculate_auto_price(self):
        """
        Calculate price based on new Helpii pricing rules:
        - EXPRESS_2HR: $30 base + $5/km (+$50 oversize surcharge)
        - SAME_DAY: Complex weight/distance rules with caps
        - OVERNIGHT: Flat rates based on weight
        """
        if not self.distance_km or not self.parcel_weight:
            print("DEBUG: No distance or weight available for price calculation")
            return None
        
        try:
            distance = float(self.distance_km)
            weight = float(self.parcel_weight)
            is_oversize = getattr(self, 'is_oversize', False)
            delivery_speed = self.delivery_speed or 'SAME_DAY'
            
            print(f"DEBUG: Calculating price - Distance: {distance}km, Weight: {weight}kg, Oversize: {is_oversize}, Speed: {delivery_speed}")
            
            # Try new pricing rules first
            delivery_type = DeliveryType.objects.filter(
                code=delivery_speed,
                is_active=True
            ).first()
            
            if delivery_type:
                # Find matching pricing rule
                rules = PricingRule.objects.filter(
                    delivery_type=delivery_type,
                    is_active=True
                ).order_by('priority')
                
                for rule in rules:
                    if rule.matches(weight, distance, is_oversize):
                        price = rule.calculate_price(distance, weight, is_oversize)
                        print(f"DEBUG: Matched rule '{rule.name}' -> ${price}")
                        return price
                
                print(f"DEBUG: No matching rule found for {delivery_speed}")
            
            # Fallback to legacy tier system
            tier = PricingTier.objects.filter(
                is_active=True,
                weight_min__lte=weight
            ).filter(
                Q(weight_max__gte=weight) | Q(weight_max__isnull=True)
            ).first()
            
            if tier:
                rate_per_km = tier.get_rate_for_distance(distance)
                base_cost = distance * float(rate_per_km)
                print(f"DEBUG: Using legacy tier: {tier.name}, Rate: ${rate_per_km}/km, Cost: ${base_cost}")
                return round(base_cost, 2)
            
            # Final fallback to legacy pricing
            return self._calculate_legacy_price()
            
        except Exception as e:
            print(f"DEBUG: Exception in calculate_auto_price: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _calculate_legacy_price(self):
        """Legacy pricing calculation (fallback)"""
        try:
            config = PricingConfiguration.objects.first()
            if not config:
                return None
            
            base_price = float(config.base_price)
            distance_cost = float(self.distance_km) * float(config.price_per_km)
            weight_cost = float(self.parcel_weight) * float(config.price_per_kg)
            
            type_multipliers = {
                'FRAGILE': 1.5, 'ELECTRONICS': 1.3, 'GENERAL': 1.0,
                'DOCUMENTS': 0.8, 'FOOD': 1.2, 'GIFT': 1.1,
                'FOAM': 1.0, 'CLOTHING': 0.9, 'BOOKS': 0.9, 'OTHER': 1.0,
            }
            
            multiplier = type_multipliers.get(self.parcel_type, 1.0)
            total = (base_price + distance_cost + weight_cost) * multiplier
            
            print(f"DEBUG: Using legacy pricing: ${total}")
            return round(total, 2)
        except:
            return None


class PricingTier(models.Model):
    """Weight-based pricing tiers with distance conditions"""
    
    name = models.CharField(max_length=100, help_text='Tier name (e.g., "Light Package")')
    weight_min = models.DecimalField(max_digits=10, decimal_places=2, help_text='Minimum weight in KG (inclusive)')
    weight_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Maximum weight in KG (inclusive). Leave blank for no limit')
    
    # Distance conditions
    distance_threshold = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Distance threshold in KM (e.g., 10). Leave blank if no distance condition')
    price_per_km_short = models.DecimalField(max_digits=10, decimal_places=2, help_text='Price per KM for distances ≤ threshold')
    price_per_km_long = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Price per KM for distances > threshold. Leave blank if same as short distance')
    
    is_active = models.BooleanField(default=True, help_text='Enable/disable this tier')
    order = models.IntegerField(default=0, help_text='Display order')
    
    class Meta:
        db_table = 'pricing_tiers'
        ordering = ['order', 'weight_min']
        verbose_name = 'Pricing Tier'
        verbose_name_plural = 'Pricing Tiers'
    
    def __str__(self):
        if self.weight_max:
            return f"{self.name} ({self.weight_min}-{self.weight_max} KG)"
        return f"{self.name} ({self.weight_min}+ KG)"
    
    def get_rate_for_distance(self, distance_km):
        """Get the applicable rate based on distance"""
        if self.distance_threshold and distance_km > self.distance_threshold:
            return self.price_per_km_long if self.price_per_km_long else self.price_per_km_short
        return self.price_per_km_short


class DeliverySpeedOption(models.Model):
    """Delivery speed options with pricing adjustments"""
    
    SPEED_CHOICES = [
        ('SAME_DAY', 'Same Day Delivery (8AM-6PM)'),
        ('OVERNIGHT', 'Overnight Delivery'),
        ('EXPRESS_90MIN', '90 Minutes Express'),
    ]
    
    code = models.CharField(max_length=20, choices=SPEED_CHOICES, unique=True, help_text='Delivery speed code')
    name = models.CharField(max_length=100, help_text='Display name')
    description = models.TextField(blank=True, help_text='Description for customers')
    
    # Pricing
    adjustment_type = models.CharField(
        max_length=20,
        choices=[
            ('PER_KM', 'Per Kilometer'),
            ('PERCENTAGE', 'Percentage'),
            ('FIXED', 'Fixed Amount'),
        ],
        default='PER_KM',
        help_text='How to adjust the price'
    )
    adjustment_value = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Adjustment value (e.g., 1 for $1/km, 10 for 10%, or fixed $50)')
    
    requires_admin_approval = models.BooleanField(default=False, help_text='Require admin approval for this speed')
    cutoff_time = models.TimeField(null=True, blank=True, help_text='Order cutoff time (e.g., 1:00 PM for same-day)')
    
    is_active = models.BooleanField(default=True, help_text='Enable/disable this option')
    order = models.IntegerField(default=0, help_text='Display order')
    
    class Meta:
        db_table = 'delivery_speed_options'
        ordering = ['order']
        verbose_name = 'Delivery Speed Option'
        verbose_name_plural = 'Delivery Speed Options'
    
    def __str__(self):
        return self.name


class PricingConfiguration(models.Model):
    """General pricing configuration"""
    
    allow_customer_negotiation = models.BooleanField(default=True, help_text='Allow customers to propose their own price')
    show_distance_to_customer = models.BooleanField(default=False, help_text='Show calculated distance (KM) to customers on order form')
    
    # Legacy fields (kept for backward compatibility)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=10.00, help_text='LEGACY: Base price (use Pricing Tiers instead)')
    price_per_km = models.DecimalField(max_digits=10, decimal_places=2, default=1.50, help_text='LEGACY: Price per KM (use Pricing Tiers instead)')
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=2.00, help_text='LEGACY: Price per KG (use Pricing Tiers instead)')
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pricing_configuration'
        verbose_name = 'Pricing Configuration'
        verbose_name_plural = 'Pricing Configuration'
    
    def __str__(self):
        return "Pricing Configuration"


class DeliveryType(models.Model):
    """
    Helpii Delivery Types:
    - EXPRESS_2HR: 2 Hour Urgent Delivery
    - SAME_DAY: Same Day Delivery  
    - OVERNIGHT: Overnight Delivery
    """
    
    CODE_CHOICES = [
        ('EXPRESS_2HR', 'Helpii Express (2 Hour Urgent)'),
        ('SAME_DAY', 'Helpii Same Day'),
        ('OVERNIGHT', 'Helpii Overnight'),
    ]
    
    code = models.CharField(max_length=20, choices=CODE_CHOICES, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=10.00, help_text='Base price for this delivery type')
    
    # Coverage
    max_coverage_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Maximum coverage in KM (e.g., 30 for Auckland metro)')
    
    requires_admin_approval = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'delivery_types'
        ordering = ['display_order']
        verbose_name = 'Delivery Type'
        verbose_name_plural = 'Delivery Types'
    
    def __str__(self):
        return self.name


class PricingRule(models.Model):
    """
    Comprehensive pricing rules for each delivery type.
    Supports: Rate per KM, Capped pricing, and Flat pricing.
    """
    
    WEIGHT_CATEGORY_CHOICES = [
        ('SMALL', 'Small (≤10 kg)'),
        ('MEDIUM', 'Medium (11-20 kg)'),
        ('HEAVY', 'Heavy (>20 kg)'),
        ('ANY', 'Any Weight'),
    ]
    
    CALCULATION_TYPE_CHOICES = [
        ('PER_KM', 'Rate per KM (base + rate×km)'),
        ('CAPPED', 'Capped Total (base + rate×km, max cap)'),
        ('FLAT', 'Flat Total Price'),
    ]
    
    delivery_type = models.ForeignKey(DeliveryType, on_delete=models.CASCADE, related_name='pricing_rules')
    name = models.CharField(max_length=100, help_text='Rule name for admin (e.g., "Same Day Small Short Trip")')
    
    # Weight conditions
    weight_category = models.CharField(max_length=20, choices=WEIGHT_CATEGORY_CHOICES, default='ANY')
    weight_min = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Minimum weight in KG')
    weight_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Maximum weight in KG (leave blank for no limit)')
    
    # Oversize condition
    is_oversize_rule = models.BooleanField(default=False, help_text='This rule applies to oversize items only')
    
    # Distance conditions
    distance_threshold = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='KM threshold for short/long trips (e.g., 10)')
    is_short_trip = models.BooleanField(null=True, blank=True, help_text='True=short trip (≤threshold), False=long trip (>threshold), None=any distance')
    
    # Calculation
    calculation_type = models.CharField(max_length=20, choices=CALCULATION_TYPE_CHOICES, default='PER_KM')
    
    # For PER_KM type: base_price + rate_per_km × distance
    rate_per_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Rate per KM (for PER_KM type)')
    
    # For CAPPED type: min(base_price + rate×km, max_price)
    max_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Maximum capped price (for CAPPED type)')
    
    # For FLAT type: Just return this amount
    flat_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Flat total price (for FLAT type)')
    
    # Extra surcharge for oversize/overweight on EXPRESS
    oversize_surcharge = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Additional surcharge for oversize items')
    
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0, help_text='Lower number = higher priority for matching')
    
    class Meta:
        db_table = 'pricing_rules'
        ordering = ['delivery_type', 'priority', 'weight_min']
        verbose_name = 'Pricing Rule'
        verbose_name_plural = 'Pricing Rules'
    
    def __str__(self):
        return f"{self.delivery_type.code} - {self.name}"
    
    def calculate_price(self, distance_km, weight_kg, is_oversize=False):
        """Calculate price based on this rule"""
        base = float(self.delivery_type.base_price)
        
        if self.calculation_type == 'FLAT':
            total = float(self.flat_total) if self.flat_total else base
        elif self.calculation_type == 'CAPPED':
            rate = float(self.rate_per_km) if self.rate_per_km else 0
            calculated = base + (rate * float(distance_km))
            max_cap = float(self.max_price) if self.max_price else calculated
            total = min(calculated, max_cap)
        else:  # PER_KM
            rate = float(self.rate_per_km) if self.rate_per_km else 0
            total = base + (rate * float(distance_km))
        
        # Add oversize surcharge if applicable
        if is_oversize and self.oversize_surcharge:
            total += float(self.oversize_surcharge)
        
        return round(total, 2)
    
    def matches(self, weight_kg, distance_km, is_oversize=False):
        """Check if this rule matches the given conditions"""
        weight = float(weight_kg)
        distance = float(distance_km)
        
        # Check oversize condition
        if self.is_oversize_rule and not is_oversize:
            return False
        if not self.is_oversize_rule and is_oversize:
            # Non-oversize rules don't match oversize items (unless it's EXPRESS which handles it with surcharge)
            if self.delivery_type.code != 'EXPRESS_2HR':
                return False
        
        # Check weight
        if weight < float(self.weight_min):
            return False
        if self.weight_max and weight > float(self.weight_max):
            return False
        
        # Check distance threshold
        if self.is_short_trip is not None and self.distance_threshold:
            threshold = float(self.distance_threshold)
            if self.is_short_trip and distance > threshold:
                return False
            if not self.is_short_trip and distance <= threshold:
                return False
        
        return True


class OrderConcern(models.Model):
    """Model for customer concerns about delivered orders"""
    
    CONCERN_TYPE_CHOICES = [
        ('DAMAGED', 'Parcel Damaged'),
        ('MISSING_ITEMS', 'Missing Items'),
        ('WRONG_DELIVERY', 'Wrong Delivery Address'),
        ('DELAY', 'Excessive Delay'),
        ('OTHER', 'Other Issue'),
    ]
    
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='concerns')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='concerns')
    
    concern_type = models.CharField(max_length=20, choices=CONCERN_TYPE_CHOICES)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    concern_image = models.ImageField(upload_to='concerns/%Y/%m/', null=True, blank=True, help_text='Photo of the issue')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    admin_response = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'order_concerns'
        ordering = ['-created_at']
        verbose_name = 'Order Concern'
        verbose_name_plural = 'Order Concerns'
    
    def __str__(self):
        return f"Concern #{self.id} - {self.order.order_id} - {self.get_concern_type_display()}"


class UserDelivery(models.Model):
    """Many-to-many relationship between users and deliveries"""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='deliveries')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deliveries')
    
    # Delivery tracking
    assigned_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'user_deliveries'
        unique_together = [['order', 'customer']]
        verbose_name = 'User Delivery'
        verbose_name_plural = 'User Deliveries'
    
    def __str__(self):
        return f"{self.order.order_id} - {self.customer.get_full_name()}"

