"""Track the founder's face through 1001.mp4 so every shot can be framed
consistently (eyes on the upper third). Writes edit/assets/face_track.json."""
import json
import os
import subprocess

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, FPS, STEP = 1080, 1920, 30, 3
casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", os.path.join(ROOT, "1001.mp4"), "-vf", f"fps={FPS},format=gray",
                      "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
ts, xs, ys, ss = [], [], [], []
n = 0
while True:
    buf = p.stdout.read(W * H)
    if len(buf) < W * H:
        break
    if n % STEP == 0:
        g = np.frombuffer(buf, np.uint8).reshape(H, W)
        small = cv2.resize(g, (W // 2, H // 2))
        faces = casc.detectMultiScale(small, 1.1, 6, minSize=(90, 90))
        if len(faces):
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3]) * 2
            ts.append(n / FPS); xs.append(x + w / 2); ys.append(y + h * 0.42); ss.append(w)
    n += 1
ts, xs, ys, ss = map(np.array, (ts, xs, ys, ss))
# reject outliers against a running median, then smooth (~0.8 s)
def smooth(v):
    med = np.array([np.median(v[max(0, i - 7):i + 8]) for i in range(len(v))])
    ok = np.abs(v - med) < 60
    vv = np.interp(ts, ts[ok], v[ok])
    k = 9
    return np.convolve(np.pad(vv, k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), "valid")
grid = np.arange(0, n) / FPS
out = {"fps": FPS, "cx": np.interp(grid, ts, smooth(xs)).round(1).tolist(),
       "eye": np.interp(grid, ts, smooth(ys)).round(1).tolist(), "face_w": float(np.median(ss))}
json.dump(out, open(os.path.join(ROOT, "edit", "assets", "face_track.json"), "w"))
print(len(ts), "detections /", n // STEP, "| cx", np.percentile(xs, [5, 50, 95]), "| eye", np.percentile(ys, [5, 50, 95]), "| w", np.median(ss))
