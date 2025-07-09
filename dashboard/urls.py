from django.urls import path, include
from django.contrib.auth.views import LogoutView

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/logout/', LogoutView.as_view(), name='logout'),
    path('accounts/register/', views.register, name='register'),
    path('update_google_sheet_url/', views.update_google_sheet_url, name='update_google_sheet_url'),
    path('update_google_sheet_url/<int:pk>/', views.update_google_sheet_url, name='update_google_sheet_url'),
    path('delete_google_sheet/<int:pk>/', views.delete_google_sheet, name='delete_google_sheet'),
    path("historical_data/", views.historical_data, name="historical_data"),
    path("dashboard_view/", views.dashboard_view, name="dashboard_view"),
    path("dashboard_view_dark/", views.dashboard_view_dark, name="dashboard_view_dark"),
    path('tilt-data/', views.receive_tilt_data, name='receive_tilt_data'),
    path('debug-tilt/', views.tilt_debug, name='tilt_debug'),
    path('google_sheets_dashboard/', views.google_sheet_dashboard, name='google_sheets_dashboard'),
    path('api/latest-tilt-data/', views.get_latest_tilt_data, name='get_latest_tilt_data'),
    # path('api/current-device-temps/', views.get_current_device_temps, name='get_current_device_temps'),
]