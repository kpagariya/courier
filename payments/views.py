"""
Views for payment processing
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
import stripe
import paypalrestsdk
import uuid
from orders.models import Order
from .models import Payment

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Configure PayPal
paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,  # sandbox or live
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET
})


@login_required
def payment_method_view(request, order_id):
    """Select payment method"""
    order = get_object_or_404(Order, order_id=order_id, customer=request.user)
    
    # Check if order can be paid
    if not order.can_be_paid():
        messages.error(request, 'This order cannot be paid at this time.')
        return redirect('orders:order_detail', order_id=order_id)
    
    context = {
        'order': order,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
    }
    
    return render(request, 'payments/payment_method.html', context)


@login_required
def stripe_payment_view(request, order_id):
    """Stripe payment processing"""
    order = get_object_or_404(Order, order_id=order_id, customer=request.user)
    
    if not order.can_be_paid():
        messages.error(request, 'This order cannot be paid at this time.')
        return redirect('orders:order_detail', order_id=order_id)
    
    if request.method == 'POST':
        try:
            # Create payment intent with receipt email
            intent = stripe.PaymentIntent.create(
                amount=int(float(order.courier_amount) * 100),  # Amount in cents
                currency='nzd',
                receipt_email=request.user.email,  # Stripe sends receipt to this email
                description=f'Helpii Courier - Order {order.order_id}',
                metadata={
                    'order_id': order.order_id,
                    'customer_name': request.user.get_full_name(),
                    'customer_email': request.user.email
                }
            )
            
            # Create payment record
            transaction_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
            payment = Payment.objects.create(
                transaction_id=transaction_id,
                order=order,
                customer=request.user,
                amount=order.courier_amount,
                currency='NZD',
                payment_method='STRIPE',
                status='PROCESSING',
                stripe_payment_intent_id=intent.id,
                description=f'Payment for order {order.order_id}'
            )
            
            context = {
                'order': order,
                'payment': payment,
                'client_secret': intent.client_secret,
                'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
            }
            
            return render(request, 'payments/stripe_payment.html', context)
            
        except Exception as e:
            messages.error(request, f'Payment initiation failed: {str(e)}')
            return redirect('payments:payment_method', order_id=order_id)
    
    return redirect('payments:payment_method', order_id=order_id)


@csrf_exempt
def stripe_webhook(request):
    """Stripe webhook handler"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_SECRET_KEY
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
    
    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        
        # Update payment and order
        try:
            payment = Payment.objects.get(stripe_payment_intent_id=payment_intent['id'])
            payment.status = 'COMPLETED'
            payment.completed_at = timezone.now()
            payment.save()
            
            # Update order
            order = payment.order
            order.is_paid = True
            order.save()
            
        except Payment.DoesNotExist:
            pass
    
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        
        try:
            payment = Payment.objects.get(stripe_payment_intent_id=payment_intent['id'])
            payment.status = 'FAILED'
            payment.save()
        except Payment.DoesNotExist:
            pass
    
    return HttpResponse(status=200)


@login_required
def stripe_payment_success(request, order_id):
    """Stripe payment success callback"""
    order = get_object_or_404(Order, order_id=order_id, customer=request.user)
    payment = Payment.objects.filter(order=order, payment_method='STRIPE').first()
    
    if payment:
        payment.status = 'COMPLETED'
        payment.completed_at = timezone.now()
        payment.save()
        
        order.is_paid = True
        order.save()
        
        messages.success(request, 'Payment successful! Your order has been confirmed.')
    
    return redirect('orders:order_detail', order_id=order_id)


@login_required
def paypal_payment_view(request, order_id):
    """PayPal payment processing"""
    order = get_object_or_404(Order, order_id=order_id, customer=request.user)
    
    if not order.can_be_paid():
        messages.error(request, 'This order cannot be paid at this time.')
        return redirect('orders:order_detail', order_id=order_id)
    
    if request.method == 'POST':
        try:
            # Create PayPal payment
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "redirect_urls": {
                    "return_url": request.build_absolute_uri(
                        f"/payments/paypal/execute/{order_id}/"
                    ),
                    "cancel_url": request.build_absolute_uri(
                        f"/payments/method/{order_id}/"
                    )
                },
                "transactions": [{
                    "item_list": {
                        "items": [{
                            "name": f"Courier Service - Order {order.order_id}",
                            "sku": order.order_id,
                            "price": str(order.courier_amount),
                            "currency": "NZD",
                            "quantity": 1
                        }]
                    },
                    "amount": {
                        "total": str(order.courier_amount),
                        "currency": "NZD"
                    },
                    "description": f"Payment for courier order {order.order_id}"
                }]
            })
            
            if payment.create():
                # Create payment record
                transaction_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
                Payment.objects.create(
                    transaction_id=transaction_id,
                    order=order,
                    customer=request.user,
                    amount=order.courier_amount,
                    currency='NZD',
                    payment_method='PAYPAL',
                    status='PROCESSING',
                    paypal_order_id=payment.id,
                    description=f'Payment for order {order.order_id}'
                )
                
                # Redirect to PayPal
                for link in payment.links:
                    if link.rel == "approval_url":
                        return redirect(link.href)
            else:
                messages.error(request, f'PayPal payment creation failed: {payment.error}')
                
        except Exception as e:
            messages.error(request, f'Payment initiation failed: {str(e)}')
    
    return redirect('payments:payment_method', order_id=order_id)


@login_required
def paypal_execute_view(request, order_id):
    """Execute PayPal payment"""
    order = get_object_or_404(Order, order_id=order_id, customer=request.user)
    
    payment_id = request.GET.get('paymentId')
    payer_id = request.GET.get('PayerID')
    
    if not payment_id or not payer_id:
        messages.error(request, 'Invalid payment parameters.')
        return redirect('orders:order_detail', order_id=order_id)
    
    try:
        payment = paypalrestsdk.Payment.find(payment_id)
        
        if payment.execute({"payer_id": payer_id}):
            # Update payment record
            payment_record = Payment.objects.filter(
                order=order,
                paypal_order_id=payment_id
            ).first()
            
            if payment_record:
                payment_record.status = 'COMPLETED'
                payment_record.completed_at = timezone.now()
                payment_record.save()
            
            # Update order
            order.is_paid = True
            order.save()
            
            messages.success(request, 'Payment successful! Your order has been confirmed.')
        else:
            messages.error(request, f'Payment execution failed: {payment.error}')
            
    except Exception as e:
        messages.error(request, f'Payment processing failed: {str(e)}')
    
    return redirect('orders:order_detail', order_id=order_id)


@login_required
def payment_history_view(request):
    """View payment history"""
    payments = Payment.objects.filter(customer=request.user).order_by('-created_at')
    
    context = {
        'payments': payments,
    }
    
    return render(request, 'payments/payment_history.html', context)

