from django.test import TestCase, Client
from django.urls import reverse
from dashboard.forms import (
    DateForm, DateFilterForm, TempSetForm
)
from dashboard.models import TemperatureData, FermentationData
from datetime import date, datetime
from django.utils.timezone import make_aware
from django.contrib.messages import get_messages


''' Tests for forms.py '''
class DateFormTest(TestCase):
    def test_date_form_valid(self):
        """Test if DateForm is valid with correct data."""
        form = DateForm(data={'start': '2024-12-01', 'end': '2024-12-31'})
        self.assertTrue(form.is_valid())

    def test_date_form_invalid(self):
        """Test if DateForm is invalid with incorrect data."""
        form = DateForm(data={'start': 'invalid-date', 'end': '2024-12-31'})
        self.assertFalse(form.is_valid())


class DateFilterFormTest(TestCase):
    def test_date_filter_form_valid(self):
        """Test if DateFilterForm is valid with optional data."""
        form = DateFilterForm(data={'start_date': '2024-12-01', 'end_date': '2024-12-31'})
        self.assertTrue(form.is_valid())

    def test_date_filter_form_empty(self):
        """Test if DateFilterForm is valid with no data."""
        form = DateFilterForm(data={})
        self.assertTrue(form.is_valid())


class TempSetFormTest(TestCase):
    def test_temp_set_form_valid(self):
        """Test if TempSetForm is valid with a valid temperature."""
        form = TempSetForm(data={'temp': 20})
        self.assertTrue(form.is_valid())

    def test_temp_set_form_invalid(self):
        """Test if TempSetForm is invalid with a negative temperature."""
        form = TempSetForm(data={'temp': -5})
        self.assertFalse(form.is_valid())

''' Tests for models.py '''

class TemperatureDataTest(TestCase):
    def setUp(self):
        self.temp_data = TemperatureData.objects.create(
            time_stamp=datetime(2024, 12, 14, 10, 0, 0),
            set_temp=72.50,
            current_temp=70.25,
        )

    def test_temperature_data_creation(self):
        """Test if a TemperatureData object is created successfully."""
        self.assertEqual(self.temp_data.time_stamp, datetime(2024, 12, 14, 10, 0, 0))
        self.assertEqual(self.temp_data.set_temp, 72.50)
        self.assertEqual(self.temp_data.current_temp, 70.25)


class FermentationDataTest(TestCase):
    def setUp(self):
        self.fermentation_data = FermentationData.objects.create(
            time_stamp="2024-12-14 10:00:00",
            time_point=48.5,
            specific_gravity=1.05,
            temperature=68.2,
            color="Amber",
            beer="IPA",
        )

    def test_fermentation_data_creation(self):
        """Test if a FermentationData object is created successfully."""
        self.assertEqual(self.fermentation_data.time_stamp, "2024-12-14 10:00:00")
        self.assertEqual(self.fermentation_data.time_point, 48.5)
        self.assertEqual(self.fermentation_data.specific_gravity, 1.05)
        self.assertEqual(self.fermentation_data.temperature, 68.2)
        self.assertEqual(self.fermentation_data.color, "Amber")
        self.assertEqual(self.fermentation_data.beer, "IPA")

    def test_fermentation_data_str_representation(self):
        """Test the __str__ method of FermentationData."""
        self.assertEqual(str(self.fermentation_data), "IPA")

''' Tests for views.py '''


    def test_index_view(self):
        """Test the index view renders successfully with the correct template."""
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/index.html')
        self.assertIn('df_json', response.context)
        self.assertIn('temp_form', response.context)

    def test_dashboard_view(self):
        """Test the dashboard view filters temperature data correctly."""
        response = self.client.get(
            reverse('dashboard_view'), {'start_date': '2024-12-13', 'end_date': '2024-12-14'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/dashboard_view.html')
        self.assertIn('data', response.context)
        self.assertIn('fermentation_data', response.context)

    def test_dashboard_view_dark(self):
        """Test the dark mode dashboard view renders successfully."""
        response = self.client.get(reverse('dashboard_view_dark'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/dashboard_view_dark.html')
