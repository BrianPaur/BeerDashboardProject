import pandas as pd
from .models import FermentationData


def add_dataframe_to_db(df):
    """
    Adds rows from a Pandas DataFrame to the TempData database table.

    Args:
        df (pd.DataFrame): The DataFrame containing the data to insert.
    """
    for _, row in df.iterrows():
        FermentationData.objects.create(
            time_stamp=row['Time Stamp'],  # Replace with your DataFrame column name
            time_point=row['Timepoint'],
            specific_gravity=row['Specific Gravity'],
            temperature=row['Temperature'],
            color=row['Color'],
            beer=row['Beer']
        )


def add_dataframe_to_db_bulk(df):
    """
    Adds rows from a Pandas DataFrame to the TempData database table using bulk_create.

    Args:
        df (pd.DataFrame): The DataFrame containing the data to insert.
    """
    temp_data_objects = [
        FermentationData(
            time_stamp=row['Time Stamp'],  # Replace with your DataFrame column name
            time_point=row['Timepoint'],
            specific_gravity=row['Specific Gravity'],
            temperature=row['Temperature'],
            color=row['Color'],
            beer=row['Beer']
        )
        for _, row in df.iterrows()
    ]
    FermentationData.objects.bulk_create(temp_data_objects)
    
def add_dataframe_to_db_safe(df):
    for _, row in df.iterrows():
        try:
            FermentationData.objects.create(
            time_stamp=row['Time Stamp'],  # Replace with your DataFrame column name
            time_point=row['Timepoint'],
            specific_gravity=row['Specific Gravity'],
            temperature=row['Temperature'],
            color=row['Color'],
            beer=row['Beer']
        )
        except Exception as e:
            print(f"Error saving row: {row}, Error: {e}")
    


