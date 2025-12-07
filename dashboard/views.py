from tempfile import template

from django.http import HttpResponse
from django.utils import timezone
from django.utils.timezone import now
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
from django.views.decorators.http import require_GET
from django.db.models import Min, Max


from .models import TemperatureData,FermentationData, GoogleSheetSourceData, ProfileDataSelect, FermentationDataTilt
from .forms import DateForm, DateFilterForm, TempSetFermForm, TempSetFreezeForm, GoogleSheetURLForm, SelectGoogleSheetForm, UserRegistrationForm, TiltDataSelectForm , TempGetFreezeForm, TempGetFermForm


import schedule
import time
import json

from datetime import datetime, timedelta

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

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

    # Handle TempSetForm
    ferm_form = TempSetFermForm(request.POST or None, prefix="ferm")
    freeze_form = TempSetFreezeForm(request.POST or None, prefix="freeze")

    ferm_feedback = None
    freeze_feedback = None

    if request.method == "POST":
        if 'ferm-temp-submit' in request.POST and ferm_form.is_valid():
            ferm_feedback = ferm_form.set_temp(ferm_form.cleaned_data['temp'])
        elif 'freeze-temp-submit' in request.POST and freeze_form.is_valid():
            freeze_feedback = freeze_form.set_temp(freeze_form.cleaned_data['temp'])

    # Handle getting current temps

    # current_ferm_temp = TempGetFermForm(request.GET or None, prefix="c_ferm")
    # current_freeze_temp = TempGetFreezeForm(request.GET or None, prefix="c_freeze")

    # Handle tilt batch select
    tilt_form = TiltDataSelectForm(request.POST or None)
    tilt_data = FermentationDataTilt.objects.none()  # Default to empty queryset
    tilt_batch_name = None
    tilt_chart_html = None

    if request.method == "POST" and tilt_form.is_valid():
        tilt_batch_name = tilt_form.cleaned_data['name']
        tilt_data = FermentationDataTilt.objects.filter(name=tilt_batch_name).order_by('-timestamp')

        if tilt_data.exists():
            timestamps = [entry.timestamp for entry in tilt_data]
            temps = [entry.temperature for entry in tilt_data]
            gravities = [entry.gravity for entry in tilt_data]

            fig = make_subplots(specs=[[{"secondary_y": True}]])

            fig.add_trace(
                go.Scatter(x=timestamps, y=temps, name="Temperature (°F)", line=dict(color='red')),
                secondary_y=False,
            )
            fig.add_trace(
                go.Scatter(x=timestamps, y=gravities, name="Gravity", line=dict(color='blue')),
                secondary_y=True,
            )

            fig.update_layout(
                title_text=f"Tilt Data for Batch: {tilt_batch_name}",
                xaxis_title="Timestamp",
                yaxis_title="Temperature (°F)",
                legend=dict(x=0.70, y=1.00),
                height=400
            )

            fig.update_yaxes(title_text="Gravity", secondary_y=True)

            tilt_chart_html = fig.to_html(full_html=False)

    # Render the page
    return render(request, 'dashboard/index.html', {
        'ferm_form': ferm_form,
        'freeze_form': freeze_form,
        'ferm_feedback': ferm_feedback,
        'freeze_feedback': freeze_feedback,
        'tilt_form': tilt_form,
        'tilt_data': tilt_data,
        'tilt_batch_name': tilt_batch_name,
        'tilt_chart_html': tilt_chart_html,
        # 'current_ferm_temp':current_ferm_temp,
        # 'current_freeze_temp':current_freeze_temp,
    })

