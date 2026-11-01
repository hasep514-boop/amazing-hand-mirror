import time
import numpy as np
from rustypot import Sts3215PyController
from hand_config import FINGERS, targets

c = Sts3215PyController(serial_port="COM4", baudrate=1000000, timeout=0.5)
SPEED = 3

def move(f, pose):
    a, b = targets(f, pose)
    i1, i2 = FINGERS[f]["id1"], FINGERS[f]["id2"]
    for i in (i1, i2):
        c.write_goal_speed(i, SPEED)
    c.write_goal_position(i1, np.deg2rad(a))
    c.write_goal_position(i2, np.deg2rad(b))

for f in ["finger1", "finger2", "finger3", "finger4"]:
    input(f"{f} を動かします。Enterで開始")
    i1, i2 = FINGERS[f]["id1"], FINGERS[f]["id2"]
    c.write_torque_enable(i1, True)
    c.write_torque_enable(i2, True)
    for pose in ["middle", "close", "middle", "open", "middle"]:
        move(f, pose)
        time.sleep(3)
        print(f"  {pose:6s} 負荷 {c.read_present_load(i1)} / {c.read_present_load(i2)}")
    c.write_torque_enable(i1, False)
    c.write_torque_enable(i2, False)
print("終了。全指トルクOFF")