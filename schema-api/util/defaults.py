"""
This module contains functions that generate defaults for models' fields

The purpose of a separate module and separate default providers lies to the particularity of Django default functions
being persisted within the corresponding migration and ultimately getting used through their reference when the
corresponding field value is missing. This causes an issue when trying to test the corresponding field that it indeed
stores the default value of the function, by mocking the function - the mocking mocks the reference to the function but
the Django model already uses the function as it is passed in the migration file, thus the mocking never takes place
and the test fails.

A work-around to this is to enclose these default providers to dummy wrappers that call these providers and return the
corresponding value. The dummy wrapper will be stored in the generated migrations but the actual default provider is
free to be mocked. The issue with this though is that the dummy wrapper cannot be erased, since this will break the
migration that was generated for it.
"""
from django.utils import timezone


def get_current_datetime():
    return timezone.now()
