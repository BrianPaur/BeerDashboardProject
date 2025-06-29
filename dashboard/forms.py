from django import forms
from datetime import date, timedelta
from tuya_connector import TuyaOpenAPI
# from dashboard.creds.creds import ACCESS_ID, ACCESS_KEY, ENDPOINT, DEVICE_ID,DEVICE_ID2
# import json
# with open('/etc/secrets/creds.json') as f:
#     creds = json.load(f)
#
# ACCESS_ID = creds['ACCESS_ID']
# ACCESS_KEY = creds['ACCESS_KEY']
# ENDPOINT = creds['ENDPOINT']
# DEVICE_ID = creds['DEVICE_ID']
# DEVICE_ID2 = creds['DEVICE_ID2']

import os
ACCESS_ID = os.getenv('ACCESS_ID')
ACCESS_KEY = os.getenv('ACCESS_KEY')
ENDPOINT = os.getenv('ENDPOINT')
DEVICE_ID = os.getenv('DEVICE_ID')
DEVICE_ID2 = os.getenv('DEVICE_ID2')

from django import forms
from .models import GoogleSheetSourceData, FermentationDataTilt
from django.contrib.auth.models import User

class DateForm(forms.Form):
    start = forms.DateField(widget=forms.DateInput(attrs={'type':'date'}))
    end = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

class DateFilterForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.TextInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=False, widget=forms.TextInput(attrs={'type': 'date'}))

class TempSetFermForm(forms.Form):
    temp = forms.FloatField(min_value=0, label="Temperature")
    openapi = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_KEY)
    openapi.connect()

    def set_temp(self, temp):
        commands = {"commands": [{"code": "temp_set", "value": int(temp * 10)}]}

        data_set_ferm = self.openapi.post(f"/v1.0/iot-03/devices/{DEVICE_ID}/commands", commands)

        # Return response or error details
        if 'success' in data_set_ferm and data_set_ferm['success']:
            return f"Temperature set to {temp}°F successfully."
        else:
            error_message = data_set_ferm.get('msg', 'Unknown error')
            return f"Failed to set temperature: {error_message}"
        
    def temp_reading(self):
        data_pull_ferm = self.openapi.get(F"/v1.0/iot-03/devices/{DEVICE_ID}/status")
        if data_pull_ferm['msg'] == 'No permissions. Your subscription to cloud development plan has expired.':
            return data_pull_ferm['msg']
        else:
            self.current_temp = data_pull_ferm['result'][3]['value'] / 10
            return self.current_temp


class TempSetFreezeForm(forms.Form):
    temp = forms.FloatField(min_value=0, label="Temperature")
    openapi = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_KEY)
    openapi.connect()

    def set_temp(self, temp):
        commands = {"commands": [{"code": "temp_set", "value": int(temp * 10)}]}

        data_set_freeze = self.openapi.post(f"/v1.0/iot-03/devices/{DEVICE_ID2}/commands", commands)

        # Return response or error details
        if 'success' in data_set_freeze and data_set_freeze['success']:
            return f"Temperature set to {temp}°F successfully."
        else:
            error_message = data_set_freeze.get('msg', 'Unknown error')
            return f"Failed to set temperature: {error_message}"

    def temp_reading(self):
        data_pull_freeze = self.openapi.get(F"/v1.0/iot-03/devices/{DEVICE_ID2}/status")
        if data_pull_freeze['msg'] == 'No permissions. Your subscription to cloud development plan has expired.':
            return data_pull_freeze['msg']
        else:
            self.current_temp = data_pull_freeze['result'][3]['value'] / 10
            return self.current_temp

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

class TiltDataSelectForm(forms.Form):
    name = forms.ChoiceField(choices=[], label='Select Batch')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate the dropdown with distinct batch names
        batch_names = FermentationDataTilt.objects.values_list('name', flat=True).distinct()
        self.fields['name'].choices = [(name, name) for name in batch_names if name]


# class DateFilterForm(forms.Form):
#     start_date = forms.DateField(
#         required=False,
#         widget=forms.TextInput(attrs={'type': 'date'})
#     )
#     end_date = forms.DateField(
#         required=False,
#         widget=forms.TextInput(attrs={'type': 'date'})
#     )
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # Set initial values for the date fields
#         self.fields['start_date'].initial = date.today() + timedelta(days=-1)
#         self.fields['end_date'].initial = date.today() + timedelta(days=1)
