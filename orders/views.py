"""
Views for order management
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.http import JsonResponse
from datetime import timedelta
from .models import Order, UserDelivery, OrderConcern, PricingConfiguration, PricingTier, DeliverySpeedOption
from .forms import OrderForm, OrderConcernForm
from .utils import get_coordinates_google_maps, calculate_distance_google_maps


@login_required
def dashboard_view(request):
    """Customer dashboard view"""
    # Get customer's orders
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')[:5]
    
    # Statistics
    total_orders = Order.objects.filter(customer=request.user).count()
    pending_orders = Order.objects.filter(
        customer=request.user, 
        status__in=['UNDER_REVIEW', 'ACCEPTED', 'PICKED', 'ON_THE_WAY']
    ).count()
    delivered_orders = Order.objects.filter(
        customer=request.user, 
        status='DELIVERED'
    ).count()
    
    context = {
        'orders': orders,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'delivered_orders': delivered_orders,
    }
    
    return render(request, 'orders/dashboard.html', context)


@login_required
def create_order_view(request):
    """Create new order view"""
    if request.method == 'POST':
        form = OrderForm(request.POST, request.FILES)
        if form.is_valid():
            order = form.save(commit=False)
            order.customer = request.user
            
            # Check if coordinates were provided by autocomplete
            pickup_lat = request.POST.get('pickup_lat')
            pickup_lng = request.POST.get('pickup_lng')
            delivery_lat = request.POST.get('delivery_lat')
            delivery_lng = request.POST.get('delivery_lng')
            
            print(f"DEBUG: Coordinates from form - Pickup: ({pickup_lat}, {pickup_lng}), Delivery: ({delivery_lat}, {delivery_lng})")
            
            # If not provided, geocode the addresses
            if not (pickup_lat and pickup_lng):
                print(f"DEBUG: Geocoding pickup address: {order.pickup_address}")
                pickup_lat, pickup_lng = get_coordinates_google_maps(order.pickup_address)
                print(f"DEBUG: Geocoded pickup: ({pickup_lat}, {pickup_lng})")
            else:
                pickup_lat = float(pickup_lat)
                pickup_lng = float(pickup_lng)
            
            if not (delivery_lat and delivery_lng):
                print(f"DEBUG: Geocoding delivery address: {order.delivery_address}")
                delivery_lat, delivery_lng = get_coordinates_google_maps(order.delivery_address)
                print(f"DEBUG: Geocoded delivery: ({delivery_lat}, {delivery_lng})")
            else:
                delivery_lat = float(delivery_lat)
                delivery_lng = float(delivery_lng)
            
            # Capture is_oversize from POST (checkbox)
            is_oversize = request.POST.get('is_oversize') == 'on'
            order.is_oversize = is_oversize
            print(f"DEBUG: Is Oversize: {is_oversize}")
            
            if pickup_lat and delivery_lat:
                order.pickup_latitude = pickup_lat
                order.pickup_longitude = pickup_lng
                order.delivery_latitude = delivery_lat
                order.delivery_longitude = delivery_lng
                
                # Calculate distance using coordinates
                from orders.utils import calculate_distance
                distance = calculate_distance(pickup_lat, pickup_lng, delivery_lat, delivery_lng)
                print(f"DEBUG: Calculated distance: {distance} km")
                
                if distance:
                    order.distance_km = distance
                    
                    # Calculate auto price using new Helpii pricing
                    auto_price = order.calculate_auto_price()
                    print(f"DEBUG: Auto-calculated price: ${auto_price}")
                    
                    if auto_price:
                        order.auto_calculated_amount = auto_price
                    else:
                        print("DEBUG: Price calculation returned None - check PricingConfiguration")
                else:
                    print("DEBUG: Distance calculation failed")
            
            order.save()
            
            # Create UserDelivery entry
            UserDelivery.objects.create(order=order, customer=request.user)
            
            # Send email to admin
            try:
                send_new_order_email_to_admin(order)
            except Exception as e:
                print(f"Error sending admin email: {e}")
            
            # Send confirmation email to customer
            try:
                from orders.utils import send_order_confirmation_email
                send_order_confirmation_email(order)
            except Exception as e:
                print(f"Error sending customer confirmation email: {e}")
            
            # Success message with quote and/or customer proposed price
            success_msg = f'Order {order.order_id} has been successfully created! '
            
            if order.auto_calculated_amount:
                success_msg += f'Estimated quote: NZD ${order.auto_calculated_amount:.2f}. '
            
            if order.customer_proposed_price:
                success_msg += f'Your proposed price: NZD ${order.customer_proposed_price:.2f}. '
            
            if order.customer_proposed_price and order.auto_calculated_amount:
                success_msg += 'Our team will review both prices. '
            elif not order.auto_calculated_amount:
                success_msg += 'Our team will calculate the quote and notify you shortly. '
            else:
                success_msg += 'Our team will review it shortly. '
            
            messages.success(request, success_msg)
            return redirect('orders:order_detail', order_id=order.order_id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = OrderForm()
    
    # Get pricing configuration for display
    pricing_config = PricingConfiguration.objects.first()
    
    # Warn if pricing not configured
    if not pricing_config and request.user.is_staff:
        messages.warning(
            request,
            'Pricing Configuration not set! Please add it in Admin Panel → Pricing Configuration.'
        )
    
    return render(request, 'orders/create_order.html', {
        'form': form,
        'pricing_config': pricing_config,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY
    })


def send_new_order_email_to_admin(order):
    """Send email notification to admin for new orders"""
    subject = f'New Courier Order - {order.order_id}'
    
    html_message = render_to_string('orders/email/new_order_admin.html', {
        'order': order,
    })
    
    plain_message = f"""
    New Courier Order Received
    
    Order ID: {order.order_id}
    Customer: {order.customer.get_full_name()}
    Email: {order.customer.email}
    Contact: {order.customer.contact}
    
    Parcel Type: {order.get_parcel_type_display()}
    Pickup: {order.pickup_address}
    Delivery: {order.delivery_address}
    Weight: {order.parcel_weight} kg
    Distance: {order.distance_km} km
    
    Estimated Price: NZD ${order.auto_calculated_amount}
    
    Please review and accept/reject this order in the admin panel.
    """
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@courierpro.co.nz',
        recipient_list=[settings.ADMIN_EMAIL],
        html_message=html_message,
        fail_silently=True,
    )


@login_required
def order_detail_view(request, order_id):
    """Order detail view"""
    order = get_object_or_404(Order, order_id=order_id, customer=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})


@login_required
def order_list_view(request):
    """List all customer orders"""
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    
    # Filter by status if requested
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    context = {
        'orders': orders,
        'status_filter': status_filter,
    }
    
    return render(request, 'orders/order_list.html', context)


@login_required
def reorder_view(request, order_id):
    """Reorder from previous order"""
    original_order = get_object_or_404(Order, order_id=order_id, customer=request.user)
    
    if request.method == 'POST':
        form = OrderForm(request.POST, request.FILES)
        if form.is_valid():
            order = form.save(commit=False)
            order.customer = request.user
            order.save()
            
            UserDelivery.objects.create(order=order, customer=request.user)
            
            messages.success(
                request,
                f'Order {order.order_id} has been created from your previous order!'
            )
            return redirect('orders:order_detail', order_id=order.order_id)
    else:
        # Pre-fill form with previous order data
        form = OrderForm(initial={
            'pickup_address': original_order.pickup_address,
            'delivery_address': original_order.delivery_address,
            'parcel_weight': original_order.parcel_weight,
            'quantity': original_order.quantity,
            'description': original_order.description,
        })
    
    context = {
        'form': form,
        'original_order': original_order,
        'is_reorder': True,
    }
    
    return render(request, 'orders/create_order.html', context)


def track_order_public_view(request):
    """Public order tracking - no login required"""
    order_id = request.GET.get('order_id', '').strip().upper()
    order = None
    error = None
    
    if order_id:
        try:
            order = Order.objects.get(order_id=order_id)
        except Order.DoesNotExist:
            error = f"Order '{order_id}' not found. Please check your Order ID and try again."
    
    if order:
        # Timeline data
        timeline = []
        
        timeline.append({
            'status': 'UNDER_REVIEW',
            'label': 'Order Placed',
            'date': order.created_at,
            'completed': True,
            'icon': 'bi-check-circle-fill'
        })
        
        if order.status in ['ACCEPTED', 'PICKED', 'ON_THE_WAY', 'DELIVERED']:
            timeline.append({
                'status': 'ACCEPTED',
                'label': 'Order Accepted',
                'date': order.accepted_at,
                'completed': True,
                'icon': 'bi-check-circle-fill'
            })
        else:
            timeline.append({
                'status': 'ACCEPTED',
                'label': 'Order Accepted',
                'date': None,
                'completed': False,
                'icon': 'bi-circle'
            })
        
        if order.status in ['PICKED', 'ON_THE_WAY', 'DELIVERED']:
            timeline.append({
                'status': 'PICKED',
                'label': 'Parcel Picked Up',
                'date': order.picked_at,
                'completed': True,
                'icon': 'bi-check-circle-fill'
            })
        else:
            timeline.append({
                'status': 'PICKED',
                'label': 'Parcel Picked Up',
                'date': None,
                'completed': False,
                'icon': 'bi-circle'
            })
        
        if order.status in ['ON_THE_WAY', 'DELIVERED']:
            timeline.append({
                'status': 'ON_THE_WAY',
                'label': 'Out for Delivery',
                'date': order.updated_at,
                'completed': True,
                'icon': 'bi-check-circle-fill'
            })
        else:
            timeline.append({
                'status': 'ON_THE_WAY',
                'label': 'Out for Delivery',
                'date': None,
                'completed': False,
                'icon': 'bi-circle'
            })
        
        if order.status == 'DELIVERED':
            timeline.append({
                'status': 'DELIVERED',
                'label': 'Delivered',
                'date': order.delivered_at,
                'completed': True,
                'icon': 'bi-check-circle-fill'
            })
        else:
            timeline.append({
                'status': 'DELIVERED',
                'label': 'Delivered',
                'date': None,
                'completed': False,
                'icon': 'bi-circle'
            })
        
        context = {
            'order': order,
            'timeline': timeline,
            'search_query': order_id,
        }
    else:
        context = {
            'error': error,
            'search_query': order_id,
        }
    
    return render(request, 'orders/track_order_public.html', context)


@login_required
def track_order_view(request, order_id):
    """Track order status (authenticated)"""
    order = get_object_or_404(Order, order_id=order_id, customer=request.user)
    
    # Timeline data
    timeline = []
    
    timeline.append({
        'status': 'UNDER_REVIEW',
        'label': 'Order Placed',
        'date': order.created_at,
        'completed': True
    })
    
    if order.status in ['ACCEPTED', 'PICKED', 'ON_THE_WAY', 'DELIVERED']:
        timeline.append({
            'status': 'ACCEPTED',
            'label': 'Order Accepted',
            'date': order.accepted_at,
            'completed': True
        })
    
    if order.status in ['PICKED', 'ON_THE_WAY', 'DELIVERED']:
        timeline.append({
            'status': 'PICKED',
            'label': 'Parcel Picked Up',
            'date': order.picked_at,
            'completed': True
        })
    
    if order.status in ['ON_THE_WAY', 'DELIVERED']:
        timeline.append({
            'status': 'ON_THE_WAY',
            'label': 'Out for Delivery',
            'date': order.updated_at,
            'completed': True
        })
    
    if order.status == 'DELIVERED':
        timeline.append({
            'status': 'DELIVERED',
            'label': 'Delivered',
            'date': order.delivered_at,
            'completed': True
        })
    
    context = {
        'order': order,
        'timeline': timeline,
    }
    
    return render(request, 'orders/track_order.html', context)


# Admin Views
@login_required
def admin_dashboard_view(request):
    """Admin dashboard view"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('orders:dashboard')
    
    # Statistics
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='UNDER_REVIEW').count()
    active_orders = Order.objects.filter(
        status__in=['ACCEPTED', 'PICKED', 'ON_THE_WAY']
    ).count()
    delivered_orders = Order.objects.filter(status='DELIVERED').count()
    
    # Recent orders
    recent_orders = Order.objects.all().order_by('-created_at')[:10]
    
    # Monthly statistics
    current_month = timezone.now().month
    current_year = timezone.now().year
    monthly_base = Order.objects.filter(
        created_at__month=current_month,
        created_at__year=current_year
    )
    monthly_orders = monthly_base.count()
    monthly_delivered = monthly_base.filter(status='DELIVERED').count()
    monthly_active = monthly_base.filter(
        status__in=['ACCEPTED', 'PICKED', 'ON_THE_WAY']
    ).count()
    
    context = {
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'active_orders': active_orders,
        'delivered_orders': delivered_orders,
        'recent_orders': recent_orders,
        'monthly_orders': monthly_orders,
        'monthly_delivered': monthly_delivered,
        'monthly_active': monthly_active,
    }
    
    return render(request, 'orders/admin_dashboard.html', context)


