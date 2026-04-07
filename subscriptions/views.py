from collections import defaultdict
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, TemplateView, UpdateView

from .forms import SignUpForm, SubscriptionForm
from .models import Subscription


class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        messages.success(self.request, 'Account created. You can log in now.')
        return super().form_valid(form)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'subscriptions/dashboard.html'

    @staticmethod
    def _format_currency_breakdown(active_subscriptions):
        spend_by_currency = defaultdict(
            lambda: {
                'active_count': 0,
                'monthly_total': Decimal('0.00'),
                'yearly_total': Decimal('0.00'),
                'upcoming_30_total': Decimal('0.00'),
                'upcoming_30_count': 0,
            }
        )

        for subscription in active_subscriptions:
            bucket = spend_by_currency[subscription.currency]
            bucket['active_count'] += 1
            bucket['monthly_total'] += subscription.estimated_monthly_cost
            bucket['yearly_total'] += subscription.estimated_yearly_cost

            if subscription.days_until_renewal is not None and 0 <= subscription.days_until_renewal <= 30:
                bucket['upcoming_30_total'] += subscription.price
                bucket['upcoming_30_count'] += 1

        return [
            {
                'currency': currency,
                'active_count': values['active_count'],
                'monthly_total': values['monthly_total'].quantize(Decimal('0.01')),
                'yearly_total': values['yearly_total'].quantize(Decimal('0.01')),
                'upcoming_30_total': values['upcoming_30_total'].quantize(Decimal('0.01')),
                'upcoming_30_count': values['upcoming_30_count'],
            }
            for currency, values in sorted(spend_by_currency.items())
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subscriptions = list(
            Subscription.objects.filter(owner=self.request.user)
            .prefetch_related('notification_history')
            .order_by('platform', 'plan_name')
        )

        active_subscriptions = [
            subscription
            for subscription in subscriptions
            if subscription.status == Subscription.Status.ACTIVE
        ]
        active_subscriptions.sort(
            key=lambda subscription: (
                subscription.days_until_renewal if subscription.days_until_renewal is not None else 10**9,
                subscription.platform.lower(),
            )
        )
        canceled_subscriptions = [
            subscription
            for subscription in subscriptions
            if subscription.status == Subscription.Status.CANCELED
        ]
        spend_breakdown = self._format_currency_breakdown(active_subscriptions)
        top_monthly_subscriptions = sorted(
            active_subscriptions,
            key=lambda subscription: (
                subscription.estimated_monthly_cost,
                subscription.price,
            ),
            reverse=True,
        )[:5]

        history_by_subscription = {
            subscription.pk: subscription.notification_history.all()[:3]
            for subscription in active_subscriptions
        }
        for subscription in active_subscriptions:
            subscription.history = history_by_subscription.get(subscription.pk, [])

        context.update(
            {
                'active_subscriptions': active_subscriptions,
                'canceled_subscriptions': canceled_subscriptions,
                'summary': {
                    'active_count': len(active_subscriptions),
                    'due_soon_count': sum(
                        1 for subscription in active_subscriptions if subscription.in_reminder_window
                    ),
                    'due_today_count': sum(
                        1 for subscription in active_subscriptions if subscription.is_due_today
                    ),
                    'canceled_count': len(canceled_subscriptions),
                },
                'spend_breakdown': spend_breakdown,
                'top_monthly_subscriptions': top_monthly_subscriptions,
                'history_by_subscription': history_by_subscription,
            }
        )
        return context


class SubscriptionCreateView(LoginRequiredMixin, CreateView):
    model = Subscription
    form_class = SubscriptionForm
    template_name = 'subscriptions/subscription_form.html'
    success_url = reverse_lazy('dashboard')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user_email'] = self.request.user.email
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, 'Subscription tracker created.')
        return super().form_valid(form)


class SubscriptionUpdateView(LoginRequiredMixin, UpdateView):
    model = Subscription
    form_class = SubscriptionForm
    template_name = 'subscriptions/subscription_form.html'
    success_url = reverse_lazy('dashboard')

    def get_queryset(self):
        return Subscription.objects.filter(owner=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user_email'] = self.request.user.email
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Subscription tracker updated.')
        return super().form_valid(form)


class SubscriptionStatusView(LoginRequiredMixin, View):
    status = None
    success_message = ''

    def post(self, request, *args, **kwargs):
        subscription = get_object_or_404(
            Subscription,
            pk=kwargs['pk'],
            owner=request.user,
        )
        subscription.status = self.status
        if self.status == Subscription.Status.ACTIVE:
            subscription.last_reminder_sent_on = None
            subscription.last_reminder_key = ''
        subscription.save(update_fields=['status', 'last_reminder_sent_on', 'last_reminder_key', 'updated_at'])
        messages.success(request, self.success_message)
        return HttpResponseRedirect(reverse('dashboard'))


class SubscriptionCancelView(SubscriptionStatusView):
    status = Subscription.Status.CANCELED
    success_message = 'Subscription tracking paused.'


class SubscriptionActivateView(SubscriptionStatusView):
    status = Subscription.Status.ACTIVE
    success_message = 'Subscription tracking reactivated.'
