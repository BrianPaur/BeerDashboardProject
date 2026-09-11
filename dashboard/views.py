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


from .models import TemperatureData,FermentationData, FermentationDataTilt
from .forms import (
    TempSetFermForm,
    TempSetFreezeForm,
    UserRegistrationForm,
    TiltDataSelectForm,
    CSVImportForm,
)

from .services.inkbird import InkbirdService
from dashboard.creds.creds import DEVICE_ID, DEVICE_ID2

import schedule
import time
import json

from datetime import datetime, timedelta

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from decimal import Decimal
import csv
from dateutil import parser

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
    ferm_inkbird = InkbirdService(DEVICE_ID)
    freeze_inkbird = InkbirdService(DEVICE_ID2)

    ferm_form = TempSetFermForm(
        request.POST or None,
        prefix="ferm"
    )

    freeze_form = TempSetFreezeForm(
        request.POST or None,
        prefix="freeze"
    )

    ferm_feedback = None
    freeze_feedback = None

    if request.method == "POST":

        if "ferm-temp-submit" in request.POST:
            if ferm_form.is_valid():

                try:
                    temperature = ferm_form.cleaned_data["temp"]

                    ferm_inkbird.set_temperature(temperature)

                    ferm_feedback = (
                        f"Temperature set to {temperature}°F successfully."
                    )

                except Exception as e:
                    ferm_feedback = f"Failed to set temperature: {e}"

        elif "freeze-temp-submit" in request.POST:
            if freeze_form.is_valid():

                try:
                    temperature = freeze_form.cleaned_data["temp"]

                    freeze_inkbird.set_temperature(temperature)

                    freeze_feedback = (
                        f"Temperature set to {temperature}°F successfully."
                    )

                except Exception as e:
                    freeze_feedback = f"Failed to set temperature: {e}"

    # Handle Tilt batch select
    tilt_form = TiltDataSelectForm(request.POST or None)

    tilt_data = FermentationDataTilt.objects.none()
    tilt_batch_name = None
    tilt_chart_html = None

    if request.method == "POST" and tilt_form.is_valid():

        tilt_batch_name = tilt_form.cleaned_data["name"]

        tilt_data = (
            FermentationDataTilt.objects
            .filter(name=tilt_batch_name)
            .order_by("-timestamp")
        )

        if tilt_data.exists():

            timestamps = [entry.timestamp for entry in tilt_data]
            temps = [entry.temperature for entry in tilt_data]
            gravities = [entry.gravity for entry in tilt_data]

            fig = make_subplots(
                specs=[[{"secondary_y": True}]]
            )

            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=temps,
                    name="Temperature (°F)",
                    line=dict(color="red")
                ),
                secondary_y=False,
            )

            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=gravities,
                    name="Gravity",
                    line=dict(color="blue")
                ),
                secondary_y=True,
            )

            fig.update_layout(
                title_text=f"Tilt Data for Batch: {tilt_batch_name}",
                xaxis_title="Timestamp",
                yaxis_title="Temperature (°F)",
                legend=dict(x=0.01, y=0.99),
                height=400,
                autosize=True,
                margin=dict(
                    l=60,
                    r=60,
                    t=80,
                    b=60
                )
            )

            fig.update_yaxes(
                title_text="Gravity",
                secondary_y=True
            )

            tilt_chart_html = fig.to_html(
                full_html=False,
                config={
                    "responsive": True,
                    "displayModeBar": True,
                    "displaylogo": False
                },
                div_id="tilt-chart"
            )

    return render(
        request,
        "dashboard/index.html",
        {
            "ferm_form": ferm_form,
            "freeze_form": freeze_form,
            "ferm_feedback": ferm_feedback,
            "freeze_feedback": freeze_feedback,
            "tilt_form": tilt_form,
            "tilt_data": tilt_data,
            "tilt_batch_name": tilt_batch_name,
            "tilt_chart_html": tilt_chart_html,
        }
    )

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
    batch_name = request.GET.get('batch', None)

    if batch_name:
        # Get the latest data for the specified batch
        latest = FermentationDataTilt.objects.filter(name=batch_name).order_by('-timestamp').first()
    else:
        # Get the latest data overall
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
        apparent_attenuation = 0

        if batch_data.exists() and batch_data.count() > 1:
            original_gravity = batch_data.first().gravity
            current_gravity = latest.gravity
            highest_gravity = batch_data.aggregate(Max('gravity'))
            lowest_gravity = batch_data.aggregate(Min('gravity'))
            # ABV calculation: (OG - FG) * 131.25
            abv = round((float(highest_gravity['gravity__max']) - float(current_gravity)) * 131.25, 2)

            # Calculate duration
            first_timestamp = timezone.localtime(batch_data.first().timestamp)
            duration_delta = local_time - first_timestamp

            # Format duration nicely (e.g., "5 days, 3 hours")
            days = duration_delta.days
            hours = duration_delta.seconds // 3600
            minutes = (duration_delta.seconds % 3600) // 60
            duration = f"{days}:{hours}:{minutes}"

            apparent_attenuation = round((((float(highest_gravity['gravity__max']) - float(current_gravity)) / (
                        float(highest_gravity['gravity__max']) - 1)) * 100), 2)

        return JsonResponse({
            'temperature': latest.temperature,
            'gravity': round(float(latest.gravity), 3),
            'timestamp': local_time.strftime('%m-%d-%Y %I:%M:%S %p'),
            'name': latest.name,
            'abv': f'{abv}%',
            'duration': duration,
            'highest_gravity': round(float(highest_gravity['gravity__max']), 3) if 'gravity__max' in highest_gravity and
                                                                                   highest_gravity[
                                                                                       'gravity__max'] else 0,
            'lowest_gravity': round(float(lowest_gravity['gravity__min']), 3) if 'gravity__min' in lowest_gravity and
                                                                                 lowest_gravity['gravity__min'] else 0,
            'apparent_attenuation': apparent_attenuation
        })
    else:
        return JsonResponse({'error': 'No data found'}, status=404)

