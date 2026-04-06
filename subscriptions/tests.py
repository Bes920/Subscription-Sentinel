from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Subscription


class SubscriptionModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='tester',
            email='tester@example.com',
            password='testpass123',
        )

    def test_monthly_cycle_stays_anchored_to_original_day(self):
        subscription = Subscription.objects.create(
            owner=self.user,
            platform='Spotify',
            anchor_date=date(2025, 1, 31),
            cycle_length=1,
            cycle_unit=Subscription.CycleUnit.MONTH,
            reminder_email='alerts@example.com',
            price='9.99',
            currency='usd',
        )

        self.assertEqual(
            subscription.get_next_billing_date(date(2025, 2, 15)),
            date(2025, 2, 28),
        )
        self.assertEqual(
            subscription.get_next_billing_date(date(2025, 3, 20)),
            date(2025, 3, 31),
        )

    def test_custom_quarterly_cycle_moves_forward_correctly(self):
        subscription = Subscription.objects.create(
            owner=self.user,
            platform='Hack The Box',
            anchor_date=date(2025, 1, 15),
            cycle_length=3,
            cycle_unit=Subscription.CycleUnit.MONTH,
            reminder_email='alerts@example.com',
            price='18.00',
            currency='usd',
        )

        self.assertEqual(
            subscription.get_next_billing_date(date(2025, 6, 16)),
            date(2025, 7, 15),
        )

    def test_reminders_stop_when_subscription_is_canceled_or_already_sent(self):
        subscription = Subscription.objects.create(
            owner=self.user,
            platform='THM',
            anchor_date=date(2026, 4, 8),
            cycle_length=1,
            cycle_unit=Subscription.CycleUnit.MONTH,
            reminder_email='alerts@example.com',
            price='12.00',
            currency='usd',
        )

        run_date = date(2026, 4, 1)
        reminder = subscription.get_pending_reminder(run_date, slot='morning')
        self.assertIsNotNone(reminder)
        self.assertTrue(subscription.should_send_reminder(run_date, slot='morning'))

        subscription.last_reminder_sent_on = run_date
        subscription.last_reminder_key = reminder['key']
        self.assertFalse(subscription.should_send_reminder(run_date, slot='morning'))

        subscription.status = Subscription.Status.CANCELED
        self.assertFalse(subscription.should_send_reminder(run_date, slot='morning'))

    def test_advance_reminder_only_sends_once_on_the_advance_day(self):
        subscription = Subscription.objects.create(
            owner=self.user,
            platform='Netflix',
            anchor_date=date(2026, 4, 8),
            cycle_length=1,
            cycle_unit=Subscription.CycleUnit.MONTH,
            reminder_email='alerts@example.com',
            price='10.00',
            currency='usd',
        )

        run_date = date(2026, 3, 25)
        advance_reminder = subscription.get_pending_reminder(run_date, slot='morning')

        self.assertIsNotNone(advance_reminder)
        self.assertEqual(advance_reminder['label'], '14-day reminder')

        subscription.last_reminder_key = advance_reminder['key']
        self.assertIsNone(subscription.get_pending_reminder(run_date, slot='night'))

    def test_morning_and_night_reminders_can_both_send_in_repeat_window(self):
        subscription = Subscription.objects.create(
            owner=self.user,
            platform='Spotify',
            anchor_date=date(2026, 4, 8),
            cycle_length=1,
            cycle_unit=Subscription.CycleUnit.MONTH,
            reminder_email='alerts@example.com',
            price='9.99',
            currency='usd',
        )

        run_date = date(2026, 4, 1)
        morning_reminder = subscription.get_pending_reminder(run_date, slot='morning')
        self.assertIsNotNone(morning_reminder)
        self.assertEqual(morning_reminder['label'], 'Morning reminder')

        subscription.last_reminder_key = morning_reminder['key']
        night_reminder = subscription.get_pending_reminder(run_date, slot='night')
        self.assertIsNotNone(night_reminder)
        self.assertEqual(night_reminder['label'], 'Night reminder')

    def test_estimated_monthly_and_yearly_costs_are_normalized_from_cycle(self):
        subscription = Subscription.objects.create(
            owner=self.user,
            platform='Quarterly Tool',
            anchor_date=date(2026, 4, 8),
            cycle_length=3,
            cycle_unit=Subscription.CycleUnit.MONTH,
            reminder_email='alerts@example.com',
            price='18.00',
            currency='usd',
        )

        self.assertEqual(subscription.estimated_monthly_cost, Decimal('6.00'))
        self.assertEqual(subscription.estimated_yearly_cost, Decimal('72.00'))


class DashboardViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='owner',
            email='owner@example.com',
            password='testpass123',
        )
        self.other_user = get_user_model().objects.create_user(
            username='other',
            email='other@example.com',
            password='testpass123',
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_dashboard_only_shows_current_users_subscriptions(self):
        Subscription.objects.create(
            owner=self.user,
            platform='Spotify',
            anchor_date=date(2026, 4, 21),
            cycle_length=1,
            cycle_unit=Subscription.CycleUnit.MONTH,
            reminder_email='owner@example.com',
            price='9.99',
            currency='USD',
        )
        Subscription.objects.create(
            owner=self.other_user,
            platform='Private App',
            anchor_date=date(2026, 4, 21),
            cycle_length=1,
            cycle_unit=Subscription.CycleUnit.MONTH,
            reminder_email='other@example.com',
            price='19.99',
            currency='USD',
        )

        self.client.login(username='owner', password='testpass123')
        response = self.client.get(reverse('dashboard'))

        self.assertContains(response, 'Spotify')
        self.assertNotContains(response, 'Private App')

    def test_dashboard_includes_spending_breakdown_and_top_monthly_costs(self):
        monthly = Subscription.objects.create(
            owner=self.user,
            platform='Spotify',
            anchor_date=date(2026, 4, 21),
            cycle_length=1,
            cycle_unit=Subscription.CycleUnit.MONTH,
            reminder_email='owner@example.com',
            price='9.99',
            currency='USD',
        )
        yearly = Subscription.objects.create(
            owner=self.user,
            platform='Annual VPN',
            anchor_date=date(2026, 4, 16),
            cycle_length=1,
            cycle_unit=Subscription.CycleUnit.YEAR,
            reminder_email='owner@example.com',
            price='120.00',
            currency='USD',
        )
        Subscription.objects.create(
            owner=self.user,
            platform='Design App',
            anchor_date=date(2026, 6, 1),
            cycle_length=1,
            cycle_unit=Subscription.CycleUnit.MONTH,
            reminder_email='owner@example.com',
            price='15.00',
            currency='EUR',
        )

        self.client.login(username='owner', password='testpass123')
        response = self.client.get(reverse('dashboard'))

        spend_breakdown = response.context['spend_breakdown']
        usd_bucket = next(bucket for bucket in spend_breakdown if bucket['currency'] == 'USD')
        eur_bucket = next(bucket for bucket in spend_breakdown if bucket['currency'] == 'EUR')

        self.assertEqual(usd_bucket['active_count'], 2)
        self.assertEqual(usd_bucket['monthly_total'], Decimal('19.99'))
        self.assertEqual(usd_bucket['yearly_total'], Decimal('239.88'))
        self.assertEqual(usd_bucket['upcoming_30_total'], Decimal('129.99'))
        self.assertEqual(usd_bucket['upcoming_30_count'], 2)
        self.assertEqual(eur_bucket['monthly_total'], Decimal('15.00'))

        top_monthly = response.context['top_monthly_subscriptions']
        self.assertEqual(top_monthly[0].platform, 'Design App')
        self.assertEqual(top_monthly[1].pk, yearly.pk)
        self.assertEqual(top_monthly[2].pk, monthly.pk)
        self.assertContains(response, 'Estimated recurring cost by currency')
        self.assertContains(response, 'Top subscriptions by estimated monthly cost')


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='alerts@example.com',
    APP_BASE_URL='http://127.0.0.1:8000',
)
class ReminderCommandTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='mailer',
            email='mailer@example.com',
            password='testpass123',
        )

    def test_send_subscription_reminders_sends_advance_email(self):
        Subscription.objects.create(
            owner=self.user,
            platform='Spotify',
            anchor_date=date(2026, 4, 8),
            cycle_length=1,
            cycle_unit=Subscription.CycleUnit.MONTH,
            reminder_email='alerts@example.com',
            price='9.99',
            currency='USD',
        )

        call_command('send_subscription_reminders', date='2026-03-25', slot='morning')

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('14 day', mail.outbox[0].subject)
        self.assertIn('14-day reminder', mail.outbox[0].body)

    def test_send_subscription_reminders_sends_morning_and_night_in_repeat_window(self):
        Subscription.objects.create(
            owner=self.user,
            platform='Spotify',
            anchor_date=date(2026, 4, 8),
            cycle_length=1,
            cycle_unit=Subscription.CycleUnit.MONTH,
            reminder_email='alerts@example.com',
            price='9.99',
            currency='USD',
        )

        call_command('send_subscription_reminders', date='2026-04-01', slot='morning')
        call_command('send_subscription_reminders', date='2026-04-01', slot='night')

        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('7 days left', mail.outbox[0].subject)
        self.assertIn('Morning reminder', mail.outbox[0].body)
        self.assertIn('Night reminder', mail.outbox[1].body)
        self.assertEqual(mail.outbox[0].to, ['alerts@example.com'])

    def test_send_subscription_reminders_does_not_duplicate_same_slot(self):
        Subscription.objects.create(
            owner=self.user,
            platform='HTB',
            anchor_date=date(2026, 4, 8),
            cycle_length=1,
            cycle_unit=Subscription.CycleUnit.MONTH,
            reminder_email='alerts@example.com',
            price='9.99',
            currency='USD',
        )

        call_command('send_subscription_reminders', date='2026-04-01', slot='morning')
        call_command('send_subscription_reminders', date='2026-04-01', slot='morning')

        self.assertEqual(len(mail.outbox), 1)

    def test_send_test_email_command_sends_one_message(self):
        call_command('send_test_email', 'alerts@example.com')

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['alerts@example.com'])
        self.assertEqual(mail.outbox[0].from_email, 'alerts@example.com')
