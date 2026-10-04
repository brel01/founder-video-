"""'Ibadan is Urbn' — animated campaign teaser (1080x1920).

A man shouts from Bower's Tower on Oke Aremo; a runner climbs toward him,
mishearing each time, until the message lands: Ibadan is Urbn.

    python3 ibadan/animate.py [out.mp4] | --still SEC out.png ...
"""
import math
import os
import random
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "edit"))
import render as R  # noqa: E402  (brand fonts, text, logo, phone mockup helpers)

W, H, FPS = 1080, 1920, 30
TOTAL = 28.5
SS = 2  # supersampling for the vector world
BLUE, WHITE, BLACK = R.BLUE, R.WHITE, R.BLACK
M = R.M
R.SCR["ibadan"] = "ibadan/app_ibadan.png"

ease_out, ease_in_out, prog, clamp = R.ease_out, R.ease_in_out, R.prog, R.clamp


# --------------------------------------------------------------------------- world (wide-shot coordinates)
def hill_y(x):
    return 1520 - 800 * math.exp(-((x - 600) / 420) ** 2)


PEAK = (600, hill_y(600))          # ~ (600, 700)
TOWER_H, TOWER_W = 235, 74
DECK_Y = PEAK[1] - TOWER_H         # where the shouter stands
SHOUTER = (600, DECK_Y)            # feet
MOUTH = (600, DECK_Y - 27)

PATH = [(150, 1478), (430, 1395), (250, 1290), (520, 1180), (360, 1060), (545, 935), (470, 840), (575, 742)]
_seg = [math.dist(PATH[i], PATH[i + 1]) for i in range(len(PATH) - 1)]
_plen = sum(_seg)


def path_at(u):
    d = clamp(u) * _plen
    for i, L in enumerate(_seg):
        if d <= L or i == len(_seg) - 1:
            f = clamp(d / L)
            (x0, y0), (x1, y1) = PATH[i], PATH[i + 1]
            return x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, (1 if x1 >= x0 else -1)
        d -= L


rnd = random.Random(5)
STARS = [(rnd.uniform(-300, 1400), rnd.uniform(-600, 1050), rnd.uniform(0.8, 2.2), rnd.uniform(0, 6.28)) for _ in range(170)]

# far skyline (behind the hill), incl. Cocoa House
SKY_BLD = []
x = -400
while x < 1500:
    w = rnd.randint(30, 90)
    h = rnd.randint(30, 120)
    SKY_BLD.append((x, 1385 - h, w, h))
    x += w + rnd.randint(-6, 10)
COCOA = (95, 1000, 76, 385)

# rocks and shrubs on the hillside (give the run a sense of speed)
ROCKS = []
for _ in range(420):
    x = rnd.uniform(-300, 1500)
    y = rnd.uniform(hill_y(x) + 12, 1500)
    ROCKS.append((x, y, rnd.uniform(3, 11), rnd.choice([(9, 13, 32), (13, 18, 42), (7, 10, 24)]), rnd.random() < 0.3))

# foreground zinc roofs (Ibadan's brown roofs), rows front to back
ROOFS = []
for row, (y, sc) in enumerate([(1470, 0.7), (1560, 0.85), (1665, 1.0), (1790, 1.2), (1930, 1.45)]):
    x = -500 + rnd.randint(0, 60)
    while x < 1600:
        w = int(rnd.randint(120, 210) * sc)
        h = int(rnd.randint(40, 70) * sc)
        shade = rnd.choice([(46, 26, 18), (58, 33, 21), (38, 22, 16), (52, 30, 22)])
        k = 0.55 + 0.1 * row
        ROOFS.append((row, x, y, w, h, tuple(int(c * k) for c in shade), rnd.random() < 0.35))
        x += w + rnd.randint(4, 24)


def sky_column(cy, z):
    """Per-row sky colour for the current camera."""
    sy = np.arange(H * SS) / SS
    wy = (sy - H / 2) / z + cy
    stops_y = np.array([-800, 300, 900, 1300, 1450])
    cols = np.array([(2, 3, 10), (5, 8, 26), (12, 20, 78), (34, 52, 170), (60, 80, 205)], float)
    out = np.stack([np.interp(wy, stops_y, cols[:, c]) for c in range(3)], 1)
    return out.astype(np.uint8)


