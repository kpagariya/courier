"""
Views for core pages
"""
from django.shortcuts import render


def home_view(request):
    """Home page view"""
    return render(request, 'core/home.html')


def services_view(request):
    """Services page view"""
    services_list = [
        {
            'title': 'Domestic Delivery',
            'icon': 'bi-truck',
            'description': 'Fast and reliable delivery across New Zealand. From Auckland to Queenstown, we deliver anywhere in the country.',
        },
        {
            'title': 'Express Shipping',
            'icon': 'bi-lightning-charge',
            'description': 'Need it urgently? Our express service ensures same-day or next-day delivery for time-sensitive parcels.',
        },
        {
            'title': 'Parcel Tracking',
            'icon': 'bi-geo-alt',
            'description': 'Track your parcel in real-time with our advanced tracking system. Know exactly where your package is at all times.',
        },
        {
            'title': 'Secure Handling',
            'icon': 'bi-shield-check',
            'description': 'Your parcels are handled with care. We provide secure packaging and insurance options for valuable items.',
        },
        {
            'title': 'Bulk Shipping',
            'icon': 'bi-boxes',
            'description': 'Sending multiple parcels? Get special rates for bulk shipping and business accounts.',
        },
        {
            'title': '24/7 Support',
            'icon': 'bi-headset',
            'description': 'Our customer support team is available round the clock to assist with any queries or concerns.',
        },
    ]
    
    return render(request, 'core/services.html', {'services': services_list})


def contact_view(request):
    """Contact us page view"""
    return render(request, 'core/contact.html')


def career_view(request):
    """Career page view"""
    job_openings = [
        {
            'title': 'Delivery Driver',
            'location': 'Auckland',
            'type': 'Full-time',
            'description': 'We are looking for reliable delivery drivers to join our team.',
        },
        {
            'title': 'Customer Service Representative',
            'location': 'Wellington',
            'type': 'Full-time',
            'description': 'Join our customer service team to help our customers with their queries.',
        },
        {
            'title': 'Warehouse Manager',
            'location': 'Christchurch',
            'type': 'Full-time',
            'description': 'Manage warehouse operations and ensure efficient parcel processing.',
        },
    ]
    
    return render(request, 'core/career.html', {'job_openings': job_openings})


def terms_view(request):
    """Terms and conditions page view"""
    return render(request, 'core/terms.html')


def privacy_view(request):
    """Privacy policy page view"""
    return render(request, 'core/privacy.html')


def about_view(request):
    """About us page view"""
    return render(request, 'core/about.html')

