import datetime
from xmlrpc.client import boolean

from django.conf.locale.ar.formats import DATE_FORMAT
from django.db import models

class TemperatureData(models.Model):
    time_stamp = models.DateTimeField("Time Stamp")
    set_temp = models.DecimalField("Set Temp",decimal_places=2,max_digits=5)
    current_temp = models.DecimalField("Current Temp",decimal_places=2,max_digits=5)

class FermentationData(models.Model):
    time_stamp = models.CharField("Time Stamp",max_length=20)
    time_point = models.DecimalField("Timepoint",decimal_places=2,max_digits=8,null=True)
    specific_gravity = models.DecimalField("Specific Gravity",decimal_places=2,max_digits=5)
    temperature = models.DecimalField("Temperature",decimal_places=2,max_digits=5)
    color = models.CharField(verbose_name="Color", max_length=20)
    beer = models.CharField(verbose_name="Beer", max_length=100)

    def __str__(self):
        return self.beer
    
class GoogleSheetSourceData(models.Model):
    sourceURL = models.CharField("SourceURL", max_length=250, unique=True)
    readable_name = models.CharField("Readable Name", max_length=250, unique=True)

    def __str__(self):
        return f"{self.readable_name} ({self.sourceURL})"

class ProfileDataSelect(models.Model):
    user_profile = models.CharField("user_profile", max_length=250, unique=True)
    selected_google_sheet = models.CharField("Readable Name", max_length=250, unique=True)

    def __str__(self):
        return f"{self.user_profile} ({self.selected_google_sheet})"

class FermentationDataTilt(models.Model):
    name = models.CharField(max_length=50)
    temperature = models.FloatField()
    gravity = models.FloatField()
    color = models.CharField(max_length=20, blank=True)
    timestamp = models.DateTimeField()
    



