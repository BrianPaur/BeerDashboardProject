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

class FermentationDataTilt(models.Model):
    name = models.CharField(max_length=50)
    temperature = models.FloatField()
    gravity = models.DecimalField("GRAVITY",decimal_places=4,max_digits=5)
    color = models.CharField(max_length=20, blank=True)
    timestamp = models.DateTimeField()
    comment = models.CharField(max_length=250, blank=True)