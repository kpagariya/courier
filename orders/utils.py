"""
Utility functions for orders app
"""
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import googlemaps


def get_coordinates_from_address(address):
    """
    Get latitude and longitude from address using geopy
    """
    try:
        geolocator = Nominatim(user_agent="courierpro")
        location = geolocator.geocode(address + ", New Zealand")
        if location:
            return location.latitude, location.longitude
        return None, None
    except Exception as e:
        print(f"Error getting coordinates: {e}")
        return None, None


def calculate_distance(pickup_lat, pickup_lng, delivery_lat, delivery_lng):
    """
    Calculate distance between two coordinates in kilometers
    """
    try:
        pickup_coords = (pickup_lat, pickup_lng)
        delivery_coords = (delivery_lat, delivery_lng)
        distance = geodesic(pickup_coords, delivery_coords).kilometers
        return round(distance, 2)
    except Exception as e:
        print(f"Error calculating distance: {e}")
        return None


def get_coordinates_google_maps(address):
    """
    Get coordinates using Google Maps API (more accurate for NZ)
    Falls back to geopy if Google Maps key is not available
    """
    if settings.GOOGLE_MAPS_API_KEY:
        try:
            gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
            geocode_result = gmaps.geocode(address + ", New Zealand")
            if geocode_result:
                location = geocode_result[0]['geometry']['location']
                return location['lat'], location['lng']
        except Exception as e:
            print(f"Google Maps API error: {e}")
    
    # Fallback to geopy
    return get_coordinates_from_address(address)


def calculate_distance_google_maps(pickup_address, delivery_address):
    """
    Calculate distance using Google Maps Distance Matrix API
    Falls back to geodesic calculation if API is not available
    """
    if settings.GOOGLE_MAPS_API_KEY:
        try:
            gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
            result = gmaps.distance_matrix(
                origins=[pickup_address + ", New Zealand"],
                destinations=[delivery_address + ", New Zealand"],
                mode="driving"
            )
            
            if result['rows'][0]['elements'][0]['status'] == 'OK':
                # Distance in meters, convert to kilometers
                distance_m = result['rows'][0]['elements'][0]['distance']['value']
                distance_km = distance_m / 1000
                return round(distance_km, 2)
        except Exception as e:
            print(f"Google Maps Distance Matrix error: {e}")
    
    # Fallback to geodesic calculation
    pickup_lat, pickup_lng = get_coordinates_google_maps(pickup_address)
    delivery_lat, delivery_lng = get_coordinates_google_maps(delivery_address)
    
    if all([pickup_lat, pickup_lng, delivery_lat, delivery_lng]):
        return calculate_distance(pickup_lat, pickup_lng, delivery_lat, delivery_lng)
    
    return None


# ============================================
# EMAIL NOTIFICATION FUNCTIONS FOR CUSTOMERS
# ============================================

def send_order_confirmation_email(order):
    """
    Send order confirmation email to customer when order is created
    """
    try:
        subject = f'Order Confirmation - {order.order_id}'
        html_message = render_to_string('orders/email/customer_order_created.html', {'order': order})
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"✅ Order confirmation email sent to {order.customer.email}")
    except Exception as e:
        print(f"❌ Error sending order confirmation email: {e}")


def send_order_accepted_email(order):
    """
    Send email to customer when admin accepts the order
    """
    try:
        subject = f'Order Accepted - {order.order_id}'
        html_message = render_to_string('orders/email/customer_order_accepted.html', {'order': order})
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"✅ Order accepted email sent to {order.customer.email}")
    except Exception as e:
        print(f"❌ Error sending order accepted email: {e}")


def send_order_rejected_email(order):
    """
    Send email to customer when admin rejects the order
    """
    try:
        subject = f'Order Update - {order.order_id}'
        html_message = render_to_string('orders/email/customer_order_rejected.html', {'order': order})
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"✅ Order rejected email sent to {order.customer.email}")
    except Exception as e:
        print(f"❌ Error sending order rejected email: {e}")


def send_order_picked_email(order):
    """
    Send email to customer when order is picked up
    """
    try:
        subject = f'Order Picked Up - {order.order_id}'
        html_message = render_to_string('orders/email/customer_order_picked.html', {'order': order})
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"✅ Order picked email sent to {order.customer.email}")
    except Exception as e:
        print(f"❌ Error sending order picked email: {e}")


def send_order_on_the_way_email(order):
    """
    Send email to customer when order is on the way
    """
    try:
        subject = f'Order On The Way - {order.order_id}'
        html_message = render_to_string('orders/email/customer_order_on_the_way.html', {'order': order})
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"✅ Order on the way email sent to {order.customer.email}")
    except Exception as e:
        print(f"❌ Error sending order on the way email: {e}")


def send_order_delivered_email(order):
    """
    Send email to customer when order is delivered
    """
    try:
        subject = f'Order Delivered - {order.order_id}'
        html_message = render_to_string('orders/email/customer_order_delivered.html', {'order': order})
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"✅ Order delivered email sent to {order.customer.email}")
    except Exception as e:
        print(f"❌ Error sending order delivered email: {e}")


def send_payment_confirmation_email(order):
    """
    Send payment confirmation email to customer
    """
    try:
        subject = f'Payment Confirmed - {order.order_id}'
        html_message = render_to_string('orders/email/customer_payment_confirmed.html', {'order': order})
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"✅ Payment confirmation email sent to {order.customer.email}")
    except Exception as e:
        print(f"❌ Error sending payment confirmation email: {e}")

