from django.contrib import admin
from .models import JobOpening


@admin.register(JobOpening)
class JobOpeningAdmin(admin.ModelAdmin):
    list_display = ['title', 'location', 'job_type', 'is_active', 'created_at']
    list_filter = ['is_active', 'job_type', 'location']
    search_fields = ['title', 'description']
    list_editable = ['is_active']  # Quick toggle active/inactive from list view
    ordering = ['-created_at']

