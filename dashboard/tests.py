from django.test import TestCase, Client
from django.urls import reverse
from dashboard.forms import (
    DateForm, DateFilterForm, TempSetForm,
    GoogleSheetURLForm, SelectGoogleSheetForm, GoogleSheetSourceDataForm
)
from dashboard.models import TemperatureData, FermentationData, GoogleSheetSourceData
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


class GoogleSheetURLFormTest(TestCase):
    def test_google_sheet_url_form_valid(self):
        """Test if GoogleSheetURLForm is valid with correct data."""
        form = GoogleSheetURLForm(data={'sourceURL': 'https://example.com/sheet', 'readable_name': 'Test Sheet'})
        self.assertTrue(form.is_valid())

    def test_google_sheet_url_form_invalid(self):
        """Test if GoogleSheetURLForm is invalid with missing readable_name."""
        form = GoogleSheetURLForm(data={'sourceURL': 'https://example.com/sheet'})
        self.assertFalse(form.is_valid())


class SelectGoogleSheetFormTest(TestCase):
    def setUp(self):
        # Set up test data for GoogleSheetSourceData
        self.sheet1 = GoogleSheetSourceData.objects.create(
            sourceURL="https://example.com/sheet1", readable_name="Test Sheet 1"
        )
        self.sheet2 = GoogleSheetSourceData.objects.create(
            sourceURL="https://example.com/sheet2", readable_name="Test Sheet 2"
        )

    def test_select_google_sheet_form_valid(self):
        """Test if SelectGoogleSheetForm is valid with a selected option."""
        form = SelectGoogleSheetForm(data={'google_sheet_url': self.sheet1.pk})
        self.assertTrue(form.is_valid())

    def test_select_google_sheet_form_invalid(self):
        """Test if SelectGoogleSheetForm is invalid with no selection."""
        form = SelectGoogleSheetForm(data={})
        self.assertFalse(form.is_valid())


class GoogleSheetSourceDataFormTest(TestCase):
    def setUp(self):
        # Set up test data for GoogleSheetSourceData
        self.sheet = GoogleSheetSourceData.objects.create(
            sourceURL="https://example.com/sheet", readable_name="Test Sheet"
        )

    def test_google_sheet_source_data_form_valid(self):
        """Test if GoogleSheetSourceDataForm is valid with unique data."""
        form = GoogleSheetSourceDataForm(
            data={'sourceURL': 'https://example.com/another_sheet', 'readable_name': 'Another Test Sheet'}
        )
        self.assertTrue(form.is_valid())

    def test_google_sheet_source_data_form_duplicate_url(self):
        """Test if GoogleSheetSourceDataForm raises validation error for duplicate URL."""
        form = GoogleSheetSourceDataForm(
            data={'sourceURL': self.sheet.sourceURL, 'readable_name': 'Unique Name'}
        )
        self.assertFalse(form.is_valid())
        self.assertIn('This URL already exists in the database.', form.errors['sourceURL'])

    def test_google_sheet_source_data_form_duplicate_name(self):
        """Test if GoogleSheetSourceDataForm raises validation error for duplicate readable_name."""
        form = GoogleSheetSourceDataForm(
            data={'sourceURL': 'https://example.com/new_sheet', 'readable_name': self.sheet.readable_name}
        )
        self.assertFalse(form.is_valid())
        self.assertIn('This readable name already exists in the database.', form.errors['readable_name'])


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


class GoogleSheetSourceDataTest(TestCase):
    def setUp(self):
        self.sheet_data = GoogleSheetSourceData.objects.create(
            sourceURL="https://example.com/sheet1",
            readable_name="Test Sheet",
        )

    def test_google_sheet_source_data_creation(self):
        """Test if a GoogleSheetSourceData object is created successfully."""
        self.assertEqual(self.sheet_data.sourceURL, "https://example.com/sheet1")
        self.assertEqual(self.sheet_data.readable_name, "Test Sheet")

    def test_google_sheet_source_data_unique_constraints(self):
        """Test that duplicate sourceURL or readable_name raises an error."""
        with self.assertRaises(Exception):  # Use IntegrityError if not wrapped
            GoogleSheetSourceData.objects.create(
                sourceURL="https://example.com/sheet1",
                readable_name="Another Sheet",
            )
        with self.assertRaises(Exception):  # Use IntegrityError if not wrapped
            GoogleSheetSourceData.objects.create(
                sourceURL="https://example.com/sheet2",
                readable_name="Test Sheet",
            )

    def test_google_sheet_source_data_str_representation(self):
        """Test the __str__ method of GoogleSheetSourceData."""
        self.assertEqual(
            str(self.sheet_data),
            "Test Sheet (https://example.com/sheet1)",
        )

''' Tests for views.py '''

class ViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.temp_data = TemperatureData.objects.create(
            time_stamp=make_aware(datetime(2024, 12, 14, 10, 0, 0)),
            set_temp=72.5,
            current_temp=70.2,
        )
        self.fermentation_data = FermentationData.objects.create(
            time_stamp="2024-12-14 10:00:00",
            time_point=48.5,
            specific_gravity=1.05,
            temperature=68.2,
            color="Amber",
            beer="IPA",
        )
        self.google_sheet = GoogleSheetSourceData.objects.create(
            sourceURL="https://example.com/sheet1",
            readable_name="Test Sheet",
        )

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

    def test_update_google_sheet_url_view(self):
        """Test adding and updating Google Sheet URLs."""
        response = self.client.get(reverse('update_google_sheet_url'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/update_google_sheet_url.html')

        # Test adding a new Google Sheet
        response = self.client.post(
            reverse('update_google_sheet_url'),
            {'sourceURL': 'https://example.com/sheet2', 'readable_name': 'New Sheet'},
        )
        self.assertEqual(response.status_code, 302)  # Redirect after successful form submission
        self.assertTrue(GoogleSheetSourceData.objects.filter(readable_name="New Sheet").exists())

    def test_delete_google_sheet_view(self):
        """Test deleting a Google Sheet entry."""
        response = self.client.post(reverse('delete_google_sheet', args=[self.google_sheet.id]))
        self.assertEqual(response.status_code, 302)  # Redirect after deletion
        self.assertFalse(GoogleSheetSourceData.objects.filter(id=self.google_sheet.id).exists())

        # Verify success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Successfully deleted "Test Sheet".')

    # def test_update_google_sheet_url_view(self):
    #     """Test adding a Google Sheet URL with form validation."""
    #     response = self.client.post(
    #         reverse('update_google_sheet_url'),
    #         {'sourceURL': 'https://example.com/sheet3', 'readable_name': 'Another Sheet'},
    #     )
    #     self.assertEqual(response.status_code, 302)  # Redirect after successful form submission
    #     self.assertTrue(GoogleSheetSourceData.objects.filter(readable_name="Another Sheet").exists())
    #
    #     # Test duplicate entry handling
    #     response = self.client.post(
    #         reverse('update_google_sheet_url'),
    #         {'sourceURL': 'https://example.com/sheet3', 'readable_name': 'Another Sheet'},
    #     )
    #     self.assertEqual(response.status_code, 200)
    #     messages = list(get_messages(response.wsgi_request))
    #     self.assertTrue(any("Duplicate entry detected" in str(msg) for msg in messages))