import json
import logging
import typing
from dataclasses import dataclass, fields
from datetime import datetime
from decimal import Decimal
from enum import EnumMeta, Enum
from typing import Union

import aenum


from locations.exceptions import DetailedException, ErrorCodes
from locations.utils.json_utils import decamelize, camelize

logger = logging.getLogger(__name__)
__FIELDS = "_____CONVERTIBLE______"


def _is_convertible(_cls):
    if hasattr(_cls, __FIELDS):
        return True

    return False


def _extract_metadata_callable(f, callable_name):
    if hasattr(f, "metadata"):
        if callable_name in f.metadata and hasattr(
            f.metadata[callable_name], "__call__"
        ):
            return f.metadata[callable_name]

    return None


def _extract_metadata_boolean(f, boolean_name):
    if hasattr(f, "metadata"):
        if boolean_name in f.metadata and isinstance(f.metadata[boolean_name], bool):
            return f.metadata[boolean_name]

    return False


VALIDATOR = "validator"
REQUIRED = "required"
VAL_TO_FIELD = "val_to_field"
FIELD_TO_VAL = "field_to_val"


def meta(
    validator=None, required: bool = False, field_to_value=None, value_to_field=None
):
    result = {}
    if validator is not None:
        result[VALIDATOR] = validator
    if required is not None:
        result[REQUIRED] = required
    if value_to_field:
        result[VAL_TO_FIELD] = value_to_field
    if field_to_value:
        result[FIELD_TO_VAL] = field_to_value
    return result


def from_dict(
    cls, d: dict, use_validator_field=True, ignored_fields: Union[list, tuple] = None
):
    new_instance = cls()
    # Generating {field: [field_nested_ignore_value_1, field_nested_ignore_value_2]} dictionary to ignore nested fields
    nested_ignore_dict = {}
    if ignored_fields is not None:
        nested_ignore_fields = [field for field in ignored_fields if "." in field]
        for f in nested_ignore_fields:
            ignore_key = f.split(".")[0]
            ignore_value = f.split(f"{ignore_key}.", maxsplit=1)[1]
            if ignore_key not in nested_ignore_dict:
                nested_ignore_dict[ignore_key] = []
            nested_ignore_dict[ignore_key].append(ignore_value)
    for f in fields(cls):
        field_name = f.name
        if field_name.startswith("_"):
            continue

        if field_name[0].isupper():
            continue

        if isinstance(ignored_fields, (list, tuple)) and field_name in ignored_fields:
            setattr(new_instance, field_name, d[field_name])
            continue

        field_type = None
        if hasattr(f, "type"):
            if not isinstance(f.type, str):
                field_type = f.type
            else:
                # Check if string is a Platform Play class name and convert to class type if so
                field_type = globals().get("registered_class", {}).get(f.type)
                if not field_type:
                    raise RuntimeError(
                        "Please don't import annotations from __future__. read more here [https://bugs.python.org/issue34776]"
                    )

        field_validator = _extract_metadata_callable(f, VALIDATOR)
        field_required = _extract_metadata_boolean(f, REQUIRED)
        value_to_field = _extract_metadata_callable(f, VAL_TO_FIELD)
        if field_name in d:
            field_value = d[field_name]
            field_ignored_list = nested_ignore_dict.get(field_name)
            try:
                if field_validator is not None and use_validator_field:
                    try:
                        validated_ok = field_validator(field_value)
                    except Exception as e:
                        raise ConvertibleClassValidationError(
                            "Validation function error for [{}.{}] field with error [{}]".format(
                                cls.__name__, field_name, e.args
                            )
                        )

                    if type(field_validator) is not type and not validated_ok:
                        # If the validator is a simple type e.g. bool, int, field_validator will return the value, and
                        # we must allow False/0/empty string.
                        logger.warning(
                            "Field error [{}.{}]".format(cls.__name__, field_name)
                        )
                        raise DetailedException(
                            400, "Field error [{}.{}]".format(cls.__name__, field_name)
                        )

                if isinstance(field_type, list) and not isinstance(field_value, list):
                    raise ConvertibleClassValidationError(
                        f"[{field_value}] Field type is list but field value {field_name} is not"
                    )

                if is_list_field(field_type, field_value):
                    _handle_list_values(
                        cls,
                        field_name,
                        field_type,
                        field_validator,
                        field_value,
                        new_instance,
                        use_validator_field,
                        value_to_field,
                        field_ignored_list,
                    )
                elif not isinstance(field_type, list):
                    val = _from_single_value(
                        field_type,
                        field_validator,
                        field_value,
                        use_validator_field,
                        field_required,
                        value_to_field,
                        field_ignored_list,
                    )
                    setattr(new_instance, field_name, val)
            except CreateSingleValueWrongTypeError:
                raise ConvertibleClassValidationError(
                    "Field [{}.{}] with value [{}] is not type of [{}]".format(
                        cls.__name__, field_name, field_value, field_type.__name__
                    )
                )

            except ConvertibleClassValidationError as e:
                raise e
            except Exception as e:
                raise ConvertibleClassValidationError(
                    "Field [{}.{}] with value [{}] has error [{}]".format(
                        cls.__name__, field_name, field_value, e.args
                    )
                )

        elif field_required and use_validator_field:
            raise ConvertibleClassValidationError(
                "Field [{}.{}] is mandatory".format(cls.__name__, field_name)
            )

    if hasattr(cls, "validate"):
        cls.validate(new_instance)
    if hasattr(cls, "post_init"):
        new_instance.post_init()
    return new_instance


