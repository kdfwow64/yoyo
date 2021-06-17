from dataclasses import field

from locations.utils.convertible import convertibleclass, meta
from locations.utils.validators import validate_range


@convertibleclass
class RetrieveTemperatureDataRequestObject:
    """Retrieve Temperature Data request object."""
    CITY = "city"
    DAYS = "days"

    city: str = field(default=None)
    days: int = field(default=None, metadata=meta(value_to_field=int, validator=validate_range(1, 10)))
