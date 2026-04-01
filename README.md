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

## Automate daily reminders

You do not need to run `send_subscription_reminders` manually forever. The normal setup is to schedule it once per day. The Django web server does not need to be running for this command to work.

Recommended command:

```bash
/usr/bin/python3 /home/exploitforge/Documents/edu/reminder/manage.py send_subscription_reminders >> /home/exploitforge/Documents/edu/reminder/cron.log 2>&1
```

This version uses absolute paths and writes output to `cron.log` so failures are easier to debug.

### Linux

Open your user crontab:

```bash
crontab -e
```

Add this line to run reminders every day at `08:00`:

```cron
0 8 * * * /usr/bin/python3 /home/exploitforge/Documents/edu/reminder/manage.py send_subscription_reminders >> /home/exploitforge/Documents/edu/reminder/cron.log 2>&1
```

Save and exit, then verify it:

```bash
crontab -l
```

To watch cron output:

```bash
tail -f /home/exploitforge/Documents/edu/reminder/cron.log
```

### macOS

macOS also supports user crontabs, so the setup is the same:

```bash
crontab -e
```

Add:

```cron
0 8 * * * /usr/bin/python3 /home/exploitforge/Documents/edu/reminder/manage.py send_subscription_reminders >> /home/exploitforge/Documents/edu/reminder/cron.log 2>&1
```

Then confirm it was saved:

```bash
crontab -l
```

If your Python path is different on macOS, check it first:

```bash
which python3
```

and replace `/usr/bin/python3` with that result.

### Windows

Windows does not use `crontab`. Use Task Scheduler instead.

1. Open `Task Scheduler`.
2. Create a new basic task.
3. Set the trigger to `Daily` at `8:00 AM`.
4. Set the action to `Start a program`.
5. Use your Python executable as the program.
6. Pass the Django command as arguments.
7. Set the start-in directory to the project root.

Example values:

- Program/script:

```text
C:\Path\To\Python\python.exe
```

- Add arguments:

```text
manage.py send_subscription_reminders
```

- Start in:

```text
C:\Path\To\reminder
```

If you want a Linux-style `crontab` on Windows, the usual approach is to run the project inside WSL and configure cron inside that Linux environment, not in native Windows itself.

### Notes

- The machine must be on at `08:00` for the scheduled job to run.
- The project `.env` file is read automatically by the app, so you do not need to manually source it in cron.
- Internet access is required for SMTP delivery.
- Only subscriptions whose next billing date is `1` to `7` days away will send emails.

## Deploy instead of relying on a local machine

If you do not want to depend on `crontab` on your personal computer, or if your machine may be turned off at `08:00`, deploy the app to a server or platform that stays online.

This is the more reliable setup because:

- reminder emails can still be sent even when your laptop is off
- the dashboard stays available from anywhere
- the daily scheduler runs on infrastructure that is meant to stay up

Typical deployment shape:

- deploy the Django app to a Linux server, VPS, or platform service
- configure the same `.env` email variables on the server
- run migrations on the deployed app
- add one scheduled daily job on the server to run `send_subscription_reminders`

The command remains the same:

```bash
python3 manage.py send_subscription_reminders
```

What changes is where it runs: on the deployed machine instead of your local computer.

Examples of deployment approaches:

- A VPS such as Ubuntu on DigitalOcean, Hetzner, or AWS Lightsail with `gunicorn` and `nginx`
- A platform that supports scheduled jobs and background tasks
- Docker deployment on a server with a separate scheduler container or host cron

In all of those cases, the important point is the same:

- the web app serves the dashboard
- a daily scheduled job runs at `08:00`
- that job sends reminder emails automatically

If you deploy it, you usually do not need local cron anymore.
