from typing import Union


def _value_to_int(value: Union[int, str]) -> int:
    """String value to int."""
    try:
        return int(value)
    except ValueError as error:
        raise Exception("The value is not integer")


def validate_range(min_: Union[int, float] = None, max_: Union[int, float] = None):
    """Check if value is in certain range"""
    def validator(value):
        value = _value_to_int(value)
        if min_ is not None and max_ is not None:
            msg = f"value must be between {min_} and {max_}"
            valid = min_ <= value <= max_
        elif min_ is not None:
            msg = f"value must be above or equal to {min_}"
            valid = min_ <= value
        elif max_ is not None:
            msg = f"value must be below or equal to {max_}"
            valid = value <= max_
        else:
            raise TypeError(
                "At least one of arguments should be provided: 'min_number', 'max_number'"
            )

        if not valid:
            raise Exception(msg)

        return True

    return validator
