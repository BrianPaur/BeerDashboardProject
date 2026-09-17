from django import forms
from datetime import date, timedelta
from .models import FermentationDataTilt, GoogleSheetSourceData
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

class GoogleSheetURLForm(forms.ModelForm):
    class Meta:
        model = GoogleSheetSourceData
        fields = ['sourceURL','readable_name']
        widgets = {
            'readable_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Beer Name'}),
            'sourceURL': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Enter a readable name'}),

        }

class SelectGoogleSheetForm(forms.Form):
    google_sheet_url = forms.ModelChoiceField(
        queryset=GoogleSheetSourceData.objects.all(),
        empty_label="Select Data Sheet",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Select Data Sheet"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize the dropdown display to show readable_name
        self.fields['google_sheet_url'].queryset = GoogleSheetSourceData.objects.all()
        self.fields['google_sheet_url'].label_from_instance = lambda obj: f"{obj.readable_name}"

class GoogleSheetSourceDataForm(forms.ModelForm):
    class Meta:
        model = GoogleSheetSourceData
        fields = ['sourceURL', 'readable_name']

    def clean_sourceURL(self):
        source_url = self.cleaned_data['sourceURL']
        if GoogleSheetSourceData.objects.filter(sourceURL=source_url).exists():
            raise forms.ValidationError("This URL already exists in the database.")
        return source_url

    def clean_readable_name(self):
        readable_name = self.cleaned_data['readable_name']
        if GoogleSheetSourceData.objects.filter(readable_name=readable_name).exists():
            raise forms.ValidationError("This readable name already exists in the database.")
        return readable_name

class DateFilterForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.TextInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=False, widget=forms.TextInput(attrs={'type': 'date'}))
