import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
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
    advance_reminder_days = models.PositiveIntegerField(
        default=14,
        help_text='Send one reminder when this many days remain.',
    )
    repeat_reminder_start_days = models.PositiveIntegerField(
        default=7,
        help_text='Start morning and night reminders when this many days remain.',
    )
    repeat_reminder_morning = models.BooleanField(
        default=True,
        help_text='Send morning reminders inside the repeated reminder window.',
    )
    repeat_reminder_night = models.BooleanField(
        default=True,
        help_text='Send night reminders inside the repeated reminder window.',
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    notes = models.TextField(blank=True)
    last_reminder_sent_on = models.DateField(null=True, blank=True)
    last_reminder_key = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['platform', 'plan_name', 'created_at']

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return f'{self.platform} - {self.plan_name}' if self.plan_name else self.platform

    def clean(self):
        if self.advance_reminder_days <= self.repeat_reminder_start_days:
            raise ValidationError(
                {
                    'advance_reminder_days': (
                        'The advance reminder must happen before the repeated reminder window starts.'
                    )
                }
            )

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
        return days is not None and 1 <= days <= self.repeat_reminder_start_days

    @property
    def is_advance_reminder_day(self):
        return self.days_until_renewal == self.advance_reminder_days

    @property
    def needs_reminder_attention(self):
        return self.is_advance_reminder_day or self.in_reminder_window

    @property
    def cycle_description(self):
        unit_label = self.get_cycle_unit_display().lower()
        if self.cycle_length == 1:
            return f'Every {unit_label}'
        return f'Every {self.cycle_length} {unit_label}s'

    @property
    def reminder_schedule_description(self):
        cadence = []
        cadence.append(f'1 email at {self.advance_reminder_days} days remaining')

        times = []
        if self.repeat_reminder_morning:
            times.append('morning')
        if self.repeat_reminder_night:
            times.append('night')

        if times:
            if len(times) == 2:
                time_summary = 'morning and night'
            else:
                time_summary = times[0]
            cadence.append(
                f'{time_summary} from {self.repeat_reminder_start_days} days remaining'
            )

        return ', then '.join(cadence)

    @staticmethod
    def resolve_reminder_slot(slot='auto'):
        if slot in {'morning', 'night'}:
            return slot

        current_hour = timezone.localtime().hour
        return 'morning' if current_hour < 15 else 'night'

    def get_pending_reminder(self, on_date=None, slot='auto'):
        if self.status != self.Status.ACTIVE:
            return None

        run_date = on_date or timezone.localdate()
        billing_date = self.get_next_billing_date(run_date)
        if billing_date is None:
            return None

        days_until = (billing_date - run_date).days
        resolved_slot = self.resolve_reminder_slot(slot)

        if days_until == self.advance_reminder_days:
            reminder_key = f'{billing_date.isoformat()}:{days_until}:advance'
            reminder_label = f'{days_until}-day reminder'
        elif 1 <= days_until <= self.repeat_reminder_start_days:
            if resolved_slot == 'morning' and not self.repeat_reminder_morning:
                return None
            if resolved_slot == 'night' and not self.repeat_reminder_night:
                return None

            reminder_key = f'{billing_date.isoformat()}:{days_until}:{resolved_slot}'
            reminder_label = f'{resolved_slot.capitalize()} reminder'
        else:
            return None

        if self.last_reminder_key == reminder_key:
            return None

        return {
            'billing_date': billing_date,
            'days_until': days_until,
            'slot': resolved_slot,
            'key': reminder_key,
            'label': reminder_label,
        }

    def should_send_reminder(self, on_date=None, slot='auto'):
        return self.get_pending_reminder(on_date=on_date, slot=slot) is not None

    def save(self, *args, **kwargs):
        self.currency = (self.currency or '').upper()
        self.full_clean()
        super().save(*args, **kwargs)