class Cam:
    def __init__(self, cx, cy, z):
        self.cx, self.cy, self.z = cx, cy, z

    def P(self, x, y):
        return ((x - self.cx) * self.z + W / 2) * SS, ((y - self.cy) * self.z + H / 2) * SS

    def S(self, v):
        return v * self.z * SS


def draw_world(cam, t):
    col = sky_column(cam.cy, cam.z)
    img = Image.fromarray(np.repeat(col[:, None, :], W * SS, axis=1), "RGB").convert("RGBA")
    d = ImageDraw.Draw(img)
    # stars
    for sx, sy, r, ph in STARS:
        X, Y = cam.P(sx, sy)
        if -10 < X < W * SS + 10 and -10 < Y < H * SS + 10:
            a = int(140 + 100 * math.sin(t * 1.7 + ph))
            rr = max(1.0, cam.S(r) * 0.35 + 1)
            d.ellipse((X - rr, Y - rr, X + rr, Y + rr), fill=(255, 255, 255, a))
    # glow behind the tower
    # far skyline
    for bx, by, bw, bh in SKY_BLD:
        X0, Y0 = cam.P(bx, by)
        X1, Y1 = cam.P(bx + bw, 1400)
        d.rectangle((X0, Y0, X1, Y1), fill=(14, 21, 70))
    cx, cy, cw, ch = COCOA
    X0, Y0 = cam.P(cx, cy)
    X1, Y1 = cam.P(cx + cw, 1400)
    d.rectangle((X0, Y0, X1, Y1), fill=(16, 24, 78))
    d.rectangle(cam.P(cx + 18, cy - 40) + cam.P(cx + cw - 18, cy), fill=(16, 24, 78))
    d.line(cam.P(cx + cw / 2, cy - 90) + cam.P(cx + cw / 2, cy - 40), fill=(16, 24, 78), width=max(1, int(cam.S(3))))
    rr = random.Random(3)
    for k in range(14):
        for j in range(3):
            if rr.random() < 0.55:
                X, Y = cam.P(cx + 12 + j * 22, cy + 20 + k * 26)
                s = cam.S(5)
                d.rectangle((X, Y, X + s, Y + s * 0.7), fill=(255, 214, 150, 170))
    # hill
    pts = [cam.P(x, hill_y(x)) for x in range(-700, 1801, 10)]
    pts += [cam.P(1800, 2600), cam.P(-700, 2600)]
    d.polygon(pts, fill=(4, 6, 17))
    rim = [cam.P(x, hill_y(x) + 1) for x in range(300, 901, 6)]
    d.line(rim, fill=(60, 90, 230, 160), width=max(1, int(cam.S(2.2))))
    # rocks / shrubs
    for x, y, r, col, shrub in ROCKS:
        X, Y = cam.P(x, y)
        rr = cam.S(r)
        if -rr < X < W * SS + rr and -rr < Y < H * SS + rr:
            if shrub:
                for k in range(3):
                    d.ellipse((X - rr + k * rr * 0.6, Y - rr * 1.2, X + k * rr * 0.6, Y), fill=(10, 20, 30))
            else:
                d.ellipse((X - rr, Y - rr * 0.6, X + rr, Y + rr * 0.6), fill=col)
    # path
    pp = [cam.P(*p) for p in PATH]
    d.line(pp, fill=(18, 24, 52), width=max(2, int(cam.S(12))), joint="curve")
    d.line(pp, fill=(30, 40, 85), width=max(1, int(cam.S(3))), joint="curve")
    # Bower's Tower
    bx, by = PEAK
    tw, th = TOWER_W, TOWER_H
    body = [cam.P(bx - tw / 2, by + 6), cam.P(bx - tw / 2 + 7, by - th), cam.P(bx + tw / 2 - 7, by - th),
            cam.P(bx + tw / 2, by + 6)]
    d.polygon(body, fill=(7, 10, 26))
    d.line([cam.P(bx + tw / 2 - 7, by - th), cam.P(bx + tw / 2, by + 6)], fill=(55, 80, 210, 200),
           width=max(1, int(cam.S(2))))
    X, Y = cam.P(bx - 3, by - 40)  # door light
    d.rectangle((X, Y, X + cam.S(6), Y + cam.S(14)), fill=(255, 214, 150, 90))
    d.rectangle(cam.P(bx - tw / 2 - 12, by - th - 6) + cam.P(bx + tw / 2 + 12, by - th + 4), fill=(9, 13, 32))
    for k in range(9):  # deck railing posts
        X0, Y0 = cam.P(bx - tw / 2 - 10 + k * (tw + 20) / 8, by - th - 22)
        d.line((X0, Y0, X0, Y0 + cam.S(16)), fill=(9, 13, 32), width=max(1, int(cam.S(2))))
    d.line(cam.P(bx - tw / 2 - 12, by - th - 22) + cam.P(bx + tw / 2 + 12, by - th - 22), fill=(9, 13, 32),
           width=max(1, int(cam.S(2.5))))
    # roofs (foreground, in front of hill base)
    for row, x, y, w, h, shade, lit in ROOFS:
        a, b = cam.P(x, y)
        c_, e = cam.P(x + w, y + 260)
        top_l, top_r = cam.P(x + w * 0.18, y - h), cam.P(x + w * 0.82, y - h)
        d.polygon([(a, b), top_l, top_r, (c_, b), (c_, e), (a, e)], fill=shade + (255,))
        d.line([(a, b), top_l, top_r, (c_, b)], fill=tuple(min(255, int(v * 1.6)) for v in shade) + (255,),
               width=max(1, int(cam.S(1.5))))
        if lit:
            X, Y = cam.P(x + w * 0.4, y + 18)
            s = cam.S(9)
            d.rectangle((X, Y, X + s, Y + s * 1.2), fill=(255, 196, 120, 200))
    return img, d


