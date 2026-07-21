from dataclasses import dataclass, field
from time import monotonic

from app.basepose import BasePose
from app.drills import DrillSession


@dataclass
class PracticeState:
    base_pose: BasePose = field(default_factory=BasePose)
    drill_session: DrillSession = field(default_factory=DrillSession)
    calibration_started_at: float | None = None
    calibration_message: str | None = None
    last_seen_at: float = field(default_factory=monotonic)

