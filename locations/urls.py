from django.urls import path
from . import views


urlpatterns = [
    path(
        "<city>/",
        views.RetrieveTemperatureData.as_view(),
        name="retrieve_temperature_data",
    )
]
