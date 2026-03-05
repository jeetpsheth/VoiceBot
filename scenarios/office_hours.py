"""Office hours and location scenarios."""
from .base import Scenario, Turn

SCENARIO_OFFICE_HOURS = Scenario(
    id="office_hours",
    name="Ask about office hours",
    description="Patient asks when the office is open.",
    opener="Hi, could you tell me what your office hours are?",
    turns=[
        Turn(patient_says="What about on Saturdays?"),
        Turn(patient_says="Got it, thank you.", is_final=True),
    ],
)

SCENARIO_LOCATION = Scenario(
    id="location",
    name="Ask about location / address",
    description="Patient asks for office address or directions.",
    opener="Hi, I have an appointment next week. Can you give me the office address?",
    turns=[
        Turn(patient_says="Is there parking available?"),
        Turn(patient_says="Thank you.", is_final=True),
    ],
)
