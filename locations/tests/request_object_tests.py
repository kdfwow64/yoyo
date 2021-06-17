from django.core.exceptions import ValidationError
from django.test import TestCase

from locations.request_object import RetrieveTemperatureDataRequestObject
from locations.utils.convertible import ConvertibleClassValidationError


class RetrieveTemperatureDataTestCase(TestCase):
    def test_failure_request_object_with_invalid_days_string(self):
        request_dict = {
            "city": "London",
            "days": "days"
        }
        with self.assertRaises(ConvertibleClassValidationError):
            RetrieveTemperatureDataRequestObject.from_dict(request_dict)

    def test_failure_request_object_with_invalid_days_number(self):
        request_dict = {
            "city": "London",
            "days": 55
        }
        with self.assertRaises(ConvertibleClassValidationError):
            RetrieveTemperatureDataRequestObject.from_dict(request_dict)
