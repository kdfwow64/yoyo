import logging


class ErrorCodes:
    INVALID_REQUEST = 100001


class DetailedException(Exception):

    status_code = 400

    def __init__(
        self,
        code,
        debug_message,
        status_code=None,
        payload=None,
        log_level: int = logging.ERROR,
    ):
        Exception.__init__(self)
        self.code = code
        self.debug_message = debug_message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
        self.log_level = log_level

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["code"] = self.code
        rv["message"] = self.debug_message
        return rv

    def __str__(self):
        return self.debug_message or str(self.to_dict())
