import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Subscription(models.Model):
    class CycleUnit(models.TextChoices):
        DAY = 'day', 'Day'
        WEEK = 'week', 'Week'
        MONTH = 'month', 'Month'
        YEAR = 'year', 'Year'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        CANCELED = 'canceled', 'Canceled'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions',
    )
    platform = models.CharField(max_length=120)
    plan_name = models.CharField(max_length=120, blank=True)
    anchor_date = models.DateField(
        help_text='The original billing date or the next known renewal date.'
    )
    cycle_length = models.PositiveIntegerField(default=1)
    cycle_unit = models.CharField(
        max_length=10,
        choices=CycleUnit.choices,
        default=CycleUnit.MONTH,
    )
    reminder_email = models.EmailField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    notes = models.TextField(blank=True)
    last_reminder_sent_on = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['platform', 'plan_name', 'created_at']

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return f'{self.platform} - {self.plan_name}' if self.plan_name else self.platform

    @staticmethod
    def _days_in_month(year, month):
        return calendar.monthrange(year, month)[1]

    @classmethod
    def _add_months(cls, anchor, months):
        month_index = (anchor.month - 1) + months
        year = anchor.year + (month_index // 12)
        month = (month_index % 12) + 1
        day = min(anchor.day, cls._days_in_month(year, month))
        return date(year, month, day)

    @classmethod
    def _add_years(cls, anchor, years):
        target_year = anchor.year + years
        day = min(anchor.day, cls._days_in_month(target_year, anchor.month))
        return date(target_year, anchor.month, day)

    def get_next_billing_date(self, reference_date=None):
        if self.status == self.Status.CANCELED:
            return None

        ref = reference_date or timezone.localdate()
        if ref <= self.anchor_date:
            return self.anchor_date

        if self.cycle_unit == self.CycleUnit.DAY:
            step_days = self.cycle_length
            elapsed_days = (ref - self.anchor_date).days
            steps = elapsed_days // step_days
            candidate = self.anchor_date + timedelta(days=steps * step_days)
            if candidate < ref:
                candidate += timedelta(days=step_days)
            return candidate

        if self.cycle_unit == self.CycleUnit.WEEK:
            step_days = self.cycle_length * 7
            elapsed_days = (ref - self.anchor_date).days
            steps = elapsed_days // step_days
            candidate = self.anchor_date + timedelta(days=steps * step_days)
            if candidate < ref:
                candidate += timedelta(days=step_days)
            return candidate

        if self.cycle_unit == self.CycleUnit.MONTH:
            months_since_anchor = (
                (ref.year - self.anchor_date.year) * 12
                + ref.month
                - self.anchor_date.month
            )
            steps = max(months_since_anchor // self.cycle_length, 0)
            candidate = self._add_months(self.anchor_date, steps * self.cycle_length)
            while candidate < ref:
                steps += 1
                candidate = self._add_months(
                    self.anchor_date,
                    steps * self.cycle_length,
                )
            return candidate

        years_since_anchor = ref.year - self.anchor_date.year
        steps = max(years_since_anchor // self.cycle_length, 0)
        candidate = self._add_years(self.anchor_date, steps * self.cycle_length)
        while candidate < ref:
            steps += 1
            candidate = self._add_years(self.anchor_date, steps * self.cycle_length)
        return candidate

    @property
    def upcoming_billing_date(self):
        return self.get_next_billing_date()

    @property
    def days_until_renewal(self):
        billing_date = self.upcoming_billing_date
        if billing_date is None:
            return None
        return (billing_date - timezone.localdate()).days

    @property
    def is_due_today(self):
        return self.days_until_renewal == 0

    @property
    def in_reminder_window(self):
        days = self.days_until_renewal
        return days is not None and 1 <= days <= 7

    @property
    def cycle_description(self):
        unit_label = self.get_cycle_unit_display().lower()
        if self.cycle_length == 1:
            return f'Every {unit_label}'
        return f'Every {self.cycle_length} {unit_label}s'

    def should_send_reminder(self, on_date=None):
        if self.status != self.Status.ACTIVE:
            return False

        run_date = on_date or timezone.localdate()
        billing_date = self.get_next_billing_date(run_date)
        if billing_date is None:
            return False

        days_until = (billing_date - run_date).days
        return 1 <= days_until <= 7 and self.last_reminder_sent_on != run_date

    def save(self, *args, **kwargs):
        self.currency = (self.currency or '').upper()
        super().save(*args, **kwargs)

# Create your models here.