@require_GET
@login_required
def calculate_slope(request):
    batch_name = request.GET.get('batch', None)

    if batch_name:
        # Get data for specified batch
        batch_data = FermentationDataTilt.objects.filter(name=batch_name).order_by('timestamp')
    else:
        # Get the latest batch name
        latest = FermentationDataTilt.objects.order_by('-timestamp').first()
        if not latest:
            return JsonResponse({'error': 'No data found'}, status=404)
        batch_name = latest.name
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
            if float(gravities[i + j]) >= float(max_gravity_so_far) - gravity_drop_threshold:
                is_sustained_drop = False
                break

        if is_sustained_drop:
            fermentation_start_index = i
            break

    # Find when fermentation stops (gravity stabilizes)
    fermentation_end_index = len(gravities) - 1  # Default to last reading
    stability_threshold = 0.001  # Gravity change threshold for "stable"
    consecutive_stable = 10  # Number of consecutive stable readings

    # Look backwards from the end for sustained stability
    for i in range(len(gravities) - consecutive_stable, fermentation_start_index, -1):
        is_stable = True
        # Check if the next consecutive_stable readings are all within threshold
        for j in range(consecutive_stable - 1):
            if i + j + 1 >= len(gravities):
                is_stable = False
                break
            gravity_change = abs(float(gravities[i + j]) - float(gravities[i + j + 1]))
            if gravity_change > stability_threshold:
                is_stable = False
                break

        if is_stable:
            fermentation_end_index = i
            break

    # Check if fermentation has started
    if fermentation_start_index == 0:
        if float(gravities[0]) - float(gravities[-1]) < gravity_drop_threshold:
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
    y_data = np.array([float(g) for g in active_gravities])

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

    # Calculate total fermentation time
    if fermentation_complete:
        duration_delta = timestamps[fermentation_end_index] - active_timestamps[0]
        days = duration_delta.days
        hours = duration_delta.seconds // 3600
        minutes = (duration_delta.seconds % 3600) // 60
        fermentation_duration = f"{days}:{hours}:{minutes}"
    else:
        fermentation_duration = "Still fermenting"

    return JsonResponse({
        'slope': slope_formatted,
        'slope_raw': float(slope),
        'fermentation_started_at': timezone.localtime(active_timestamps[0]).strftime('%m-%d-%Y %I:%M:%S %p'),
        'fermentation_ended_at': fermentation_end_time,
        'fermentation_complete': fermentation_complete,
        'fermentation_duration': fermentation_duration,
        'data_points_used': len(active_gravities)
    })

@require_GET
@login_required
def get_inkbird_freeze_data(request):
    try:
        inkbird = InkbirdService(DEVICE_ID2)

        freeze_current = inkbird.get_temperature()
        freeze_target = inkbird.get_target_temperature()

        return JsonResponse({
            "freeze_set_temp": freeze_target,
            "freeze_current_temp": freeze_current,
        })

    except Exception as e:
        logger.exception("Failed to retrieve keezer Inkbird data.")

        return JsonResponse(
            {"error": str(e)},
            status=500
        )

@require_GET
@login_required
def get_inkbird_ferm_data(request):
    try:
        inkbird = InkbirdService(DEVICE_ID)

        ferm_current = inkbird.get_temperature()
        ferm_target = inkbird.get_target_temperature()

        return JsonResponse({
            "ferm_set_temp": ferm_target,
            "ferm_current_temp": ferm_current,
        })

    except Exception as e:
        logger.exception("Failed to retrieve fermentation Inkbird data.")

        return JsonResponse(
            {"error": str(e)},
            status=500
        )

@login_required
def import_tilt_csv(request):
    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']

            # Decode the file
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)

            success_count = 0
            error_count = 0
            errors = []

            for row_num, row in enumerate(reader, start=2):  # Start at 2 because row 1 is header
                try:
                    # Handle both old format (name, temperature, gravity...) and new format (Beer, Temp, SG...)
                    name = row.get('Beer') or row.get('name', 'Unknown')
                    name = name.strip() if name else 'Unknown'

                    temperature = float(row.get('Temp') or row.get('temperature', 0))
                    gravity = float(row.get('SG') or row.get('gravity', 0))
                    color = row.get('Color') or row.get('color', '')
                    color = color.strip() if color else ''

                    # Handle timestamp - could be 'Time' or 'timestamp'
                    timestamp_str = row.get('Time') or row.get('timestamp', '')
                    timestamp_str = timestamp_str.strip() if timestamp_str else ''

                    comment = row.get('Comment') or row.get('comment', '')
                    comment = comment.strip() if comment else ''

                    # Parse timestamp - handles multiple formats including "1/15/25 1:37:45 PM"
                    if timestamp_str:
                        timestamp = parser.parse(timestamp_str)
                    else:
                        timestamp = timezone.now()

                    # Create the record
                    FermentationDataTilt.objects.create(
                        name=name,
                        temperature=temperature,
                        gravity=gravity,
                        color=color,
                        timestamp=timestamp,
                        comment=comment
                    )
                    success_count += 1

                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {row_num}: {str(e)}")

            # Show results
            if success_count > 0:
                messages.success(request, f'Successfully imported {success_count} records.')
            if error_count > 0:
                messages.warning(request, f'{error_count} rows had errors. See details below.')
                for error in errors[:10]:  # Show first 10 errors
                    messages.error(request, error)

            return redirect('import_tilt_csv')
    else:
        form = CSVImportForm()

    return render(request, 'dashboard/import_csv.html', {'form': form})