# --------------------------------------------------------------------------- characters
def limb(d, cam, p, ang, L):
    x = p[0] + math.sin(ang) * L
    y = p[1] + math.cos(ang) * L
    return (x, y)


def figure(d, cam, feet, h, pose, t, face=1, color=(238, 240, 246), shirt=None):
    """Simple rounded-limb figure. pose: 'run', 'shout', 'phone', 'pant', 'cheer'."""
    th = 0.075 * h
    rad = math.radians
    lean = 0.0
    bob = 0.0
    if pose == "run":
        ph = t * 2 * math.pi * 1.6
        lean = rad(14)
        bob = abs(math.sin(ph)) * 0.04 * h
        legs = [(rad(38 * math.sin(ph)), rad(15 + 55 * max(0, math.sin(ph + 1.9)))),
                (rad(38 * math.sin(ph + math.pi)), rad(15 + 55 * max(0, math.sin(ph + math.pi + 1.9))))]
        arms = [(rad(-45 * math.sin(ph)), rad(-85)), (rad(-45 * math.sin(ph + math.pi)), rad(-85))]
    elif pose == "pant":
        ph = t * 2 * math.pi * 1.4
        lean = rad(20 + 3 * math.sin(ph))
        legs = [(rad(10), rad(18)), (rad(-12), rad(14))]
        arms = [(rad(28), rad(-10)), (rad(-6), rad(-14))]
    elif pose == "cheer":
        legs = [(rad(9), rad(3)), (rad(-9), rad(3))]
        wave = math.sin(t * 9) * 0.15
        arms = [(rad(160) + wave, rad(10)), (rad(-160) - wave, rad(-10))]
        bob = abs(math.sin(t * 6)) * 0.03 * h
    elif pose == "phone":
        legs = [(rad(7), rad(2)), (rad(-7), rad(2))]
        arms = [(rad(70), rad(-25)), (rad(-12), rad(-6))]
    else:  # shout: hands cupped at the mouth, rocking with the call
        k = math.sin(t * 2 * math.pi * 1.2)
        lean = rad(-6 + 4 * k)
        legs = [(rad(9), rad(2)), (rad(-9), rad(2))]
        arms = [(rad(150), rad(-118)), (rad(-150 + 300), rad(-118))]
    fx, fy = feet
    hip = (fx, fy - 0.5 * h - bob)
    neck = (hip[0] + math.sin(lean) * face * 0.34 * h, hip[1] - math.cos(lean) * 0.34 * h)
    head = (neck[0] + math.sin(lean) * face * 0.1 * h, neck[1] - 0.11 * h)
    W_ = max(1, int(cam.S(th)))

    def seg(a, b, w=W_, col=color):
        A, B = cam.P(*a), cam.P(*b)
        d.line([A, B], fill=col + (255,), width=w)
        r = w / 2
        for P in (A, B):
            d.ellipse((P[0] - r, P[1] - r, P[0] + r, P[1] + r), fill=col + (255,))

    for (thigh, knee) in legs:  # legs
        kp = (hip[0] + math.sin(thigh) * face * 0.25 * h, hip[1] + math.cos(thigh) * 0.25 * h)
        fp = (kp[0] + math.sin(thigh - knee) * face * 0.25 * h, kp[1] + math.cos(thigh - knee) * 0.25 * h)
        seg(hip, kp)
        seg(kp, fp)
    seg(hip, neck, int(W_ * 1.5), shirt or color)  # torso
    for (up, el) in arms:
        sh = (neck[0], neck[1] + 0.03 * h)
        ep = (sh[0] + math.sin(up) * face * 0.18 * h, sh[1] + math.cos(up) * 0.18 * h)
        hp = (ep[0] + math.sin(up + el) * face * 0.17 * h, ep[1] + math.cos(up + el) * 0.17 * h)
        seg(sh, ep, W_, shirt or color)
        seg(ep, hp)
        if pose == "phone" and up == arms[0][0]:
            P = cam.P(*hp)
            s = cam.S(0.06 * h)
            d.rounded_rectangle((P[0] - s * 0.6, P[1] - s, P[0] + s * 0.6, P[1] + s), s * 0.2, fill=(190, 210, 255))
    H_ = cam.P(*head)
    r = cam.S(0.1 * h)
    d.ellipse((H_[0] - r, H_[1] - r, H_[0] + r, H_[1] + r), fill=color + (255,))
    return head


