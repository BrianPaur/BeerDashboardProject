from django.utils import timezone
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import logging
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.db.models import Min, Max


from .models import (
    FermentationDataTilt,
    )

from .forms import (
    TempSetFermForm,
    TempSetFreezeForm,
    UserRegistrationForm,
    TiltDataSelectForm,
    CSVImportForm,
)

from .services.inkbird import InkbirdService
from .services.fermentation import FermentationService
from .services.tilt import TiltService
from .services.imports import ImportService
from dashboard.creds.creds import DEVICE_ID, DEVICE_ID2

import json

import plotly.graph_objects as go
from plotly.subplots import make_subplots

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

    if request.method != "POST":
        return JsonResponse(
            {"status": "invalid method"},
            status=405
        )

    try:
        if request.content_type == "application/json":
            data = json.loads(request.body.decode("utf-8"))
        else:
            data = request.POST

        name = data.get("Beer", "Unknown")
        temperature = float(data.get("Temp", 0))
        gravity = float(data.get("SG", 0))
        color = data.get("Color", "")
        comment = data.get("comment", "")

        timestamp = TiltService.parse_timestamp(
            data.get("formatteddate")
        )

        TiltService.save_reading(
            name=name,
            temperature=temperature,
            gravity=gravity,
            color=color,
            timestamp=timestamp,
            comment=comment,
        )

        logger.info("Tilt data saved successfully")

        return JsonResponse({
            "status": "success"
        })

    except Exception as e:
        logger.exception("Unexpected error in tilt-data view")

        return JsonResponse(
            {
                "status": "error",
                "message": str(e)
            },
            status=400
        )

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
        latest = TiltService.get_latest_reading(batch_name)
    else:
        # Get the latest data overall
        latest = TiltService.get_latest_reading()

    if latest:
        # Use Django's timezone handling instead of manual adjustment
        local_time = timezone.localtime(latest.timestamp)

        # Get the batch name to find original and current gravity
        batch_name = latest.name

        # Get first (original) and last (current) gravity for this batch
        batch_data = TiltService.get_batch_readings(batch_name)

        abv = 0
        duration = "0 days"
        apparent_attenuation = 0
        highest_gravity = None
        lowest_gravity = None

        if batch_data.exists() and batch_data.count() > 1:
            original_gravity = batch_data.first().gravity
            current_gravity = latest.gravity
            highest_gravity = batch_data.aggregate(Max('gravity'))['gravity__max']
            lowest_gravity = batch_data.aggregate(Min('gravity'))['gravity__min']
            # ABV calculation: (OG - FG) * 131.25
            abv = FermentationService.calculate_abv(
                highest_gravity,
                lowest_gravity,
            )

            # Calculate duration
            duration = FermentationService.calculate_fermentation_duration(batch_name)

            apparent_attenuation = (
                FermentationService.calculate_attenuation(
                    highest_gravity,
                    lowest_gravity,
                )
            )

        return JsonResponse({
            'temperature': latest.temperature,
            'gravity': round(float(latest.gravity), 3),
            'timestamp': local_time.strftime('%m-%d-%Y %I:%M:%S %p'),
            'name': latest.name,
            'abv': f'{abv}%',
            'duration': duration,
            'highest_gravity': round(float(highest_gravity), 3) if highest_gravity is not None else None,
            'lowest_gravity': round(float(lowest_gravity), 3) if lowest_gravity is not None else None,
            'apparent_attenuation': apparent_attenuation
        })
    else:
        return JsonResponse({'error': 'No data found'}, status=404)

@require_GET
@login_required
def calculate_slope(request):
    batch_name = request.GET.get('batch', None)

    if not batch_name:
        latest = TiltService.get_latest_reading()

        if not latest:
            return JsonResponse(
                {'error': 'No data found'},
                status=404
            )

        batch_name = latest.name

    slope = FermentationService.calculate_gravity_slope(
        batch_name
    )

    if slope is None:
        return JsonResponse(
            {'error': 'Unable to calculate slope'},
            status=404
        )

    start_time, end_time = (
        FermentationService.get_fermentation_period(
            batch_name
        )
    )

    if start_time is None or end_time is None:
        return JsonResponse({
            'slope': 'Fermentation not started',
            'slope_raw': 0
        })

    active_readings = FermentationService.get_active_readings(
        batch_name
    )

    latest_reading = TiltService.get_latest_reading(
        batch_name
    )

    fermentation_complete = (
            latest_reading is not None
            and end_time < latest_reading.timestamp
    )

    if fermentation_complete:
        fermentation_end_time = (
            timezone.localtime(end_time)
            .strftime('%m-%d-%Y %I:%M:%S %p')
        )
    else:
        fermentation_end_time = "Still fermenting"

    duration = (
        FermentationService.calculate_duration(
            start_time,
            end_time
        )
        if fermentation_complete
        else None
    )

    return JsonResponse({
        'slope': f'{slope:.4f} points/day',
        'slope_raw': float(slope),
        'fermentation_started_at': (
            timezone.localtime(start_time)
            .strftime('%m-%d-%Y %I:%M:%S %p')
        ),
        'fermentation_ended_at': fermentation_end_time,
        'fermentation_complete': fermentation_complete,
        'fermentation_duration': (
            str(duration)
            if duration is not None
            else None
        ),
        'data_points_used': len(active_readings)
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

            results = ImportService.import_tilt_csv(csv_file)

            success_count = results['success_count']
            error_count = results['error_count']
            errors = results['errors']

            if success_count > 0:
                messages.success(
                    request,
                    f'Successfully imported {success_count} records.'
                )

            if error_count > 0:
                messages.warning(
                    request,
                    f'{error_count} rows had errors. '
                    'See details below.'
                )

                for error in errors[:10]:
                    messages.error(request, error)

            return redirect('import_tilt_csv')

    else:
        form = CSVImportForm()

    return render(
        request,
        'dashboard/import_csv.html',
        {'form': form}
    )



