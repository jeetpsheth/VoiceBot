"""Insurance-related questions."""
from .base import Scenario, Turn

SCENARIO_INSURANCE = Scenario(
    id="insurance",
    name="Insurance question",
    description="Patient asks whether the office takes their insurance.",
    opener="Hello, do you accept Blue Cross Blue Shield?",
    turns=[
        Turn(patient_says="Do I need to bring my insurance card to my first visit?"),
        Turn(patient_says="Okay, thanks.", is_final=True),
    ],
)
