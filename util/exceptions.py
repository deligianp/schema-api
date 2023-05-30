import rest_framework
from django.conf import settings
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from rest_framework import serializers, status
from rest_framework.views import exception_handler

from util.constraints import ApplicationUniqueConstraint


class ApplicationError(Exception):
    pass


class ApplicationValidationError(ApplicationError, ValidationError):
    pass


class ApplicationDuplicateError(ApplicationValidationError):
    pass


class ApplicationNotFoundError(ApplicationError):
    pass


class ApplicationErrorHelper:

    @staticmethod
    def _is_unique_error(err: ValidationError) -> bool:
        return hasattr(err, 'code') and err.code == ApplicationUniqueConstraint.error_code

    @classmethod
    def _remove_unique_errors(cls, error_dict: dict):
        non_unique_errors = [err for err in error_dict.get(NON_FIELD_ERRORS, []) if
                             not ApplicationErrorHelper._is_unique_error(err)]
        if non_unique_errors:
            return {
                **error_dict,
                NON_FIELD_ERRORS: non_unique_errors
            }
        return error_dict

    @classmethod
    def _keep_unique_errors(cls, error_dict: dict):
        unique_errors = [err for err in error_dict.get(NON_FIELD_ERRORS, []) if
                         ApplicationErrorHelper._is_unique_error(err)]
        if unique_errors:
            return {
                **error_dict,
                NON_FIELD_ERRORS: unique_errors
            }
        return error_dict

    @classmethod
    def _normalize_constraint_errors(cls, error_dict: dict):
        new_error_dict = {
            **error_dict
        }

        non_field_errors = new_error_dict.pop(NON_FIELD_ERRORS, [])
        if non_field_errors:
            new_non_field_errors = []
            for err in non_field_errors:
                if hasattr(err, 'context') and 'field' in err.context:
                    new_error_dict.setdefault(err.context['field'], []).append(err)
                else:
                    new_non_field_errors.append(err)
            if new_non_field_errors:
                new_error_dict[NON_FIELD_ERRORS] = new_non_field_errors
        return new_error_dict

    @classmethod
    def to_application_error(cls, ex: ValidationError) -> ApplicationError:
        """A converter - converting from a Django ValidationError to a proper ApplicationError

        The method aims to deal with the ValidationErrors, potentially raised by invoking a model's full_clean() method.
        full_clean() validation errors are expected to have an `error_dict` attribute containing the specific
        ValidationErrors raised by each field individually, as well as model-wide ValidationErrors. These can come
        either from custom model validation logic and model database constraints. Specifically for constraints, the
        method takes into account the implementation of contextualized constraints, defined under `util.constraints.py`,
        that raise more meaningful errors. If these constraints are in place, raised ValidationErrors will have more
        knowledge about what went wrong and thus will be able to return the proper `ApplicationError` subclass.

        For example, the default CheckConstraint will return a ValidationError with the given `violation_error_message`
        when it is violated. If instead of the CheckConstraint, ApplicationCheckConstraint is raised, ValidationError
        will have a set `code` field denoting that a constraint was violated. Moreover, during constraint definition,
        user can define the key 'field' in the `error_context` key-word argument, which will be used from this method
        to "move" the constraint from the model-wide error list, to a specific, field's error_list.

        The method will also filter and may return only a subset of the validation errors. If any of the validation
        errors is NOT due to a unique constraint violation, only non-unique-violation ValidationErrors will be returned.
        If instead, all the raised ValidationErrors are due to violating uniqueness rules, then all will be returned.
        This logic is implemented because, to the end users, it shouldn't matter if they tried to set a duplicate, as
        long as the entity that they tried to persist was invalid. If all checks regarding the entity's values pass,
        then uniqueness becomes relevant.

        Args:
              ex: The raised validation error
        Returns:
              The converted ApplicationError
        """
        if hasattr(ex, 'error_dict'):
            error_dict = ex.error_dict
            if len(error_dict) == 1 and NON_FIELD_ERRORS in error_dict:
                non_field_errors = error_dict[NON_FIELD_ERRORS]
                all_non_field_errors_are_unique_errors = all(
                    hasattr(err, 'code') and err.code == ApplicationUniqueConstraint.error_code
                    for err in non_field_errors
                )
                if all_non_field_errors_are_unique_errors:
                    error_dict = ApplicationErrorHelper._normalize_constraint_errors(
                        ApplicationErrorHelper._keep_unique_errors(error_dict)
                    )
                    return ApplicationDuplicateError(error_dict)
            error_dict = ApplicationErrorHelper._normalize_constraint_errors(
                ApplicationErrorHelper._remove_unique_errors(error_dict)
            )
            return ApplicationValidationError(error_dict)


def convert_to_drf_validation_error(err: ValidationError):
    DRF_NON_FIELD_ERRORS = getattr(settings, 'NON_FIELD_ERRORS_KEY', NON_FIELD_ERRORS)
    if isinstance(err, ValidationError):
        data = err.message_dict
        if NON_FIELD_ERRORS in data:
            data[DRF_NON_FIELD_ERRORS] = data[NON_FIELD_ERRORS]
            del data[NON_FIELD_ERRORS]

        exc = rest_framework.exceptions.ValidationError(detail=data)
        return exc


def custom_exception_handler(exc: Exception, context):
    if issubclass(type(exc), ApplicationValidationError):
        drf_exc = convert_to_drf_validation_error(exc)
        response = exception_handler(drf_exc, context)
        if type(exc) is ApplicationDuplicateError:
            response.status_code = status.HTTP_409_CONFLICT
    elif issubclass(type(exc), ApplicationNotFoundError):
        response = exception_handler(rest_framework.exceptions.NotFound(detail=exc), context)
    else:
        response = exception_handler(exc, context)
    return response
