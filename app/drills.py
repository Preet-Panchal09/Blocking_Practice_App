from dataclasses import dataclass
from time import monotonic


DRILL_CUES = {
    "read": ("Read cue: setter hands", "Close and press", "Reset to loaded stance"),
    "left": ("Left close: load", "Open step left", "Press and seal"),
    "right": ("Right close: load", "Crossover right", "Press and seal"),
}


@dataclass
class DrillSession:
    name: str = "read"
    active: bool = False
    reps: int = 0
    started_at: float | None = None
    last_rep_at: float | None = None

    def start(self, name: str) -> dict:
        self.name = name if name in DRILL_CUES else "read"
        self.active = True
        self.reps = 0
        self.started_at = monotonic()
        self.last_rep_at = self.started_at
        return self.snapshot("Stop drill", DRILL_CUES[self.name][0])

    def stop(self) -> dict:
        self.active = False
        return self.snapshot("Start drill", "Camera live")

    def tick(self) -> dict:
        if not self.active:
            return self.snapshot("Start drill", "Camera live")

        now = monotonic()
        if self.last_rep_at is None:
            self.last_rep_at = now

        if now - self.last_rep_at >= 2.2:
            self.reps += 1
            self.last_rep_at = now

        cues = DRILL_CUES[self.name]
        cue = cues[self.reps % len(cues)]
        return self.snapshot("Stop drill", cue)

    def snapshot(self, button_label: str, status: str) -> dict:
        return {
            "active": self.active,
            "drill": self.name,
            "reps": self.reps,
            "repLabel": f"{self.reps} {'rep' if self.reps == 1 else 'reps'}",
            "status": status,
            "buttonLabel": button_label,
        }
