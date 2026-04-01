# Subscription Sentinel

Subscription Sentinel is a small Django app for tracking recurring plans and warning you before they renew. It supports:

- login-protected dashboards
- multiple tracked subscriptions per account
- weekly, monthly, yearly, and custom billing cycles
- price and currency storage
- daily email reminders during the final 7 days before renewal
- paused reminders when a subscription is marked canceled

## Local setup

1. Create and activate a virtual environment if you want one.
2. Run migrations:

```bash
python3 manage.py migrate
```

3. Run the server:

```bash
python3 manage.py runserver
```

Open `http://127.0.0.1:8000/` and create an account from the signup page.

If you prefer admin access, you can still create a superuser:

```bash
python3 manage.py createsuperuser
```

## Email settings

By default, reminder emails print to the terminal using Django's console email backend. For real email delivery, set environment variables before starting the app:

```bash
export DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
export DJANGO_EMAIL_HOST=smtp.example.com
export DJANGO_EMAIL_PORT=587
export DJANGO_EMAIL_HOST_USER=your-user
export DJANGO_EMAIL_HOST_PASSWORD=your-password
export DJANGO_EMAIL_USE_TLS=1
export DJANGO_DEFAULT_FROM_EMAIL=alerts@example.com
export APP_BASE_URL=https://your-domain.example
```

## Sending reminders

Run the reminder command manually:

```bash
python3 manage.py send_subscription_reminders
```

Test it without sending real email:

```bash
python3 manage.py send_subscription_reminders --dry-run
```

Example cron entry to send reminders every morning at 8:00:

```cron
0 8 * * * cd /home/exploitforge/Documents/edu/reminder && /usr/bin/python3 manage.py send_subscription_reminders
```
