from django.urls import path

from .views import (
    DashboardView,
    SubscriptionActivateView,
    SubscriptionCancelView,
    SubscriptionCreateView,
    SubscriptionUpdateView,
)

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('subscriptions/new/', SubscriptionCreateView.as_view(), name='subscription-create'),
    path('subscriptions/<int:pk>/edit/', SubscriptionUpdateView.as_view(), name='subscription-update'),
    path('subscriptions/<int:pk>/cancel/', SubscriptionCancelView.as_view(), name='subscription-cancel'),
    path('subscriptions/<int:pk>/activate/', SubscriptionActivateView.as_view(), name='subscription-activate'),
]
