from dataclasses import dataclass
from time import monotonic


DRILL_CUES = {
    "read": ("Read cue: setter hands", "Close and press", "Reset to loaded stance"),
    "left": ("Left close: load", "Open step left", "Press and seal"),
    "right": ("Right close: load", "Crossover right", "Press and seal"),
}

WAITING_FOR_LOAD = "waiting_for_load"
LOADED = "loaded"
AIRBORNE = "airborne"
CONFIRMATION_FRAMES = 2


@dataclass
class DrillSession:
    name: str = "read"
    active: bool = False
    reps: int = 0
    started_at: float | None = None
    last_rep_at: float | None = None
    phase: str = WAITING_FOR_LOAD
    status: str = "Camera live"
    loaded_frames: int = 0
    jumped_frames: int = 0
    grounded_frames: int = 0

    def start(self, name: str) -> dict:
        self.name = name if name in DRILL_CUES else "read"
        self.active = True
        self.reps = 0
        self.started_at = monotonic()
        self.last_rep_at = self.started_at
        self.phase = WAITING_FOR_LOAD
        self.status = DRILL_CUES[self.name][0]
        self.loaded_frames = 0
        self.jumped_frames = 0
        self.grounded_frames = 0
        return self.snapshot()

    def stop(self) -> dict:
        self.active = False
        self.phase = WAITING_FOR_LOAD
        self.status = "Camera live"
        return self.snapshot()

    def update(self, is_loaded: bool, is_jumped: bool, *, pose_seen: bool = True) -> dict:
        """Advance the drill from confirmed pose events, never elapsed time."""
        if not self.active:
            return self.snapshot()

        # A missed detection is not a landing or a reset. Hold the phase until
        # the hips and shoulders are visible again.
        if not pose_seen:
            return self.snapshot()

        cues = DRILL_CUES[self.name]

        if self.phase == WAITING_FOR_LOAD:
            self.loaded_frames = self.loaded_frames + 1 if is_loaded else 0
            if self.loaded_frames >= CONFIRMATION_FRAMES:
                self.phase = LOADED
                self.status = cues[1]
                self.jumped_frames = 0

        elif self.phase == LOADED:
            self.jumped_frames = self.jumped_frames + 1 if is_jumped else 0
            if self.jumped_frames >= CONFIRMATION_FRAMES:
                self.phase = AIRBORNE
                self.status = "Jump — press and seal"
                self.grounded_frames = 0

        elif self.phase == AIRBORNE:
            self.grounded_frames = 0 if is_jumped else self.grounded_frames + 1
            if self.grounded_frames >= CONFIRMATION_FRAMES:
                self.reps += 1
                self.last_rep_at = monotonic()
                self.phase = WAITING_FOR_LOAD
                self.status = cues[2]
                self.loaded_frames = 0
                self.jumped_frames = 0
                self.grounded_frames = 0

        return self.snapshot()

    def tick(self) -> dict:
        return self.snapshot()

    def snapshot(self) -> dict:
        return {
            "active": self.active,
            "drill": self.name,
            "reps": self.reps,
            "repLabel": f"{self.reps} {'rep' if self.reps == 1 else 'reps'}",
            "phase": self.phase,
            "status": self.status,
            "buttonLabel": "Stop drill" if self.active else "Start drill",
        }