# --------------------------------------------------------------------------- sound rings
SHOUTS = [  # (start, end, clarity 0..1)
    (0.55, 2.3, 0.08),
    (6.45, 8.1, 0.5),
    (11.75, 13.5, 1.0),
    (22.7, 24.2, 1.0),
]


def rings(d, cam, t, src, max_r=520):
    for s, e, q in SHOUTS:
        if not (s <= t < e + 1.6):
            continue
        k = 0
        ts = s
        while ts < min(t, e):
            age = t - ts
            if age < 1.6:
                r = 18 + age / 1.6 * max_r
                a = (1 - age / 1.6) ** 1.3
                col = (int(120 + 135 * q), int(150 + 105 * q), 255)
                pts = []
                n = 90
                rr = random.Random(int(ts * 100))
                gaps = set(rr.sample(range(n), int((1 - q) * 45)))
                for i in range(n + 1):
                    ang = i / n * 2 * math.pi
                    jag = (1 - q) * 0.18 * r * math.sin(ang * 7 + ts * 13) * math.sin(ang * 3 + k)
                    pts.append(cam.P(src[0] + math.cos(ang) * (r + jag), src[1] + math.sin(ang) * (r + jag) * 0.92))
                w = max(1, int(cam.S(2.2 + 2 * q)))
                for i in range(n):
                    if i in gaps:
                        continue
                    d.line([pts[i], pts[i + 1]], fill=col + (int(220 * a),), width=w)
            ts += 0.28
            k += 1


# --------------------------------------------------------------------------- overlays
def shout_text(c, t, t0, t1, q, text_full):
    """Shouter's line, top of frame: blurred/scrambled when unclear, crisp when clear."""
    if not (t0 <= t < t1):
        return
    p = ease_out(prog(t, t0, 0.35))
    if q < 0.3:
        txt = "…BA…N  …S  …RB…!"
    elif q < 0.8:
        txt = "IBA·AN IS U·BN!"
    else:
        txt = text_full
    size = 100 if q >= 0.8 else 96
    img, pad = R.T(txt, size, WHITE, R.HEAD, -0.03, "URBN!" if q >= 0.8 else None, WHITE, BLUE if q >= 0.8 else None)
    blur = (1 - q) * 9
    if blur > 0.5:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    x = (W - img.width) / 2
    y = 370 + (1 - p) * 30
    shake = (1 - q) * 6 * math.sin(t * 40)
    # echoes
    for k, (dx, a) in enumerate([(-26, 0.18), (26, 0.12)] if q < 0.9 else []):
        R.paste(c, img, x + dx * (1 + 0.3 * math.sin(t * 3)), y + k * 6, p * a)
    R.paste(c, img, x + shake, y, p * (0.55 + 0.45 * q))


