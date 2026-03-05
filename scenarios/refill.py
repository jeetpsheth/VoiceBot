"""Medication refill scenario."""
from .base import Scenario, Turn

SCENARIO_REFILL = Scenario(
    id="refill",
    name="Medication refill request",
    description="Patient requests a refill for a prescription.",
    opener="Hello, I need to request a refill for my prescription.",
    turns=[
        Turn(patient_says="It's for lisinopril. Dr. Martinez prescribed it. My name is Sarah Chen."),
        Turn(patient_says="Yes, I'll pick it up at the pharmacy on Main Street. Thank you."),
        Turn(patient_says="Thanks. Bye.", is_final=True),
    ],
)