@login_required
def admin_order_list_view(request):
    """Admin order list view"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('orders:dashboard')
    
    orders = Order.objects.all().order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        if status_filter == 'ACTIVE':
            # Active = Accepted, Picked, On The Way
            orders = orders.filter(status__in=['ACCEPTED', 'PICKED', 'ON_THE_WAY'])
        else:
            orders = orders.filter(status=status_filter)
    
    # Search
    search_query = request.GET.get('search')
    if search_query:
        orders = orders.filter(
            Q(order_id__icontains=search_query) |
            Q(customer__email__icontains=search_query) |
            Q(customer__first_name__icontains=search_query) |
            Q(customer__last_name__icontains=search_query)
        )
    
    # Calculate this month's statistics
    from django.db.models import Sum
    from datetime import datetime
    
    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    month_orders = Order.objects.filter(created_at__gte=start_of_month)
    
    stats = {
        'total_orders': month_orders.count(),
        'pending': month_orders.filter(status='UNDER_REVIEW').count(),
        'delivered': month_orders.filter(status='DELIVERED').count(),
        'paid': month_orders.filter(is_paid=True).count(),
        'in_transit': month_orders.filter(status__in=['PICKED', 'ON_THE_WAY']).count(),
        'revenue': month_orders.filter(is_paid=True).aggregate(total=Sum('courier_amount'))['total'] or 0,
    }
    
    context = {
        'orders': orders,
        'status_filter': status_filter,
        'search_query': search_query,
        'stats': stats,
    }
    
    return render(request, 'orders/admin_order_list.html', context)


@login_required
def admin_order_detail_view(request, order_id):
    """Admin order detail and management view"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('orders:dashboard')
    
    order = get_object_or_404(Order, order_id=order_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'accept':
            courier_amount = request.POST.get('courier_amount')
            if courier_amount:
                order.status = 'ACCEPTED'
                order.courier_amount = courier_amount
                order.accepted_at = timezone.now()
                order.save()
                messages.success(request, f'Order {order_id} has been accepted.')
            else:
                messages.error(request, 'Please enter courier amount.')
        
        elif action == 'reject':
            order.status = 'REJECTED'
            order.save()
            messages.warning(request, f'Order {order_id} has been rejected.')
        
        elif action == 'update_status':
            new_status = request.POST.get('status')
            if new_status:
                order.status = new_status
                if new_status == 'PICKED':
                    order.picked_at = timezone.now()
                elif new_status == 'DELIVERED':
                    order.delivered_at = timezone.now()
                order.save()
                messages.success(request, f'Order status updated to {order.get_status_display()}.')
        
        elif action == 'upload_delivery_proof':
            delivery_proof = request.FILES.get('delivery_proof_image')
            if delivery_proof:
                order.delivery_proof_image = delivery_proof
                order.save()
                messages.success(request, 'Delivery proof image uploaded successfully.')
            else:
                messages.error(request, 'Please select an image to upload.')
        
        return redirect('orders:admin_order_detail', order_id=order_id)
    
    return render(request, 'orders/admin_order_detail.html', {'order': order})


# Concern Management Views
@login_required
def raise_concern_view(request, order_id):
    """Customer can raise concern about delivered order"""
    order = get_object_or_404(Order, order_id=order_id, customer=request.user)
    
    # Only allow concerns for delivered orders
    if order.status != 'DELIVERED':
        messages.error(request, 'You can only raise concerns for delivered orders.')
        return redirect('orders:order_detail', order_id=order_id)
    
    if request.method == 'POST':
        form = OrderConcernForm(request.POST, request.FILES)
        if form.is_valid():
            concern = form.save(commit=False)
            concern.order = order
            concern.customer = request.user
            concern.save()
            
            messages.success(request, 'Your concern has been submitted. Our team will review it shortly.')
            return redirect('orders:order_detail', order_id=order_id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = OrderConcernForm()
    
    context = {
        'form': form,
        'order': order,
    }
    
    return render(request, 'orders/raise_concern.html', context)


@login_required
def concern_list_view(request):
    """View all concerns raised by customer"""
    concerns = OrderConcern.objects.filter(customer=request.user).order_by('-created_at')
    
    context = {
        'concerns': concerns,
    }
    
    return render(request, 'orders/concern_list.html', context)


@login_required
def concern_detail_view(request, concern_id):
    """View concern details"""
    concern = get_object_or_404(OrderConcern, id=concern_id, customer=request.user)
    
    context = {
        'concern': concern,
    }
    
    return render(request, 'orders/concern_detail.html', context)


@login_required
def admin_concern_list_view(request):
    """Admin view for all concerns"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('orders:dashboard')
    
    concerns = OrderConcern.objects.all().order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        concerns = concerns.filter(status=status_filter)
    
    context = {
        'concerns': concerns,
        'status_filter': status_filter,
    }
    
    return render(request, 'orders/admin_concern_list.html', context)


@login_required
def admin_concern_detail_view(request, concern_id):
    """Admin view for concern management"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('orders:dashboard')
    
    concern = get_object_or_404(OrderConcern, id=concern_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_status':
            new_status = request.POST.get('status')
            admin_response = request.POST.get('admin_response')
            
            if new_status:
                concern.status = new_status
                if admin_response:
                    concern.admin_response = admin_response
                if new_status == 'RESOLVED':
                    concern.resolved_at = timezone.now()
                concern.save()
                messages.success(request, 'Concern updated successfully.')
        
        return redirect('orders:admin_concern_detail', concern_id=concern_id)
    
    context = {
        'concern': concern,
    }
    
    return render(request, 'orders/admin_concern_detail.html', context)


@login_required
def check_order_status_api(request, order_id):
    """API endpoint to check order status - returns JSON"""
    try:
        order = get_object_or_404(Order, order_id=order_id, customer=request.user)
        
        data = {
            'status': order.status,
            'status_display': order.get_status_display(),
            'status_class': order.get_status_display_class(),
            'courier_amount': str(order.courier_amount) if order.courier_amount else None,
            'is_paid': order.is_paid,
            'can_be_paid': order.can_be_paid(),
            'updated_at': order.updated_at.isoformat(),
        }
        
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def test_auto_refresh_view(request, order_id):
    """Test page for auto-refresh functionality"""
    order = get_object_or_404(Order, order_id=order_id, customer=request.user)
    
    context = {
        'order': order,
    }
    
    return render(request, 'orders/test_auto_refresh.html', context)


def calculate_quote_api(request):
    """
    API endpoint to calculate shipping quote using new Helpii pricing rules.
    Single source of truth for pricing - used by frontend for estimates.
    
    GET Parameters:
        - distance: Distance in kilometers
        - weight: Weight in kilograms
        - parcel_type: Type of parcel (GENERAL, FRAGILE, etc.)
        - delivery_speed: Delivery type code (EXPRESS_2HR, SAME_DAY, OVERNIGHT)
        - is_oversize: Whether item is too large for a standard car
    
    Returns:
        JSON with estimate, breakdown, and rule info
    """
    from .models import DeliveryType, PricingRule
    
    try:
        # Get parameters
        distance = float(request.GET.get('distance', 0))
        weight = float(request.GET.get('weight', 0))
        parcel_type = request.GET.get('parcel_type', 'GENERAL')
        delivery_speed = request.GET.get('delivery_speed', 'SAME_DAY')
        is_oversize = request.GET.get('is_oversize', 'false').lower() == 'true'
        
        if distance <= 0 or weight <= 0:
            return JsonResponse({
                'success': False,
                'error': 'Distance and weight must be greater than 0'
            }, status=400)
        
        # Find delivery type
        delivery_type = DeliveryType.objects.filter(
            code=delivery_speed,
            is_active=True
        ).first()
        
        if not delivery_type:
            return JsonResponse({
                'success': False,
                'error': f'Delivery type "{delivery_speed}" not found or inactive'
            }, status=400)
        
        # Find matching pricing rule
        rules = PricingRule.objects.filter(
            delivery_type=delivery_type,
            is_active=True
        ).order_by('priority')
        
        matched_rule = None
        for rule in rules:
            if rule.matches(weight, distance, is_oversize):
                matched_rule = rule
                break
        
        if not matched_rule:
            return JsonResponse({
                'success': False,
                'error': f'No pricing rule found for {weight}kg, {distance}km, oversize={is_oversize}'
            }, status=400)
        
        # Calculate price
        estimate = matched_rule.calculate_price(distance, weight, is_oversize)
        
        # Build breakdown info
        breakdown = {
            'distance_km': round(distance, 2),
            'weight_kg': round(weight, 2),
            'is_oversize': is_oversize,
            'delivery_type': delivery_type.name,
            'delivery_code': delivery_type.code,
            'base_price': float(delivery_type.base_price),
            'rule_name': matched_rule.name,
            'calculation_type': matched_rule.calculation_type,
        }
        
        # Add calculation-specific details
        if matched_rule.calculation_type == 'PER_KM':
            breakdown['rate_per_km'] = float(matched_rule.rate_per_km) if matched_rule.rate_per_km else 0
            breakdown['formula'] = f"${delivery_type.base_price} + ${matched_rule.rate_per_km}/km × {distance:.1f}km"
        elif matched_rule.calculation_type == 'CAPPED':
            breakdown['rate_per_km'] = float(matched_rule.rate_per_km) if matched_rule.rate_per_km else 0
            breakdown['max_price'] = float(matched_rule.max_price) if matched_rule.max_price else 0
            breakdown['formula'] = f"${delivery_type.base_price} + ${matched_rule.rate_per_km}/km (max ${matched_rule.max_price})"
        else:  # FLAT
            breakdown['flat_total'] = float(matched_rule.flat_total) if matched_rule.flat_total else 0
            breakdown['formula'] = f"Flat ${matched_rule.flat_total}"
        
        # Add oversize surcharge info if applicable
        if is_oversize and matched_rule.oversize_surcharge:
            breakdown['oversize_surcharge'] = float(matched_rule.oversize_surcharge)
            breakdown['formula'] += f" + ${matched_rule.oversize_surcharge} oversize"
        
        return JsonResponse({
            'success': True,
            'estimate': estimate,
            'breakdown': breakdown,
            'requires_admin_approval': delivery_type.requires_admin_approval,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

