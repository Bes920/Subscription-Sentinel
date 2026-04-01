from datetime import date

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from subscriptions.models import Subscription


class Command(BaseCommand):
    help = 'Send daily reminder emails for subscriptions that renew within 7 days.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            dest='run_date',
            help='Run reminders as if today were YYYY-MM-DD.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print matching reminders without sending email.',
        )

    def handle(self, *args, **options):
        run_date = (
            date.fromisoformat(options['run_date'])
            if options.get('run_date')
            else None
        )
        dry_run = options['dry_run']
        sent_count = 0

        subscriptions = Subscription.objects.filter(status=Subscription.Status.ACTIVE).select_related('owner')
        for subscription in subscriptions:
            current_date = run_date or timezone.localdate()
            if not subscription.should_send_reminder(on_date=current_date):
                continue

            billing_date = subscription.get_next_billing_date(reference_date=current_date)
            days_until = (billing_date - current_date).days
            subject = f'{subscription.display_name} renews in {days_until} day{"s" if days_until != 1 else ""}'
            message = (
                f'Your {subscription.display_name} subscription will renew on {billing_date:%B %d, %Y}.\n\n'
                f'Price: {subscription.currency} {subscription.price}\n'
                f'Billing cycle: {subscription.cycle_description}\n'
                f'Reminder email: {subscription.reminder_email}\n\n'
                f'Review it in the dashboard: {settings.APP_BASE_URL}\n'
            )

            if dry_run:
                self.stdout.write(f'[dry-run] {subscription.reminder_email}: {subject}')
            else:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[subscription.reminder_email],
                    fail_silently=False,
                )
                subscription.last_reminder_sent_on = current_date
                subscription.save(update_fields=['last_reminder_sent_on', 'updated_at'])

            sent_count += 1

        self.stdout.write(self.style.SUCCESS(f'Processed {sent_count} reminder(s).'))
