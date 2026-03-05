"""Appointment scheduling scenarios."""
from .base import Scenario, Turn

SCENARIO_SCHEDULE_NEW = Scenario(
    id="schedule_new",
    name="Schedule new appointment",
    description="Patient calls to book a new appointment.",
    opener="Hi, I'd like to schedule an appointment for a checkup, please.",
    turns=[
        Turn(patient_says="Next week if possible, any morning."),
        Turn(patient_says="Tuesday at 9 would be perfect. Thank you."),
        Turn(patient_says="Yes, that works. See you then. Bye.", is_final=True),
    ],
)

SCENARIO_RESCHEDULE = Scenario(
    id="reschedule",
    name="Reschedule existing appointment",
    description="Patient wants to move an existing appointment.",
    opener="Hello, I need to reschedule my appointment that I have for this week.",
    turns=[
        Turn(patient_says="It was on Thursday at 2 PM. My name is Jane Smith."),
        Turn(patient_says="Could I move it to Friday afternoon instead?"),
        Turn(patient_says="3 PM on Friday is great. Thanks so much.", is_final=True),
    ],
)
