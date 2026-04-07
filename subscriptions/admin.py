from django.contrib import admin

from .models import NotificationHistory, Subscription


class NotificationHistoryInline(admin.TabularInline):
    model = NotificationHistory
    fields = ('sent_at', 'slot', 'days_until', 'label')
    readonly_fields = fields
    max_num = 5
    extra = 0
    can_delete = False


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'platform',
        'plan_name',
        'owner',
        'status',
        'upcoming_billing_date',
        'advance_reminder_days',
        'repeat_reminder_start_days',
        'price',
        'currency',
    )
    list_filter = ('status', 'cycle_unit', 'currency')
    search_fields = ('platform', 'plan_name', 'owner__username', 'reminder_email')
    readonly_fields = ('created_at', 'updated_at', 'last_reminder_sent_on', 'last_reminder_key')
    inlines = [NotificationHistoryInline]


@admin.register(NotificationHistory)
class NotificationHistoryAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'slot', 'days_until', 'sent_at')
    list_filter = ('slot',)
