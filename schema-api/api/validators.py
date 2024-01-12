from rest_framework.exceptions import ValidationError


class NotEqualsValidator:

    def __init__(self, value):
        self.value = value

    def __call__(self, value_to_check):
        if value_to_check == self.value:
            raise ValidationError(f'This field\'s value cannot be {self.value}')