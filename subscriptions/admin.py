from django.contrib import admin

from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'platform',
        'plan_name',
        'owner',
        'status',
        'upcoming_billing_date',
        'price',
        'currency',
    )
    list_filter = ('status', 'cycle_unit', 'currency')
    search_fields = ('platform', 'plan_name', 'owner__username', 'reminder_email')
    readonly_fields = ('created_at', 'updated_at', 'last_reminder_sent_on')

# Register your models here.
