import requests
from django.conf import settings
from django.http import JsonResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from locations.request_object import RetrieveTemperatureDataRequestObject


def retrieve_temperature_data(data):
    """ Retrieve temperature data main stuff """

    max_temp = -100
    min_temp = 100
    avg_temp = 0
    for item in data:
        if item["day"]["maxtemp_c"] > max_temp:
            max_temp = item["day"]["maxtemp_c"]

        if item["day"]["mintemp_c"] < min_temp:
            min_temp = item["day"]["mintemp_c"]

        avg_temp = avg_temp + item["day"]["avgtemp_c"]

    avg_temp = avg_temp / len(data)
    median_temp = (min_temp + max_temp) / 2

    return {
        'maximum': max_temp,
        'minimum': min_temp,
        'average': avg_temp,
        'median': median_temp
    }


class RetrieveTemperatureData(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def get(request, city):
        if 'days' not in request.query_params:
            raise Exception("[days] parameter is missing")

        request_obj = RetrieveTemperatureDataRequestObject.from_dict({
            RetrieveTemperatureDataRequestObject.CITY: city,
            RetrieveTemperatureDataRequestObject.DAYS: request.query_params.get('days')
        })

        response = requests.get(f'https://api.weatherapi.com/v1/forecast.json?key={settings.WEATHER_API_KEY}&q={request_obj.city}&aqi=no&days={request_obj.days}')

        if response.status_code != 200:
            raise Exception(response.json()["error"]["message"])

        rsp = retrieve_temperature_data(response.json()["forecast"]["forecastday"])

        return JsonResponse(rsp, safe=False)
