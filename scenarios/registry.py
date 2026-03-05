"""Scenario registry."""
from typing import Optional

from .base import Scenario
from . import scheduling, refill, office_hours, cancel, insurance

_SCENARIOS: list[Scenario] = [
    scheduling.SCENARIO_SCHEDULE_NEW,
    scheduling.SCENARIO_RESCHEDULE,
    cancel.SCENARIO_CANCEL,
    refill.SCENARIO_REFILL,
    office_hours.SCENARIO_OFFICE_HOURS,
    office_hours.SCENARIO_LOCATION,
    insurance.SCENARIO_INSURANCE,
]


def list_scenarios() -> list[Scenario]:
    return list(_SCENARIOS)


def get_scenario(scenario_id: str) -> Optional[Scenario]:
    for s in _SCENARIOS:
        if s.id == scenario_id:
            return s
    return None