def runner_line(c, t, t0, t1, line, sub, strike=None, t_strike=None):
    if not (t0 <= t < t1):
        return
    p = ease_out(prog(t, t0, 0.3))
    y = 1270
    w = R.put_text(c, line, M, y, 84, t, t0, WHITE, R.HEAD, -0.035)
    R.put_text(c, sub, M, y + 112, 40, t, t0 + 0.12, (190, 196, 220), R.BODYM, 0)
    if strike and t_strike and t >= t_strike:
        f = R.font(R.HEAD, 84)
        tr = -0.035 * 84
        i = line.index(strike)
        x0 = M + f.getlength(line[:i]) + tr * i
        x1 = M + f.getlength(line[:i + len(strike)]) + tr * (i + len(strike) - 1)
        q = ease_out(prog(t, t_strike, 0.25))
        d = ImageDraw.Draw(c)
        d.line((x0 - 6, y + 58, x0 - 6 + (x1 - x0 + 12) * q, y + 52), fill=BLUE + (255,), width=12)


def label(c, t, t0, text):
    d = ImageDraw.Draw(c)
    pk = ease_out(prog(t, t0, 0.4))
    d.rectangle((M, 286, M + 26, 312), fill=BLUE + (int(255 * pk),))
    R.put_text(c, text, M + 46, 280, 34, t, t0, WHITE, R.BODY, 0.12)


# --------------------------------------------------------------------------- timeline
U_KEYS = ([0, 3.2, 6.2, 9.0, 11.6, 14.2, 17.0, 17.9], [0.0, 0.04, 0.24, 0.33, 0.5, 0.6, 0.93, 1.0])


def runner_u(t):
    return float(np.interp(t, *U_KEYS))


def runner_feet(t):
    x, y, face = path_at(runner_u(t))
    if t >= 17.9:  # stands at the tower base, facing the tower
        return (x, y), 1
    return (x, y), face


SHOTS = [  # (start, end, kind)
    (0.0, 3.2, "wide"),
    (3.2, 6.2, "runner"),
    (6.2, 9.0, "shouter"),
    (9.0, 11.6, "runner"),
    (11.6, 14.2, "shouter_med"),
    (14.2, 17.0, "runner"),
    (17.0, 18.8, "top"),
    (18.8, 21.0, "phone"),
    (21.0, 22.6, "runner_end"),
    (22.6, 24.6, "wide_end"),
    (24.6, TOTAL, "endcard"),
]


def camera(kind, t, s, e):
    p = ease_in_out(prog(t, s, e - s))
    if kind == "wide":
        return Cam(560, 1010 - 40 * p, 1.0 + 0.1 * p)
    if kind in ("runner", "runner_end"):
        (x, y), _ = runner_feet(t)
        return Cam(x + 10, y - 40, 7.0 + 0.5 * p)
    if kind == "shouter":
        return Cam(SHOUTER[0], SHOUTER[1] - 32, 6.0 + 0.5 * p)
    if kind == "shouter_med":
        return Cam(SHOUTER[0], SHOUTER[1] - 30, 3.2 + 0.3 * p)
    if kind == "top":
        return Cam(590, 600, 4.4 + 0.2 * p)
    if kind == "wide_end":
        return Cam(580, 960 + 40 * (1 - p), 1.12 - 0.1 * p)
    return Cam(540, 960, 1.0)


def shouter_pose(t):
    if 17.4 <= t < 21.0:
        return "phone"
    if t >= 22.4:
        return "cheer"
    return "shout"


def scene(t, kind, s, e):
    cam = camera(kind, t, s, e)
    img, d = draw_world(cam, t)
    # shout rings from the deck
    rings(d, cam, t, MOUTH, 560 if kind.startswith("wide") else 300)
    # shouter
    figure(d, cam, SHOUTER, 34, shouter_pose(t), t, face=-1 if t >= 17.4 and t < 22.4 else 1,
           color=(250, 250, 252), shirt=BLUE)
    # runner
    (fx, fy), face = runner_feet(t)
    if t < 17.9:
        pose = "run"
    elif t < 21.2:
        pose = "pant"
    elif t < 22.4:
        pose = "pant" if t < 21.6 else "cheer"
    else:
        pose = "cheer"
    figure(d, cam, (fx, fy), 34, pose, t, face=face, color=(232, 234, 240), shirt=(200, 204, 214))
    if kind == "top" and t >= 17.4:  # phone glow
        X, Y = cam.P(SHOUTER[0] - 14, SHOUTER[1] - 22)
        g = R.glow(int(cam.S(16)), (140, 170, 255), 0.7 * ease_out(prog(t, 17.4, 0.6)))
        img.alpha_composite(g, (int(X - g.width / 2), int(Y - g.height / 2)))
    img = img.resize((W, H), Image.LANCZOS)
    return img


