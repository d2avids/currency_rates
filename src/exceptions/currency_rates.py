from fastapi import HTTPException, status


class MaxRatesExceededException(HTTPException):
    def __init__(self, max_rates: int):
        self.max_rates = max_rates
        self.status_code = status.HTTP_400_BAD_REQUEST
        self.detail = f'Cannot request more than {max_rates} currency pairs at once.'