@login_required
def google_sheet_dashboard(request):
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
    temp_form = TempSetFermForm(request.POST or None)
    temp_feedback = None
    if request.method == "POST" and temp_form.is_valid():
        temp_feedback = temp_form.set_temp(temp_form.cleaned_data['temp'])

    # Render the page
    return render(request, 'dashboard/google_sheets_dashboard.html', {
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
                logger.info("Form POST keys: %s", list(data.keys()))
                logger.info("Form POST data: %s", dict(data))

            # Extract data safely
            name = data.get('Beer', 'Unknown')
            temperature = float(data.get('Temp', 0))
            gravity = float(data.get('SG', 0))
            color = data.get('Color', 'Unknown')
            # time_str = data.get('Time') or data.get('Date')
            time_str = data.get('formatteddate')
            comment = data.get('comment','Unknown')

            timestamp = parser.parse(time_str) if time_str else now()

            # Save to DB
            from .models import FermentationDataTilt
            FermentationDataTilt.objects.create(
                name=name,
                temperature=temperature,
                gravity=gravity,
                color=color,
                timestamp=timestamp,
                comment=comment
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

@require_GET
@login_required
def get_latest_tilt_data(request):
    latest = FermentationDataTilt.objects.order_by('-timestamp').first()
    if latest:

        # Use Django's timezone handling instead of manual adjustment
        local_time = timezone.localtime(latest.timestamp)

        # Get the batch name to find original and current gravity
        batch_name = latest.name

        # Get first (original) and last (current) gravity for this batch
        batch_data = FermentationDataTilt.objects.filter(name=batch_name).order_by('timestamp')

        abv = 0  # Default value
        duration = "0 days"  # Default value
        if batch_data.exists() and batch_data.count() > 1:
            original_gravity = batch_data.first().gravity
            current_gravity = latest.gravity
            highest_gravity = FermentationDataTilt.objects.aggregate(Max('gravity'))
            lowest_gravity = FermentationDataTilt.objects.aggregate(Min('gravity'))
            # ABV calculation: (OG - FG) * 131.25
            abv = round((original_gravity - current_gravity) * 131.25, 2)

            # Calculate duration
            first_timestamp = timezone.localtime(batch_data.first().timestamp)
            duration_delta = local_time - first_timestamp

            # Format duration nicely (e.g., "5 days, 3 hours")
            days = duration_delta.days
            hours = duration_delta.seconds // 3600
            minutes = (duration_delta.seconds % 3600) // 60
            duration = f"{days}:{hours}:{minutes}"

            apparent_attenuation = round((((original_gravity-current_gravity)/(original_gravity-1))*100),2)

        return JsonResponse({
            'temperature': latest.temperature,
            'gravity': latest.gravity,
            'timestamp': local_time.strftime('%m-%d-%Y %I:%M:%S %p'),
            'name': latest.name,
            'abv': f'{abv}%',
            'duration': duration,
            'highest_gravity': highest_gravity['gravity__max'],
            'lowest_gravity': lowest_gravity['gravity__min'],
            'apparent_attenuation':apparent_attenuation
        })
    else:
        return JsonResponse({'error': 'No data found'}, status=404)

@require_GET
@login_required
def calculate_slope(request):
    # Get the latest batch name
    latest = FermentationDataTilt.objects.order_by('-timestamp').first()
    if not latest:
        return JsonResponse({'error': 'No data found'}, status=404)

    batch_name = latest.name

    # Get data for the current batch only
    batch_data = FermentationDataTilt.objects.filter(name=batch_name).order_by('timestamp')

    if batch_data.count() < 2:
        return JsonResponse({'error': 'Not enough data points'}, status=404)

    # Get all data
    timestamps = list(batch_data.values_list('timestamp', flat=True))
    gravities = list(batch_data.values_list('gravity', flat=True))

    # Find when fermentation actually starts with sustained drop
    fermentation_start_index = 0
    gravity_drop_threshold = 0.002  # Minimum drop to consider
    consecutive_drops = 5  # Number of consecutive readings showing decline

    # Look for sustained fermentation activity
    for i in range(len(gravities) - consecutive_drops):
        # Get the max gravity from the beginning up to this point
        max_gravity_so_far = max(gravities[:i + 1])

        # Check if we have consecutive drops from this point
        is_sustained_drop = True
        for j in range(consecutive_drops):
            if i + j >= len(gravities):
                is_sustained_drop = False
                break
            # Check if this reading and the next few are consistently lower
            if gravities[i + j] >= max_gravity_so_far - gravity_drop_threshold:
                is_sustained_drop = False
                break

        if is_sustained_drop:
            fermentation_start_index = i
            break

    # Find when fermentation stops (gravity stabilizes)
    fermentation_end_index = len(gravities) - 1  # Default to last reading
    stability_threshold = 0.001  # Gravity change threshold for "stable"
    consecutive_stable = 5  # Number of consecutive stable readings

    # Look backwards from the end for sustained stability
    for i in range(len(gravities) - consecutive_stable, fermentation_start_index, -1):
        is_stable = True
        # Check if the next consecutive_stable readings are all within threshold
        for j in range(consecutive_stable - 1):
            if i + j + 1 >= len(gravities):
                is_stable = False
                break
            gravity_change = abs(gravities[i + j] - gravities[i + j + 1])
            if gravity_change > stability_threshold:
                is_stable = False
                break

        if is_stable:
            fermentation_end_index = i
            break

    # Check if fermentation has started
    if fermentation_start_index == 0:
        if gravities[0] - gravities[-1] < gravity_drop_threshold:
            return JsonResponse({
                'slope': 'Fermentation not started',
                'slope_raw': 0
            })

    # Use data from fermentation start to end
    active_timestamps = timestamps[fermentation_start_index:fermentation_end_index + 1]
    active_gravities = gravities[fermentation_start_index:fermentation_end_index + 1]

    if len(active_timestamps) < 2:
        return JsonResponse({'error': 'Not enough active fermentation data'}, status=404)

    # Convert timestamps to DAYS since fermentation start
    first_time = active_timestamps[0]
    x_data = np.array([(t - first_time).total_seconds() / 86400 for t in active_timestamps])
    y_data = np.array(active_gravities)

    # Calculate means
    x_mean = np.mean(x_data)
    y_mean = np.mean(y_data)

    # Calculate slope
    numerator = np.sum((x_data - x_mean) * (y_data - y_mean))
    denominator = np.sum((x_data - x_mean) ** 2)

    if denominator == 0:
        return JsonResponse({'error': 'Cannot calculate slope'}, status=404)

    slope = numerator / denominator

    # Format slope nicely (gravity points per day)
    slope_formatted = f"{slope:.4f} points/day"

    # Check if fermentation is complete (end_index is not the last reading)
    fermentation_complete = fermentation_end_index < len(gravities) - 1
    fermentation_end_time = timezone.localtime(timestamps[fermentation_end_index]).strftime(
        '%m-%d-%Y %I:%M:%S %p') if fermentation_complete else "Still fermenting"

    return JsonResponse({
        'slope': slope_formatted,
        'slope_raw': float(slope),
        'fermentation_started_at': timezone.localtime(active_timestamps[0]).strftime('%m-%d-%Y %I:%M:%S %p'),
        'fermentation_ended_at': fermentation_end_time,
        'fermentation_complete': fermentation_complete,
        'data_points_used': len(active_gravities)
    })
@require_GET
@login_required
def get_inkbird_freeze_data(request):
    freeze_form = TempGetFreezeForm()
    freeze_current = freeze_form.temp_reading()
    freeze_target = freeze_form.set_temp()

    if freeze_form:
        return JsonResponse({
            'freeze_set_temp': freeze_target,
            'freeze_current_temp': freeze_current,
        })
    else:
        return JsonResponse({'error': 'No data found'}, status=404)

@require_GET
@login_required
def get_inkbird_ferm_data(request):
    ferm_form = TempGetFermForm()
    ferm_current = ferm_form.temp_reading()
    ferm_target = ferm_form.set_temp()

    if ferm_form:
        return JsonResponse({
            'ferm_set_temp': ferm_target,
            'ferm_current_temp': ferm_current,
        })
    else:
        return JsonResponse({'error': 'No data found'}, status=404)
