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

The project also reads a local `.env` file automatically. The fastest setup is:

```bash
cp .env.example .env
```

Then edit `.env` with your email credentials.

For Gmail:

- `DJANGO_EMAIL_HOST=smtp.gmail.com`
- `DJANGO_EMAIL_PORT=587`
- `DJANGO_EMAIL_USE_TLS=1`
- `DJANGO_EMAIL_HOST_USER=your_gmail_address`
- `DJANGO_EMAIL_HOST_PASSWORD=your_gmail_app_password`
- `DJANGO_DEFAULT_FROM_EMAIL=your_gmail_address`

Important:

- Gmail requires an App Password, not your normal account password.
- Reminder emails only send when a subscription is `1` to `7` days away from renewal.
- If your test subscription is outside that window, `send_subscription_reminders` will correctly send nothing.

To verify real delivery directly:

```bash
python3 manage.py send_test_email youraddress@example.com
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

Force a reminder test against a date inside the 7-day window:

```bash
python3 manage.py send_subscription_reminders --date 2026-04-01
```

Example cron entry to send reminders every morning at 8:00:

```cron
0 8 * * * cd /home/exploitforge/Documents/edu/reminder && /usr/bin/python3 manage.py send_subscription_reminders
```
