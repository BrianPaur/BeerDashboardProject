from django.contrib import admin

from .models import TemperatureData,FermentationData, FermentationDataTilt

# class ChoiceInline(admin.TabularInline):
#     model = TempData
#     # extra = 3

class TemperatureDataAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {"fields": ["time_stamp"]}),
        (None, {"fields": ["set_temp"]}),
        (None, {"fields": ["current_temp"]}),
        
    ]
    # inlines = [ChoiceInline]
    list_display = ["time_stamp", "set_temp", "current_temp"]
    list_filter = ["time_stamp"]
    search_fields = ["time_stamp"]
    
class FermentationDataAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {"fields": ["time_stamp"]}),
        (None, {"fields": ["specific_gravity"]}),
        (None, {"fields": ["temperature"]}),
        (None, {"fields": ["color"]}),
        (None, {"fields": ["beer"]}),
    ]
    
    # inlines = [ChoiceInline]
    list_display = ["time_stamp", "specific_gravity","temperature","color","beer"]
    list_filter = ["time_stamp"]
    search_fields = ["time_stamp"]

class FermentationDataTiltAdmin(admin.ModelAdmin):
    fieldsets = [
    (None, {"fields": ["name"]}),
    (None, {"fields": ["temperature"]}),
    (None, {"fields": ["gravity"]}),
    (None, {"fields": ["color"]}),
    (None, {"fields": ["timestamp"]}),
    (None, {"fields": ["comment"]}),
    ]
    list_display = ["name","timestamp", "temperature", "gravity","color","timestamp","comment"]
    list_filter = ["timestamp"]
    search_fields = ["timestamp"]

admin.site.register(TemperatureData,TemperatureDataAdmin)
admin.site.register(FermentationData,FermentationDataAdmin)
admin.site.register(FermentationDataTilt,FermentationDataTiltAdmin)