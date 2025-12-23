"""
Sitemap configuration for SEO
Helps search engines discover and index all pages
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    """Sitemap for static pages"""
    priority = 0.8
    changefreq = 'weekly'
    protocol = 'https'
    
    def items(self):
        return [
            'core:home',
            'core:services', 
            'core:about',
            'core:contact',
            'core:career',
            'core:terms',
            'core:privacy',
        ]
    
    def location(self, item):
        return reverse(item)


class HomeSitemap(Sitemap):
    """Homepage with highest priority"""
    priority = 1.0
    changefreq = 'daily'
    protocol = 'https'
    
    def items(self):
        return ['core:home']
    
    def location(self, item):
        return reverse(item)

