from tempfile import template

from django.http import HttpResponse
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.template import loader
from django.views.generic import ListView
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import logging
from django.contrib import messages
from django.db import IntegrityError
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required


from .models import TemperatureData,FermentationData, GoogleSheetSourceData, ProfileDataSelect, FermentationDataTilt
from .forms import DateForm, DateFilterForm, TempSetForm, GoogleSheetURLForm, SelectGoogleSheetForm, UserRegistrationForm
from .scheduler import data_update

import schedule
import time
import json

from datetime import datetime

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import gspread
import pandas as pd

logger = logging.getLogger(__name__)

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            login(request, user)  # Log the user in after registration
            return redirect('index')  # Redirect to the home page
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def index(request):
    google_sheet_data = GoogleSheetSourceData.objects.all()
    df_json = []
    df_json_sorted = []
    # Load TemperatureData from the database
    temperature_data = TemperatureData.objects.all()

    if request.method == 'POST':
        form = SelectGoogleSheetForm(request.POST)
        if form.is_valid():
            selected_sheet = form.cleaned_data['google_sheet_url']
            selected_url = selected_sheet.sourceURL
            gc = gspread.service_account(
                filename='/etc/secrets/credentials.json')
            sh = gc.open_by_url(selected_url)
            worksheet = sh.worksheet("Data")
            list_of_lists = worksheet.get('A2:F2972')
            df = pd.DataFrame(list_of_lists)
            df.columns = ['Timestamp', 'Timepoint', 'SG', 'Temp', 'Color', 'Beer']
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])

            # Handle DateFilterForm
            date_form = DateFilterForm(request.GET)
            if date_form.is_valid():
                start_date = date_form.cleaned_data.get('start_date')
                end_date = date_form.cleaned_data.get('end_date')

                if start_date:
                    temperature_data = temperature_data.filter(time_stamp__gte=start_date)
                    df = df[df['Timestamp'] >= pd.to_datetime(start_date)]
                if end_date:
                    temperature_data = temperature_data.filter(time_stamp__lte=end_date)
                    df = df[df['Timestamp'] <= pd.to_datetime(end_date)]

            # Prepare data for charts
            data = temperature_data.order_by('time_stamp')
            latest_temp = temperature_data.order_by('-time_stamp').values_list('current_temp', flat=True).first()
            df['Timestamp'] = pd.to_datetime(df['Timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            df_sort = df.sort_values('Timestamp', ascending=False)
            df_json_sorted = df_sort.to_dict(orient='records')
            df_json = df.to_dict(orient='records')
        else:
            # Handle DateFilterForm
            date_form = DateFilterForm(request.GET)
            data = temperature_data.order_by('time_stamp')
            latest_temp = temperature_data.order_by('-time_stamp').values_list('current_temp', flat=True).first()
            df_json = []
            df_json_sorted = []
    else:
        # Load TemperatureData from the database
        temperature_data = TemperatureData.objects.all()
        # Handle DateFilterForm
        date_form = DateFilterForm(request.GET)
        data = temperature_data.order_by('time_stamp')
        latest_temp = temperature_data.order_by('-time_stamp').values_list('current_temp', flat=True).first()
        form = SelectGoogleSheetForm()



    # Handle TempSetForm
    temp_form = TempSetForm(request.POST or None)
    temp_feedback = None
    if request.method == "POST" and temp_form.is_valid():
        temp_feedback = temp_form.set_temp(temp_form.cleaned_data['temp'])

    # Render the page
    return render(request, 'dashboard/index.html', {
        'data': data,
        'df_json': df_json,
        'df_json_sorted':df_json_sorted,
        'date_form': date_form,
        'temp_form': temp_form,
        'temp_feedback': temp_feedback,
        'latest_temp':latest_temp,
        'form': form,
    })

@login_required
def historical_data(request):
    start = request.GET.get('start')
    end = request.GET.get('end')

    all_data = TemperatureData.objects.order_by("-time_stamp")

    if start:
        all_data = all_data.filter(time_stamp__gte=start)
    if end:
        all_data = all_data.filter(time_stamp__lte=end)

    fig = px.line(
        x=[c.time_stamp for c in all_data],
        y=[[c.current_temp for c in all_data],[c.set_temp for c in all_data]],
        title="Historical Temperature",
        labels={'x':"Time Stamp",'y':"Temperature"}
    )

    fig.update_layout(title={
        'font_size':22,
        'xanchor':'center',
        'x':0.5
    })

    chart = fig.to_html()

    context = {"chart": chart, 'form':DateForm(), 'all_data':all_data }
    return render(request, "dashboard/historical.html", context)

@login_required
def dashboard_view(request):
    # Get filter parameters from the request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Filter data based on the provided dates
    temperature_data = TemperatureData.objects.all()

    if start_date:
        data = temperature_data.filter(time_stamp__gte=start_date)
    if end_date:
        data = temperature_data.filter(time_stamp__lte=end_date)

    data = temperature_data.order_by('time_stamp')  # Ensure data is ordered by timestamp

    fermentation_data = FermentationData.objects.all()

    return render(request, 'dashboard/dashboard_view.html', {
        'data': data,
        'fermentation_data': fermentation_data,
        'request': request,  # Pass request object to use GET parameters in the form
    })

@login_required
def dashboard_view_dark(request):
    # Get filter parameters from the request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Filter data based on the provided dates
    data = TemperatureData.objects.all()
    if start_date:
        data = data.filter(time_stamp__gte=start_date)
    if end_date:
        data = data.filter(time_stamp__lte=end_date)

    data = data.order_by('time_stamp')  # Ensure data is ordered by timestamp

    return render(request, 'dashboard/dashboard_view_dark.html', {
        'data': data,
        'request': request,  # Pass request object to use GET parameters in the form
    })

@login_required
def update_google_sheet_url(request, pk=None):
    if pk:
        # If a primary key is provided, retrieve the existing record
        sheet_instance = get_object_or_404(GoogleSheetSourceData, pk=pk)
    else:
        # Otherwise, create a new instance
        sheet_instance = None

    if request.method == 'POST':
        form = GoogleSheetURLForm(request.POST, instance=sheet_instance)
        if form.is_valid():
            form.save()  # Save the changes or create a new entry
            return redirect('update_google_sheet_url')  # Redirect to the same page after saving
    else:
        form = GoogleSheetURLForm(instance=sheet_instance)

    # Fetch all entries for display
    all_sheets = GoogleSheetSourceData.objects.all()

    return render(request, 'dashboard/update_google_sheet_url.html', {
        'form': form,
        'all_sheets': all_sheets,
    })

@login_required
def delete_google_sheet(request, pk):
    google_sheet = get_object_or_404(GoogleSheetSourceData, pk=pk)

    if request.method == "POST":
        readable_name = google_sheet.readable_name
        google_sheet.delete()
        messages.success(request, f'Successfully deleted "{readable_name}".')
        return redirect('update_google_sheet_url')  # Redirect to the index page or another relevant page.

    return render(request, 'dashboard/delete_google_sheet.html', {'google_sheet': google_sheet})

@login_required
def add_google_sheet_url(request):
    if request.method == 'POST':
        form = GoogleSheetSourceDataForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Google Sheet added successfully.")
                return redirect('index')
            except IntegrityError:
                messages.error(request, "Duplicate entry detected. Please check your inputs.")
        else:
            messages.error(request, "Failed to add Google Sheet. Please correct the errors below.")
    else:
        form = GoogleSheetSourceDataForm()

    return render(request, 'dashboard/add_google_sheet.html', {'form': form})

@csrf_exempt
def receive_tilt_data(request):
    logger.info("Tilt Pi request received")
    logger.info("Method: %s", request.method)
    logger.info("Headers: %s", dict(request.headers))

    if request.method == 'POST':
        try:
            # If JSON data
            if request.content_type == "application/json":
                raw = request.body.decode('utf-8')
                logger.info("Raw JSON body: %s", raw)
                data = json.loads(raw)
            else:
                # If form-encoded (likely what Tilt Pi is sending)
                data = request.POST
                logger.info("Form POST data: %s", dict(data))

            # Extract data safely
            name = data.get('Beer', 'Unknown')
            temperature = float(data.get('Temp', 0))
            gravity = float(data.get('SG', 0))
            color = data.get('Color', 'Unknown')
            time_str = data.get('Time')

            if not time_str:
                logger.info("Form POST keys: %s", list(data.keys()))
                logger.info("Form POST data: %s", dict(data))
                return JsonResponse({'status': 'error', 'message': 'Missing Time field'}, status=400)

            timestamp = parser.parse(time_str)

            # Save to DB
            from .models import FermentationDataTilt
            FermentationDataTilt.objects.create(
                name=name,
                temperature=temperature,
                gravity=gravity,
                color=color,
                timestamp=timestamp
            )

            logger.info("Data saved successfully")
            return JsonResponse({'status': 'success'})

        except Exception as e:
            logger.exception("Unexpected error in tilt-data view")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'invalid method'}, status=405)

@csrf_exempt
def tilt_debug(request):
    logger.info("---- TILT DEBUG ENDPOINT ----")
    logger.info("Method: %s", request.method)
    logger.info("Headers: %s", dict(request.headers))
    logger.info("Body: %s", request.body.decode('utf-8'))

    return JsonResponse({'status': 'received', 'method': request.method})