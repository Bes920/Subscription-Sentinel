from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
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
        self.assertTrue(subscription.should_send_reminder(run_date))

        subscription.last_reminder_sent_on = run_date
        self.assertFalse(subscription.should_send_reminder(run_date))

        subscription.status = Subscription.Status.CANCELED
        self.assertFalse(subscription.should_send_reminder(run_date))


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

# Create your tests here.
