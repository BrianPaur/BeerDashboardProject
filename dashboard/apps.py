from django.apps import AppConfig
import sys

class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'

    def ready(self):
        # Import inside the ready method to avoid AppRegistryNotReady
        if 'runserver' in sys.argv:  # Ensure this runs only when the server starts
            from .scheduler import start_data_update
            start_data_update()
