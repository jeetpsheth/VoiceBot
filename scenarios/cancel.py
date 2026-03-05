"""Cancel appointment scenario."""
from .base import Scenario, Turn

SCENARIO_CANCEL = Scenario(
    id="cancel",
    name="Cancel appointment",
    description="Patient wants to cancel an appointment.",
    opener="Hi, I need to cancel my appointment please.",
    turns=[
        Turn(patient_says="It's on Monday at 10. My name is John Davis."),
        Turn(patient_says="Yes, please cancel it. I'll call back when I need to reschedule."),
        Turn(patient_says="Thank you. Bye.", is_final=True),
    ],
)
