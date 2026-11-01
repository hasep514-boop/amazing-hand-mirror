import numpy as np
from rustypot import Sts3215PyController

c = Sts3215PyController(serial_port="COM4", baudrate=1000000, timeout=0.5)

for i in range(1, 9):
    try:
        c.write_torque_enable(i, False)
        p = float(np.rad2deg(np.ravel(c.read_present_position(i))[0]))
        print(f"ID{i}: OK  角度 {p:6.1f}")
    except Exception as e:
        print(f"ID{i}: 応答なし ({e})")