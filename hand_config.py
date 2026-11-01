FINGERS = {
    "finger1": {"id1": 1, "id2": 2, "middle1": 0.5,  "middle2": -12.0, "close": 80, "open": 30},
    "finger2": {"id1": 3, "id2": 4, "middle1": 9.0,  "middle2": -7.0,  "close": 80, "open": 30},
    "finger3": {"id1": 5, "id2": 6, "middle1": 24.5, "middle2": -32.5, "close": 78, "open": 20},
    "finger4": {"id1": 7, "id2": 8, "middle1": 30.5, "middle2": -33.5, "close": 80, "open": 30},
}

def targets(name, pose):
    f = FINGERS[name]
    m1, m2 = f["middle1"], f["middle2"]
    if pose == "middle":
        return m1, m2
    if pose == "close":
        return m1 + f["close"], m2 - f["close"]
    if pose == "open":
        return m1 - f["open"], m2 + f["open"]
    raise ValueError(pose)