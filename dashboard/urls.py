from django.urls import path, include
from django.contrib.auth.views import LogoutView

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/logout/', LogoutView.as_view(), name='logout'),
    path('accounts/register/', views.register, name='register'),
    path('tilt-data/', views.receive_tilt_data, name='receive_tilt_data'),
    path('debug-tilt/', views.tilt_debug, name='tilt_debug'),
    path('api/latest-tilt-data/', views.get_latest_tilt_data, name='get_latest_tilt_data'),
    path('api/latest-freeze-ink-data/', views.get_inkbird_freeze_data, name='get_latest_freeze_ink_data'),
    path('api/latest-ferm-ink-data/', views.get_inkbird_ferm_data, name='get_latest_ferm_ink_data'),
    path('api/calculate-slope/', views.calculate_slope, name='calculate_slope'),
    path('import-csv/', views.import_tilt_csv, name='import_tilt_csv'),
]