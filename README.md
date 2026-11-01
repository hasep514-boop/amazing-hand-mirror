# Amazing Hand × MediaPipe：カメラの手をまねる自作ロボットハンド

Physical AI講座2026 応用編1 最終課題。Webカメラの手を MediaPipe（AI推論）で読み取り、自作の Amazing Hand Enhanced（Feetech STS3032 ×8）にまねさせます。

## ファイル
| ファイル | 内容 |
|---|---|
| `hand_mirror.py` | 本体。カメラ → MediaPipe → 指の曲がり角度 → サーボへ送信（安全装置つき） |
| `hand_config.py` | 指ごとに校正した中立位置（MiddlePos）と開閉量 |
| `cam_test.py` | カメラと手の骨格推定だけの確認用 |
| `ping_all.py` | 8個のサーボが応答するかの確認 |
| `hand_test.py` | 指を1本ずつ開閉して負荷を確認 |

## 動かし方（Windows）
```
python -m pip install mediapipe opencv-python rustypot numpy
curl -L -o hand_landmarker.task https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
python hand_mirror.py
```
- シリアルポートは `hand_mirror.py` の `PORT`（既定 COM4）を環境に合わせて変更
- カメラ画面で `q` キーで終了（全指トルクOFF）

## 安全装置
- 指令10Hz・平滑化・不感帯、手が2秒消えたらトルクOFF
- 温度を1秒ごとに監視し55℃超が2回続けば停止、負荷が1.5秒高い状態が続けば警告
- 親指は人差し指と干渉しないよう閉じを6割に制限

## 参考
- Amazing Hand（Pollen Robotics）: https://github.com/pollen-robotics/AmazingHand
- MediaPipe Hand Landmarker