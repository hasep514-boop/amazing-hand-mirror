# hand_mirror.py
# Webカメラの手をMediaPipe(AI)で読み取り、Amazing Handにまねさせる
# 終了: カメラ画面で q キー(全指のトルクを切って終わる)
import time, math
import cv2
import numpy as np
import mediapipe as mp
from rustypot import Sts3215PyController
from hand_config import FINGERS, targets

PORT = "COM4"
SPEED = 4            # サーボの速さ(大きいほど速い)
SEND_HZ = 10         # 1秒あたりの指令回数
SMOOTH = 0.4         # 0〜1。小さいほど動きがなめらか(遅れる)
TEMP_LIMIT = 55      # これを超えたら全指トルクOFFで停止(℃)
LOAD_LIMIT = 250     # 負荷(0.1%単位)。25%超えが続いたら「どこかに当たっている」と警告を出す
LOAD_COUNT = 3       # 何回続けて(0.5秒ごと)超えたら警告するか。動き始めの一瞬の負荷は無視
GRACE = 3.0          # トルクONから何秒は負荷を見ない(起動時に全指が一斉に動くため)
DEADBAND = 0.03      # 命令の変化がこれより小さければ送らない
IDLE_OFF = 2.0       # 手が見えなくなって何秒でトルクを切るか
# ロボットの指ごとの「閉じ」の上限(0〜1)。親指は人差し指とぶつかるので浅くする
MAX_FRAC = {"index": 1.0, "middle": 1.0, "ring": 1.0, "thumb": 0.6}

# 人の指の曲がり角度(度) → ロボットの開き/閉じ の対応。cam_testの数字を見て調整する
#            伸ばした時, 握った時
CURL = {"index":  (10, 100),
        "middle": (10, 100),
        "ring":   (10, 100),
        "thumb":  (10, 60)}
# MediaPipeの点の番号(付け根, 第2関節, 指先)
POINTS = {"index": (5, 6, 8), "middle": (9, 10, 12), "ring": (13, 14, 16), "thumb": (2, 3, 4)}
# 人の指 → ロボットの指
ROBOT = {"index": "finger1", "middle": "finger2", "ring": "finger3", "thumb": "finger4"}

def curl(p, a, b, c):
    v1 = np.array([p[a].x - p[b].x, p[a].y - p[b].y, p[a].z - p[b].z])
    v2 = np.array([p[c].x - p[b].x, p[c].y - p[b].y, p[c].z - p[b].z])
    cos = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9)
    return 180 - math.degrees(math.acos(np.clip(cos, -1, 1)))

# ---- MediaPipe(新旧どちらでも動く) ----
try:
    hands = mp.solutions.hands.Hands(max_num_hands=1)
    def detect(rgb):
        r = hands.process(rgb)
        return r.multi_hand_landmarks[0].landmark if r.multi_hand_landmarks else None
except AttributeError:
    from mediapipe.tasks import python as mpt
    from mediapipe.tasks.python import vision
    det = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=mpt.BaseOptions(model_asset_path="hand_landmarker.task"), num_hands=1))
    def detect(rgb):
        r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        return r.hand_landmarks[0] if r.hand_landmarks else None

# ---- サーボ ----
c = Sts3215PyController(serial_port=PORT, baudrate=1000000, timeout=0.5)
IDS = [i for f in FINGERS.values() for i in (f["id1"], f["id2"])]

def torque_all(on):
    for i in IDS:
        try:
            c.write_torque_enable(i, on)
        except Exception:
            pass

def send(name, frac):
    """frac: 0=開き, 1=閉じ"""
    f = FINGERS[name]
    o1, o2 = targets(name, "open")
    c1, c2 = targets(name, "close")
    a = o1 + (c1 - o1) * frac
    b = o2 + (c2 - o2) * frac
    c.write_goal_position(f["id1"], np.deg2rad(a))
    c.write_goal_position(f["id2"], np.deg2rad(b))

for i in IDS:
    c.write_goal_speed(i, SPEED)
torque_all(True)
frac = {k: 0.5 for k in ROBOT}          # 最初は中間
sent = {k: -1.0 for k in ROBOT}
cap = cv2.VideoCapture(0)
last_send = last_temp = last_load = 0.0
last_seen = time.time()
torque_on = True
t_on = time.time()   # トルクをONにした時刻
over = 0             # 温度の上限超えが何回続いたか
hit = {k: 0 for k in ROBOT}   # 負荷の上限超えが何回続いたか(指ごと)

def load_of(i):
    v = int(np.ravel(c.read_present_load(i))[0])
    return v - 1024 if v > 1024 else v
try:
    while True:
        ok, frame = cap.read()
        if not ok:
            print("カメラが開けません"); break
        frame = cv2.flip(frame, 1)
        p = detect(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if p:
            h, w = frame.shape[:2]
            for q in p:
                cv2.circle(frame, (int(q.x * w), int(q.y * h)), 4, (0, 255, 0), -1)
            for k, (name, idx) in enumerate(POINTS.items()):
                ang = curl(p, *idx)
                lo, hi = CURL[name]
                target = float(np.clip((ang - lo) / (hi - lo), 0, MAX_FRAC[name]))
                frac[name] += SMOOTH * (target - frac[name])
                cv2.putText(frame, f"{name}: {ang:5.1f} -> {frac[name]:.2f}", (10, 30 + 30 * k),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        now = time.time()
        if p:
            last_seen = now
            if not torque_on:
                torque_all(True); torque_on = True; t_on = now
                sent = {k: -1.0 for k in ROBOT}
        elif torque_on and now - last_seen > IDLE_OFF:   # 手が消えたら休ませる
            torque_all(False); torque_on = False
            print("手が見えないのでトルクOFF(休憩中)")
        if torque_on and now - last_send > 1.0 / SEND_HZ:
            for name, robo in ROBOT.items():
                if abs(frac[name] - sent[name]) > DEADBAND:   # 小さな揺れは無視
                    send(robo, frac[name]); sent[name] = frac[name]
            last_send = now
        if torque_on and now - t_on > GRACE and now - last_load > 0.5:   # 0.5秒ごとに負荷チェック
            for name, robo in ROBOT.items():
                f = FINGERS[robo]
                ld = max(load_of(f["id1"]), load_of(f["id2"]))
                hit[name] = hit[name] + 1 if ld > LOAD_LIMIT else 0
                if hit[name] >= LOAD_COUNT:       # 1.5秒続いたら警告だけ出す(上限は変えない)
                    hit[name] = 0
                    print(f"【警告】{name} の負荷 {ld/10:.0f}% が1.5秒続いた(どこかに当たっている可能性)")
            last_load = now
        if now - last_temp > 1:                   # 1秒ごとに温度チェック
            temps = [int(np.ravel(c.read_present_temperature(i))[0]) for i in IDS]
            print("温度", temps, " 親指の負荷", load_of(7), load_of(8))
            over = over + 1 if max(temps) > TEMP_LIMIT else 0
            if over >= 2:                         # 1回だけの読み違いでは止めない
                print(f"温度が{TEMP_LIMIT}℃を2回続けて超えたので停止します"); break
            last_temp = now
        cv2.imshow("hand_mirror (q:終了)", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
finally:
    torque_all(False)
    cap.release(); cv2.destroyAllWindows()
    print("終了。全指トルクOFF")