class CreateSingleValueWrongTypeError(ValueError):
    """It wasn't possible to deserialize single element"""


def _from_single_value(
    field_type,
    field_validator,
    field_value,
    use_validator_field,
    field_required,
    value_to_field=None,
    ignored_fields=None,
):
    if value_to_field:
        field_value = value_to_field(field_value)
    if isinstance(field_value, int) and field_validator is float:
        # WARN: The opposite is not tolerable and MUST NOT be implemented
        return float(field_value)

    elif (
        isinstance(field_value, float)
        and isinstance(field_type, float)
        and _is_convertible(field_type)
    ):
        return Decimal(str(field_value))

    elif isinstance(field_value, Decimal):
        if field_validator is float:
            return float(field_value)

        elif field_validator is int:
            return int(field_value)

    elif isinstance(field_value, dict) and _is_convertible(field_type):
        return field_type.from_dict(
            field_value,
            use_validator_field=use_validator_field,
            ignored_fields=ignored_fields,
        )

    elif isinstance(field_type, EnumMeta):
        try:
            first_enum = [item for item in field_type][0]
            if isinstance(first_enum, int) or isinstance(first_enum, aenum.Enum):
                return field_type(field_value)

            return field_type[field_value]

        except KeyError as e:
            raise CreateSingleValueWrongTypeError from e

    elif field_type == typing.Any:
        return field_value

    else:
        if field_value is None and not field_required:
            return field_value

        if field_type is not None and not isinstance(field_value, field_type):
            raise CreateSingleValueWrongTypeError(
                f"{field_value} is not of type {field_type}"
            )

        return field_value


def _handle_list_values(
    cls,
    field_name,
    field_type,
    field_validator,
    field_value,
    new_instance,
    use_validator_field,
    value_to_field,
    field_ignored_list=None,
):
    if value_to_field:
        field_value = value_to_field(field_value)
    field_instance_type = _calculate_list_field_instance_type(field_type)
    if isinstance(field_instance_type, str):
        # If str, check if it's a known registered Platform Play class
        # and convert field_instance_type from str to class type
        pp_class = globals().get("registered_class", {}).get(field_instance_type)
        if pp_class:
            field_instance_type = pp_class
    if _is_convertible(field_instance_type):
        elements = [
            field_instance_type.from_dict(item, use_validator_field=use_validator_field)
            for item in field_value
        ]
        setattr(new_instance, field_name, elements)
    else:
        try:
            elements = [
                _from_single_value(
                    field_instance_type,
                    field_validator,
                    item,
                    use_validator_field,
                    True,
                    value_to_field,
                    field_ignored_list,
                )
                for item in field_value
            ]
            setattr(new_instance, field_name, elements)
        except CreateSingleValueWrongTypeError as e:
            raise ValueError(
                "List Field [{}.{}] with value [{}] is not type of [{}]".format(
                    cls.__name__, field_name, field_value, field_instance_type.__name__
                )
            ) from e

        except Exception:
            raise ConvertibleClassValidationError(
                "List Field [{}.{}] with value [{}] is not type of [{}]".format(
                    cls.__name__, field_name, field_value, field_instance_type.__name__
                )
            )


def _calculate_list_field_instance_type(field_type):
    if _is_from_generic_list(field_type):
        field_instance_type = field_type.__args__[0]
    else:
        field_instance_type = field_type[0]
    return field_instance_type


def _is_from_generic_list(field_type):
    try:
        return field_type.__origin__ == list

    except Exception:
        return False


