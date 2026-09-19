from django import forms
from .services.tilt import TiltService
from django.contrib.auth.models import User

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_password2(self):
        cd = self.cleaned_data
        if cd['password'] != cd['password2']:
            raise forms.ValidationError('Passwords don’t match.')
        return cd['password2']


class TempSetFermForm(forms.Form):
    temp = forms.FloatField(
        min_value=0,
        label="Temperature"
    )

class TempSetFreezeForm(forms.Form):
    temp = forms.FloatField(
        min_value=0,
        label="Temperature"
    )

class TiltDataSelectForm(forms.Form):
    name = forms.ChoiceField(
        choices=[],
        label="Select Batch"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        batch_names = TiltService.get_batch_names()

        self.fields["name"].choices = [
            (name, name)
            for name in batch_names
        ]

class CSVImportForm(forms.Form):
    csv_file = forms.FileField(
        label='Select CSV File',
        help_text='Upload a CSV file with columns: name, temperature, gravity, color, timestamp, comment'
    )

    def clean_csv_file(self):
        file = self.cleaned_data['csv_file']
        if not file.name.endswith('.csv'):
            raise forms.ValidationError('File must be a CSV')
        return file
