from app.drills import AIRBORNE, LOADED, WAITING_FOR_LOAD, DrillSession


def test_rep_requires_loaded_jump_and_landing_sequence():
    session = DrillSession()
    session.start("read")

    session.update(is_loaded=True, is_jumped=False)
    state = session.update(is_loaded=True, is_jumped=False)
    assert state["phase"] == LOADED

    session.update(is_loaded=False, is_jumped=True)
    state = session.update(is_loaded=False, is_jumped=True)
    assert state["phase"] == AIRBORNE
    assert state["reps"] == 0

    session.update(is_loaded=False, is_jumped=False)
    state = session.update(is_loaded=False, is_jumped=False)
    assert state["phase"] == WAITING_FOR_LOAD
    assert state["reps"] == 1

    for _ in range(5):
        state = session.update(is_loaded=False, is_jumped=False)
    assert state["reps"] == 1


def test_tick_does_not_create_reps():
    session = DrillSession()
    session.start("left")

    for _ in range(10):
        state = session.tick()

    assert state["reps"] == 0