def is_list_field(field_type, field_value):
    value_is_list = isinstance(field_value, list)
    field_type_is_list = isinstance(field_type, list) or field_type == list
    return (value_is_list and field_type_is_list) or _is_from_generic_list(field_type)


def to_dict(self, include_none=True, ignored_fields: Union[list, tuple] = None):
    if not hasattr(self, "__dict__"):
        return self

    result = {}
    # Generating {field: [field_nested_ignore_value_1, field_nested_ignore_value_2]} dictionary to ignore nested fields
    nested_ignore_dict = {}
    if ignored_fields is not None:
        nested_ignore_fields = [field for field in ignored_fields if "." in field]
        for f in nested_ignore_fields:
            ignore_key = f.split(".")[0]
            ignore_value = f.split(f"{ignore_key}.", maxsplit=1)[1]
            if ignore_key not in nested_ignore_dict:
                nested_ignore_dict[ignore_key] = []
            nested_ignore_dict[ignore_key].append(ignore_value)
    for key, val in self.__dict__.items():
        key_ignore_fields = nested_ignore_dict.get(key)
        if key.startswith("_") or key[0].isupper():
            continue

        if isinstance(ignored_fields, (list, tuple)) and key in ignored_fields:
            result[key] = val
            continue

        field = self.__dataclass_fields__.get(key)
        field_to_value = _extract_metadata_callable(field, FIELD_TO_VAL)

        if isinstance(val, (list, tuple)):
            if field_to_value and val:
                element = field_to_value(val)
            else:
                element = [
                    _to_single_value(item, include_none, key_ignore_fields)
                    for item in val
                ]
        else:
            element = _to_single_value(val, include_none, key_ignore_fields)

            if field_to_value and element:
                element = field_to_value(element)
        if include_none:
            result[key] = element
        elif element is not None and val is not None:
            result[key] = element
    return result


def _to_single_value(
    val, include_none: bool, ignored_fields: Union[list, tuple] = None
):
    if isinstance(val, Enum):
        first_enum = [item for item in val.__class__][0]
        if isinstance(first_enum, int):
            return int(val)

        return val.name

    elif isinstance(val, Decimal):
        return float(val)

    elif isinstance(val, (dict, datetime)):
        return val
    else:
        return to_dict(val, include_none, ignored_fields)


@classmethod
def from_json(
    cls,
    s,
    *,
    encoding=None,
    _cls=None,
    object_hook=None,
    parse_float=None,
    parse_int=None,
    parse_constant=None,
    object_pairs_hook=None,
    **kw,
):
    return cls.from_dict(
        json.loads(
            s,
            encoding=encoding,
            cls=_cls,
            object_hook=object_hook,
            parse_float=parse_float,
            parse_int=parse_int,
            parse_constant=parse_constant,
            object_pairs_hook=object_pairs_hook,
            **kw,
        )
    )


def to_json(
    obj,
    *,
    include_none=True,
    skipkeys=False,
    ensure_ascii=True,
    check_circular=True,
    allow_nan=True,
    cls=None,
    indent=None,
    separators=None,
    default=None,
    sort_keys=False,
    **kw,
):
    return json.dumps(
        obj.to_dict(include_none),
        skipkeys=skipkeys,
        ensure_ascii=ensure_ascii,
        check_circular=check_circular,
        allow_nan=allow_nan,
        cls=cls,
        indent=indent,
        separators=separators,
        default=default,
        sort_keys=sort_keys,
        **kw,
    )


registered_class = {}


def convertibleclass(_cls):
    """Keep track of a class"""
    registered_class[_cls.__name__] = _cls
    _cls = dataclass(_cls)
    setattr(_cls, __FIELDS, _cls.__name__)
    _cls.to_dict = to_dict
    _cls.from_dict = classmethod(from_dict)
    _cls.to_json = to_json
    _cls.from_json = from_json
    return _cls


class ConvertibleClassValidationError(DetailedException):
    """ConvertibleClass validation error."""

    def __init__(self, message=None):
        super().__init__(
            code=ErrorCodes.INVALID_REQUEST,
            debug_message=message or "Invalid Request",
            status_code=403,
        )


class Convertible:
    @classmethod
    def from_dict(cls, data: dict):
        _dict = {}
        for k, v in data.items():
            key = decamelize(k)
            _dict[key] = v
        return cls(**_dict)

    def to_dict(self, remove_keys: [] = None) -> dict:
        _dict = camelize(self.__dict__)
        kwargs = _dict.pop("kwargs", None)
        if kwargs:
            _dict.update(kwargs)

        if remove_keys:
            for key in remove_keys:
                _dict.pop(key, None)

        return _dict
