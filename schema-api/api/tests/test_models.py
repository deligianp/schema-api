import datetime
from unittest.mock import patch
from datetime import datetime as dt

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from api.constants import TaskStatus
from api.models import Task, StatusHistoryPoint


class StatusHistoryPointTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.task = Task.objects.create(name='sample-task')

    def test_valid_save_accepts_all_provided_values(self):
        dt = timezone.now()
        status = TaskStatus.SUBMITTED
        status_history_point = StatusHistoryPoint(task=self.task, created_at=dt, status=status)
        status_history_point.save()
        status_history_point.refresh_from_db()
        self.assertEqual(status_history_point.status, status)
        self.assertEqual(status_history_point.created_at, dt)
        self.assertEqual(status_history_point.task, self.task)

    def test_save_without_a_referenced_task_raises_error(self):
        dt = timezone.now()
        status = TaskStatus.SUBMITTED
        status_history_point = StatusHistoryPoint(created_at=dt, status=status)
        with self.assertRaises(IntegrityError):
            status_history_point.save()

    def test_save_with_a_referenced_task_as_none_raises_error(self):
        dt = timezone.now()
        status = TaskStatus.SUBMITTED
        status_history_point = StatusHistoryPoint(task=None, created_at=dt, status=status)
        with self.assertRaises(IntegrityError):
            status_history_point.save()

    def test_save_without_created_at_uses_timezone_now_default(self):
        mocked_datetime = dt(2020, 1, 1, 1, 1, 1, tzinfo=datetime.timezone.utc)
        status = TaskStatus.SUBMITTED
        with patch('django.utils.timezone.now', return_value=mocked_datetime):
            print(timezone.now())
            status_history_point = StatusHistoryPoint.objects.create(task=self.task, status=status)
        print(status_history_point.created_at)
        self.assertEqual(status_history_point.created_at, mocked_datetime)

    def test_save_with_created_at_as_none_raises_error(self):
        status = TaskStatus.SUBMITTED
        status_history_point = StatusHistoryPoint(task=self.task, created_at=None, status=status)
        with self.assertRaises(IntegrityError):
            status_history_point.save()

    def test_save_without_task_status_raises_error(self):
        dt = timezone.now()
        status_history_point = StatusHistoryPoint(created_at=dt, task=self.task)
        with self.assertRaises(IntegrityError):
            status_history_point.save()

    def test_save_with_task_status_as_none_raises_error(self):
        dt = timezone.now()
        status_history_point = StatusHistoryPoint(created_at=dt, task=self.task, status=None)
        with self.assertRaises(IntegrityError):
            status_history_point.save()

    def test_save_with_invalid_task_status_choice_raises_error(self):
        invalid_status_value = 414141
        dt = timezone.now()
        status_history_point = StatusHistoryPoint(created_at=dt, task=self.task, status=invalid_status_value)
        with self.assertRaises(IntegrityError):
            status_history_point.save()

    def test_str_returns_status_history_point_description(self):
        dt = timezone.now()
        status = TaskStatus.SUBMITTED
        status_history_point = StatusHistoryPoint(task=self.task, created_at=dt, status=status)
        self.assertEqual(f'{self.task.uuid}: {status.label}({dt.isoformat()})', str(status_history_point))

    def test_deleting_referenced_task_deletes_status_history_point(self):
        task = Task.objects.create(name='sample-task-2')
        dt = timezone.now()
        status = TaskStatus.SUBMITTED
        status_history_point = StatusHistoryPoint(task=task, created_at=dt, status=status)
        task.delete()
        with self.assertRaises(StatusHistoryPoint.DoesNotExist):
            status_history_point.refresh_from_db()
