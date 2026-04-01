from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Subscription


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('username', 'email')


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = [
            'platform',
            'plan_name',
            'anchor_date',
            'cycle_length',
            'cycle_unit',
            'price',
            'currency',
            'reminder_email',
            'notes',
        ]
        widgets = {
            'anchor_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, user_email='', **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['platform'].widget.attrs['placeholder'] = 'Spotify'
        self.fields['plan_name'].widget.attrs['placeholder'] = 'Premium Duo'
        self.fields['cycle_length'].widget.attrs['min'] = 1
        self.fields['price'].widget.attrs['min'] = 0
        self.fields['price'].widget.attrs['step'] = '0.01'
        self.fields['currency'].widget.attrs['placeholder'] = 'USD'
        self.fields['reminder_email'].widget.attrs['placeholder'] = user_email or 'you@example.com'
        if user_email and not self.initial.get('reminder_email'):
            self.fields['reminder_email'].initial = user_email

    def clean_currency(self):
        return self.cleaned_data['currency'].upper()
