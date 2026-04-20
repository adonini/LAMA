from datetime import datetime as real_datetime, timezone as real_timezone
from itertools import count

import pytest
from django.utils import timezone as django_timezone

from members import models, views
from members.models import Category, Duty, Institute


FROZEN_NOW = real_datetime(2024, 6, 1, 12, 0, 0, tzinfo=real_timezone.utc)


class FrozenDateTime(real_datetime):
    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return cls(
                FROZEN_NOW.year,
                FROZEN_NOW.month,
                FROZEN_NOW.day,
                FROZEN_NOW.hour,
                FROZEN_NOW.minute,
                FROZEN_NOW.second,
                FROZEN_NOW.microsecond,
            )
        return FROZEN_NOW.astimezone(tz)


@pytest.fixture(autouse=True)
def freeze_domain_time(monkeypatch):
    monkeypatch.setattr(django_timezone, "now", lambda: FROZEN_NOW)
    monkeypatch.setattr(models.timezone, "now", lambda: FROZEN_NOW)
    monkeypatch.setattr(views.timezone, "now", lambda: FROZEN_NOW)
    monkeypatch.setattr(models, "now", lambda: FROZEN_NOW)
    monkeypatch.setattr(models, "datetime", FrozenDateTime)
    monkeypatch.setattr(views, "datetime", FrozenDateTime)


@pytest.fixture(autouse=True)
def patch_model_create_defaults(monkeypatch):
    institute_counter = count(1)
    original_institute_create = Institute.objects.create
    original_duty_create = Duty.objects.create

    def create_institute(*args, **kwargs):
        if not kwargs.get("long_name"):
            suffix = next(institute_counter)
            kwargs["long_name"] = f"{kwargs.get('name', 'Institute')} Full {suffix}"
        return original_institute_create(*args, **kwargs)

    def create_duty(*args, **kwargs):
        if not kwargs.get("category"):
            kwargs["category"], _ = Category.objects.get_or_create(name="Test Category")
        return original_duty_create(*args, **kwargs)

    monkeypatch.setattr(Institute.objects, "create", create_institute)
    monkeypatch.setattr(Duty.objects, "create", create_duty)