def frame(t):
    for s, e, kind in SHOTS:
        if s <= t < e:
            break
    if kind == "phone":
        return phone_insert(t, s, e)
    if kind == "endcard":
        return endcard(t, s)
    c = scene(t, kind, s, e)
    c.alpha_composite(R.grad_top(0.3, 0.55))
    c.alpha_composite(R.grad_bottom(0.6, 0.65))
    if kind == "wide":
        label(c, t, 0.2, "OKE AREMO, IBADAN")
    # dialogue
    shout_text(c, t, 0.7, 3.2, 0.08, "")
    runner_line(c, t, 3.45, 6.2, "Oga! Wetin you dey talk?!", "Bro! What are you saying?!")
    shout_text(c, t, 6.55, 9.0, 0.5, "")
    runner_line(c, t, 9.2, 11.6, "Ibadan na… TURBO??", "Ibadan is… turbo??", strike="TURBO??", t_strike=10.6)
    shout_text(c, t, 11.8, 14.2, 1.0, "IBADAN IS URBN!")
    runner_line(c, t, 14.4, 17.0, "Ibadan na URBAN?!", "Ibadan is urban?! Since when?!")
    if kind == "top":
        R.put_text(c, "*huff* *huff*", M, 1290, 46, t, 17.3, (190, 196, 220), R.BODYM, 0)
    runner_line(c, t, 21.05, 22.6, "Ahhh… Ibadan is Urbn!", "Ahhh… Ibadan is Urbn!")
    shout_text(c, t, 22.75, 24.6, 1.0, "IBADAN IS URBN!")
    if kind == "wide_end" and t >= 23.3:  # the chain: someone in the city shouts it on
        p = ease_out(prog(t, 23.3, 0.5))
        R.put_text(c, "…ibadan is urbn!", 700, 1560, 36, t, 23.3, (200, 205, 230), R.BODYM, 0, align="center")
    return c.convert("RGB")


def phone_insert(t, s, e):
    c = R.solid(BLACK)
    wm = R.watermark((26, 26, 26), 1.0)
    R.paste(c, wm, 330 - (t - s) * 14, 520)
    p = ease_out(prog(t, s, 0.7))
    z = 1.0 + 0.35 * ease_in_out(prog(t, s + 0.8, 1.3))
    ph, pad = R.phone("ibadan", 700)
    phz = R.scaled(ph, z)
    # zoom toward the city card (upper part of the screen)
    cx = W / 2
    top = 330 + (1 - p) * 300 - (z - 1) * 520
    R.paste(c, phz, cx - phz.width / 2, top - pad * z, min(1, p * 1.5))
    d = ImageDraw.Draw(c)
    d.rectangle((M, 286, M + 26, 312), fill=BLUE + (int(255 * p),))
    R.put_text(c, "NOW IN YOUR CITY", M + 46, 280, 34, t, s, WHITE, R.BODY, 0.12)
    return c.convert("RGB")


def endcard(t, s):
    c = R.bg_card(BLACK, (28, 28, 28), 1.0, t, s)
    R.top_bar(c, t, s)
    R.put_text(c, "Ibadan", M, 640, 190, t, s + 0.1, WHITE, R.HEAD, -0.05)
    R.put_text(c, "is Urbn.", M, 840, 190, t, s + 0.35, WHITE, R.HEAD, -0.05, hl="Urbn.", hl_color=WHITE, hl_bg=BLUE)
    R.put_text(c, "Find, rent and manage homes in Ibadan.", M, 1130, 46, t, s + 0.9, (200, 200, 208), R.BODY, -0.01)
    R.put_text(c, "#IbadanIsUrbn", M, 1215, 46, t, s + 1.2, BLUE if False else (120, 150, 255), R.BODY, 0)
    R.bottom_rule(c, t, s)
    fade = prog(t, TOTAL - 0.8, 0.8)
    if fade > 0:
        c.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fade))))
    return c.convert("RGB")


def main():
    a = sys.argv[1:]
    if a and a[0] == "--still":
        for i in range(1, len(a), 2):
            frame(float(a[i])).save(a[i + 1])
        return
    out = a[0] if a else os.path.join(HERE, "video_only.mp4")
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                            "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for n in range(int(TOTAL * FPS)):
        enc.stdin.write(frame(n / FPS).tobytes())
        if n % 90 == 0:
            print(f"  {n / FPS:5.1f}s", flush=True)
    enc.stdin.close()
    enc.wait()


if __name__ == "__main__":
    main()
