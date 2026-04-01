from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Send a single test email to verify SMTP delivery.'

    def add_arguments(self, parser):
        parser.add_argument(
            'recipient',
            help='Email address that should receive the test message.',
        )

    def handle(self, *args, **options):
        recipient = options['recipient']
        send_mail(
            subject='Subscription Sentinel test email',
            message=(
                'This is a test email from Subscription Sentinel.\n\n'
                f'Backend: {settings.EMAIL_BACKEND}\n'
                f'Host: {settings.EMAIL_HOST}\n'
                f'From: {settings.DEFAULT_FROM_EMAIL}\n'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        self.stdout.write(self.style.SUCCESS(f'Test email sent to {recipient}.'))
