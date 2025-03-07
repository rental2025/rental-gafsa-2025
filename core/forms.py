from django import forms
from .models import Reservation, Trip, Driver, Bus

class ReservationForm(forms.ModelForm):
    discount = forms.FloatField(label='الخصم (%)', min_value=0.0, max_value=100.0, initial=0.0)

    class Meta:
        model = Reservation
        fields = ['client', 'destination', 'start_date', 'end_date', 'discount']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

class DiscountForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['discount']

class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ['driver', 'bus']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['driver'].queryset = Driver.objects.filter(available=True)
        self.fields['bus'].queryset = Bus.objects.filter(available=True)