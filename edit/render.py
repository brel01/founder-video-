"""Urbn founder film — frame renderer.

Decodes the founder take (1001.mp4), composites brand graphics, product
screens and typography on top, and pipes frames to ffmpeg.

    python3 edit/render.py [out.mp4] [--from SEC --to SEC] [--still SEC out.png]
"""
import glob
import json
import math
import os
import random
import subprocess
import sys
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "edit", "fonts")
W, H, FPS = 1080, 1920, 30
SRC = os.path.join(ROOT, "1001.mp4")
SRC_DUR = 78.69
TOTAL = 84.2

# Brand palette (URBN Visual Identity Guide)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (37, 61, 226)        # #253DE2
GREY = (168, 168, 168)
SUCCESS = (18, 183, 106)    # #12B76A
OFFWHITE = (230, 230, 230)

M = 90  # outer margin
OFFSET = 0.85  # trim the dead air before the founder's first word

# Instagram Reels safe zone (1080x1920): UI covers the top ~246 px, everything
# below ~1535 px, and a button column right of x~886 from y~861 down.
SAFE_TOP, SAFE_BOTTOM, SAFE_RIGHT = 250, 1535, 880


# --------------------------------------------------------------------------- utils
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(p):
    p = clamp(p)
    return 1 - (1 - p) ** 3


def ease_in_out(p):
    p = clamp(p)
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def prog(t, t0, dur):
    return clamp((t - t0) / dur)


@lru_cache(None)
def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


HEAD = "InterDisplay-Bold.ttf"     # stand-in for Creato Display Bold (headlines)
HEAD2 = "InterDisplay-SemiBold.ttf"
BODY = "Inter-SemiBold.ttf"         # Inter Semi Bold (H2 / body), per guide
BODYM = "Inter-Medium.ttf"


def asset(path):
    # Some filenames carry macOS narrow no-break spaces; resolve by glob.
    hits = glob.glob(os.path.join(ROOT, path))
    return hits[0] if hits else os.path.join(ROOT, path)


def load_rgba(path):
    im = Image.open(asset(path)).convert("RGBA")
    a = np.array(im)[..., 3]
    ys, xs = np.where(a > 8)
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def tint(im, color, alpha=1.0):
    a = im.getchannel("A")
    if alpha < 1:
        a = a.point(lambda v: int(v * alpha))
    out = Image.new("RGBA", im.size, color + (0,))
    out.putalpha(a)
    return out


def fit_w(im, w):
    return im.resize((int(w), int(round(im.height * w / im.width))), Image.LANCZOS)


def fit_h(im, h):
    return im.resize((int(round(im.width * h / im.height)), int(h)), Image.LANCZOS)


def paste(canvas, im, x, y, alpha=1.0):
    """Alpha-composite an RGBA sprite at float position with opacity."""
    if alpha <= 0.002:
        return
    if alpha < 0.999:
        a = im.getchannel("A").point(lambda v: int(v * alpha))
        im = im.copy()
        im.putalpha(a)
    canvas.alpha_composite(im, (int(round(x)), int(round(y))))


def scaled(im, s):
    if abs(s - 1) < 1e-3:
        return im
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BICUBIC)


def rounded_mask(size, r, ss=3):
    w, h = size
    m = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), r * ss, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def solid(color, size=(W, H)):
    return Image.new("RGBA", size, color + (255,))


# --------------------------------------------------------------------------- text
def text_line(runs, size, fontname=HEAD, track=-0.035, pad_hl=None):
    """Render one line of rich text.

    runs: list of (text, color) or (text, color, highlight_rgb).
    Returns RGBA image whose height is the font's line box.
    """
    f = font(fontname, size)
    tr = track * size
    asc, desc = f.getmetrics()
    full = "".join(r[0] for r in runs)
    total_w = int(f.getlength(full) + tr * max(0, len(full) - 1)) + 4
    padx = pad_hl or int(size * 0.14)
    img = Image.new("RGBA", (total_w + 2 * padx, asc + desc + int(size * 0.1)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # highlight boxes first
    i = 0
    for r in runs:
        if len(r) > 2 and r[2] is not None:
            x0 = f.getlength(full[:i]) + tr * i
            x1 = f.getlength(full[: i + len(r[0])]) + tr * (i + len(r[0]) - 1)
            top = asc - f.getbbox("H")[1] * 0 - int(size * 0.80)
            d.rectangle((padx + x0 - padx * 0.55, top - size * 0.06,
                         padx + x1 + padx * 0.55, asc + size * 0.16), fill=r[2] + (255,))
        i += len(r[0])
    i = 0
    for r in runs:
        for ch in r[0]:
            x = f.getlength(full[:i]) + tr * i
            d.text((padx + x, 0), ch, font=f, fill=r[1] + (255,))
            i += 1
    return img, padx


@lru_cache(None)
def T(text, size, color=WHITE, fontname=HEAD, track=-0.035, hl=None, hl_color=None, hl_bg=None):
    """Cached single-line text. `hl` marks a substring drawn in hl_color / on hl_bg."""
    if hl and hl in text:
        a, b = text.split(hl, 1)
        runs = []
        if a:
            runs.append((a, color))
        runs.append((hl, hl_color or color, hl_bg))
        if b:
            runs.append((b, color))
    else:
        runs = [(text, color)]
    img, padx = text_line(runs, size, fontname, track)
    return img, padx


def put_text(canvas, text, x, y, size, t=None, t0=None, color=WHITE, fontname=HEAD, track=-0.035,
             hl=None, hl_color=None, hl_bg=None, dur=0.5, alpha=1.0, align="left", rise=True):
    """Draw text with a masked rise-in reveal starting at t0. (x,y)=left/top of the glyph box."""
    img, padx = T(text, size, color, fontname, track, hl, hl_color, hl_bg)
    if align == "center":
        x = x - (img.width - 2 * padx) / 2
    elif align == "right":
        x = x - (img.width - 2 * padx)
    x -= padx
    if t is None or t0 is None:
        paste(canvas, img, x, y, alpha)
        return img.width - 2 * padx
    p = ease_out(prog(t, t0, dur))
    if p <= 0:
        return img.width - 2 * padx
    if rise:
        h = img.height
        dy = (1 - p) * h * 0.9
        vis = int(h - dy)
        if vis > 0:
            paste(canvas, img.crop((0, 0, img.width, vis)), x, y + dy, alpha * min(1, p * 1.6))
    else:
        paste(canvas, img, x, y, alpha * p)
    return img.width - 2 * padx


# --------------------------------------------------------------------------- assets
LOGO_W = load_rgba("urbn logos/Urbn logo White.png")
LOGO_B = load_rgba("urbn logos/Urbn logo black.png")
ICON = load_rgba("urbn logos/Urbn logo Icon white.png")

LOGO_W_SMALL = fit_h(tint(LOGO_W, WHITE), 54)
LOGO_B_SMALL = fit_h(tint(LOGO_B, BLACK), 54)

SCR = {
    "home_lagos": "app screens/Screenshot 2026-10-03 at 12.04.45*",
    "otp": "app screens/Screenshot 2026-10-03 at 12.05.00*",
    "home_ph": "app screens/Simulator Screenshot - iPhone 16 Plus - 2026-09-29 at 23.38.38.png",
    "dashboard": "app screens/Simulator Screenshot - iPhone 16 Plus - 2026-09-29 at 23.43.13.png",
    "listings": "app screens/Simulator Screenshot - iPhone 16 Plus - 2026-09-29 at 23.43.20.png",
}


@lru_cache(None)
def phone(key, w):
    """Phone mockup: screenshot inside a black bezel with soft shadow."""
    shot = Image.open(asset(SCR[key])).convert("RGB")
    sw = int(w * 0.94)
    sh = int(round(shot.height * sw / shot.width))
    shot = shot.resize((sw, sh), Image.LANCZOS).convert("RGBA")
    shot.putalpha(rounded_mask((sw, sh), int(sw * 0.115)))
    bz = (w - sw) // 2
    bw, bh = w, sh + 2 * bz
    body = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    body_fill = Image.new("RGBA", (bw, bh), (14, 14, 16, 255))
    body_fill.putalpha(rounded_mask((bw, bh), int(sw * 0.115) + bz))
    body.alpha_composite(body_fill)
    rim = Image.new("RGBA", (bw * 3, bh * 3), (0, 0, 0, 0))
    ImageDraw.Draw(rim).rounded_rectangle((2, 2, bw * 3 - 3, bh * 3 - 3), (int(sw * 0.115) + bz) * 3,
                                          outline=(90, 92, 100, 255), width=5)
    body.alpha_composite(rim.resize((bw, bh), Image.LANCZOS))
    body.alpha_composite(shot, (bz, bz))
    pad = 80
    out = Image.new("RGBA", (bw + 2 * pad, bh + 2 * pad), (0, 0, 0, 0))
    sh_ = Image.new("RGBA", out.size, (0, 0, 0, 0))
    sh_m = Image.new("L", out.size, 0)
    ImageDraw.Draw(sh_m).rounded_rectangle((pad, pad + 30, pad + bw, pad + bh + 20), 80, fill=150)
    sh_.putalpha(sh_m.filter(ImageFilter.GaussianBlur(36)))
    out.alpha_composite(sh_)
    out.alpha_composite(body, (pad, pad))
    return out, pad


@lru_cache(None)
def property_card(w):
    shot = Image.open(asset(SCR["dashboard"])).convert("RGB")
    card = shot.crop((40, 390, 1250, 1034))
    card = fit_w(card, w).convert("RGBA")
    card.putalpha(rounded_mask(card.size, int(w * 0.045)))
    pad = 70
    out = Image.new("RGBA", (card.width + 2 * pad, card.height + 2 * pad), (0, 0, 0, 0))
    m = Image.new("L", out.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((pad, pad + 24, pad + card.width, pad + card.height + 16), 40, fill=110)
    sh = Image.new("RGBA", out.size, (0, 0, 0, 255))
    sh.putalpha(m.filter(ImageFilter.GaussianBlur(30)))
    out.alpha_composite(sh)
    out.alpha_composite(card, (pad, pad))
    return out, pad


@lru_cache(None)
def founder_photo(name):
    im = Image.open(asset(f"founder pictures/{name}")).convert("RGB")
    s = H * 1.12 / im.height
    return im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)


@lru_cache(None)
def watermark(color, alpha, h=1500):
    return fit_h(tint(ICON, color, alpha), h)


@lru_cache(None)
def vignette(strength=0.55):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    nx, ny = (x - W / 2) / (W / 2), (y - H * 0.45) / (H / 2)
    r = np.sqrt(nx ** 2 * 0.9 + ny ** 2 * 0.7)
    a = np.clip((r - 0.55) / 0.75, 0, 1) ** 1.6 * strength
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    im.putalpha(Image.fromarray((a * 255).astype(np.uint8)))
    return im


@lru_cache(None)
def grad_bottom(start=0.5, strength=0.85, color=(2, 3, 8)):
    y = np.linspace(0, 1, H, dtype=np.float32)
    a = np.clip((y - start) / (1 - start), 0, 1) ** 1.3 * strength
    a = np.repeat(a[:, None], W, axis=1)
    im = Image.new("RGBA", (W, H), color + (0,))
    im.putalpha(Image.fromarray((a * 255).astype(np.uint8)))
    return im


@lru_cache(None)
def grad_top(end=0.35, strength=0.85, color=(2, 3, 8)):
    y = np.linspace(0, 1, H, dtype=np.float32)
    a = np.clip(1 - y / end, 0, 1) ** 1.3 * strength
    a = np.repeat(a[:, None], W, axis=1)
    im = Image.new("RGBA", (W, H), color + (0,))
    im.putalpha(Image.fromarray((a * 255).astype(np.uint8)))
    return im


@lru_cache(None)
def dot(r, color, ss=4, ring=0):
    s = int(r * 2 * ss + 4)
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if ring:
        d.ellipse((2, 2, s - 3, s - 3), outline=color + (255,), width=ring * ss)
    else:
        d.ellipse((2, 2, s - 3, s - 3), fill=color + (255,))
    return im.resize((s // ss, s // ss), Image.LANCZOS)


@lru_cache(None)
def glow(r, color, a=0.55):
    s = int(r * 4)
    im = Image.new("RGBA", (s, s), color + (0,))
    m = Image.new("L", (s, s), 0)
    ImageDraw.Draw(m).ellipse((s / 4, s / 4, 3 * s / 4, 3 * s / 4), fill=int(255 * a))
    im.putalpha(m.filter(ImageFilter.GaussianBlur(r / 2)))
    return im


@lru_cache(None)
def check_badge(text, bg=SUCCESS, size=40):
    f = font(BODY, size)
    tw = f.getlength(text)
    h = int(size * 2.1)
    w = int(tw + h * 1.45)
    ss = 3
    im = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), h * ss // 2, fill=bg + (255,))
    cx, cy = int(h * 0.62 * ss), h * ss // 2
    k = size * 0.32 * ss
    d.line([(cx - k, cy), (cx - k * 0.3, cy + k * 0.7), (cx + k, cy - k * 0.75)], fill=WHITE + (255,),
           width=int(size * 0.13 * ss), joint="curve")
    im = im.resize((w, h), Image.LANCZOS)
    ImageDraw.Draw(im).text((int(h * 1.08), h / 2), text, font=f, fill=WHITE + (255,), anchor="lm")
    return im


@lru_cache(None)
def pill(text, size=44, bg=(255, 255, 255), fg=BLACK, accent=BLUE):
    f = font(BODY, size)
    tw = f.getlength(text)
    h = int(size * 2.0)
    w = int(tw + h * 1.25)
    ss = 3
    im = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), int(h * ss * 0.32), fill=bg + (240,))
    r = size * 0.2 * ss
    cx, cy = h * 0.5 * ss, h * ss / 2
    d.rectangle((cx - r, cy - r, cx + r, cy + r), fill=accent + (255,))
    im = im.resize((w, h), Image.LANCZOS)
    ImageDraw.Draw(im).text((int(h * 0.82), h / 2), text, font=f, fill=fg + (255,), anchor="lm")
    return im


# --------------------------------------------------------------------------- brand furniture
def top_bar(c, t, t0, dark=True):
    """Guide-style header: wordmark, hairline, blue + grey squares."""
    p = ease_out(prog(t, t0, 0.7))
    logo = LOGO_W_SMALL if dark else LOGO_B_SMALL
    y = 272
    paste(c, logo, M, y, p)
    d = ImageDraw.Draw(c)
    x0, x1 = M + logo.width + 60, W - M - 110
    lc = (255, 255, 255, int(150 * p)) if dark else (37, 61, 226, int(255 * p))
    d.line((x0, y + 28, x0 + (x1 - x0) * p, y + 28), fill=lc, width=2)
    d.rectangle((W - M - 88, y + 9, W - M - 50, y + 47), fill=BLUE + (int(255 * p),))
    d.rectangle((W - M - 38, y + 9, W - M, y + 47), fill=GREY + (int(255 * p),))


def bottom_rule(c, t, t0, dark=True, y=1490):
    p = ease_out(prog(t, t0 + 0.2, 0.8))
    d = ImageDraw.Draw(c)
    d.rectangle((M, y - 19, M + 38, y + 19), fill=BLUE + (int(255 * p),))
    lc = (255, 255, 255, int(150 * p)) if dark else (37, 61, 226, int(255 * p))
    d.line((M + 70, y, M + 70 + (W - 2 * M - 70) * p, y), fill=lc, width=2)


def bg_card(color, wm_color, wm_alpha, t, t0, wm_x=330, wm_y=520):
    c = solid(color)
    wm = watermark(wm_color, wm_alpha)
    drift = (t - t0) * -14
    paste(c, wm, wm_x + drift, wm_y)
    return c


# --------------------------------------------------------------------------- footage
class Footage:
    def __init__(self):
        grade = ("eq=contrast=1.06:brightness=-0.015:saturation=0.9:gamma=0.98,"
                 "colorbalance=rs=-0.02:bs=0.04:rh=0.02:bh=-0.01")
        self.p = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-i", SRC, "-vf", f"fps={FPS},{grade},format=rgb24",
             "-f", "rawvideo", "-"], stdout=subprocess.PIPE, bufsize=W * H * 3 * 2)
        self.idx = -1
        self.cur = None

    def get(self, t):
        want = min(int(round(t * FPS)), int(SRC_DUR * FPS) - 2)
        while self.idx < want:
            buf = self.p.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                break
            self.cur = buf
            self.idx += 1
        return Image.frombuffer("RGB", (W, H), self.cur, "raw", "RGB", 0, 1)


FACE = (540, 760)
TRACK = json.load(open(os.path.join(ROOT, "edit", "assets", "face_track.json")))
MED, CLOSE = 1.18, 1.36   # the only two framings used for the founder


def face_at(t):
    i = min(len(TRACK["eye"]) - 1, max(0, int(round(t * TRACK["fps"]))))
    return TRACK["cx"][i], TRACK["eye"][i]


def zoomed(img, z, cx=FACE[0], cy=FACE[1]):
    w, h = W / z, H / z
    x0 = clamp(cx - w / 2, 0, W - w)
    y0 = clamp(cy - h / 2, 0, H - h)
    return img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h)).convert("RGBA")


def founder(img, t, t0, z0, z1=None, dur=None):
    """Founder footage framed on his eyes (upper third, same height in every
    shot), with a slow push from z0 toward z1 anchored on the eyes."""
    if z1 is None:
        z1 = z0 * 1.03
    dur = dur or 4.0
    z = z0 + (z1 - z0) * ease_in_out(prog(t, t0, dur))
    fx, eye = face_at(t)
    eye_screen = 640 if z0 < 1.3 else 625
    cy = eye - (eye_screen - H / 2) / z
    cx = 540 + (fx - 540) * 0.85
    c = zoomed(img, z, cx, cy)
    c.alpha_composite(vignette())
    return c


# --------------------------------------------------------------------------- captions
CAPTIONS = [  # "|" marks a hand-set line break; lines are timed by length
    (0.95, 2.95, "You can order food | from your phone.", "order food"),
    (6.62, 9.0, "But when it comes to | renting a house in Nigeria…", "renting a house"),
    (16.30, 18.62, "I know this because | I've gone through it.", "gone through it."),
    (18.72, 21.62, "And that's when I started | asking the bigger question.", "bigger question."),
    (33.03, 35.55, "Property owners are | juggling tenants,", "juggling"),
    (35.66, 38.30, "managers, records | and payments", None),
    (38.36, 39.95, "across different places.", "different places."),
    (40.07, 43.80, "And we keep trying to fix | each problem separately.", "separately."),
    (44.90, 47.95, "We think there's a bigger | problem to solve first.", "first."),
    (64.38, 68.22, "And eventually, | your property is no longer | just a building.", "just a building."),
    (73.50, 75.72, "That's what we're | building at Urbn —", "Urbn"),
]

CAP_SIZE = 58
CAP_X = M
CAP_MAXW = SAFE_RIGHT - M - 20
CAP_Y = 1405   # every caption sits on this one line, inside the safe zone


def _chunks():
    """Split each caption into single lines that fit the safe width, timed by length."""
    f = font(BODY, CAP_SIZE)
    out = []
    for s0, e0, text, hl in CAPTIONS:
        if "|" in text:
            parts = [x.strip().split(" ") for x in text.split("|")]
            text = " ".join(" ".join(x) for x in parts)
        else:
            parts = None
        words = text.split(" ")
        hlw = set()
        if hl:
            hw = hl.split(" ")
            for i in range(len(words) - len(hw) + 1):
                if words[i:i + len(hw)] == hw:
                    hlw = set(range(i, i + len(hw)))
        if parts:
            lines, k = [], 0
            for x in parts:
                lines.append(list(range(k, k + len(x))))
                k += len(x)
            n = None
        # balanced line breaks: n lines of roughly equal width
        full = f.getlength(text)
        n = max(1, math.ceil(full / CAP_MAXW))
        while not parts:
            target = full / n
            lines, cur = [], []
            for i in range(len(words)):
                trial = f.getlength(" ".join(words[j] for j in cur + [i]))
                if cur and (trial > CAP_MAXW or (trial > target * 1.08 and len(lines) < n - 1)):
                    lines.append(cur)
                    cur = [i]
                else:
                    cur.append(i)
            lines.append(cur)
            if all(f.getlength(" ".join(words[j] for j in ln)) <= CAP_MAXW for ln in lines):
                break
            n += 1
        total = sum(len(" ".join(words[i] for i in ln)) for ln in lines)
        t = s0
        for ln in lines:
            n = len(" ".join(words[i] for i in ln))
            dt = (e0 - s0) * n / total
            out.append((t, t + dt, tuple(words[i] for i in ln), tuple(i in hlw for i in ln)))
            t += dt
    return out


@lru_cache(None)
def caption_img(words, hls):
    f = font(BODY, CAP_SIZE)
    lh = int(CAP_SIZE * 1.42)
    img = Image.new("RGBA", (W, lh + 40), (0, 0, 0, 0))
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d, ds = ImageDraw.Draw(img), ImageDraw.Draw(shadow)
    txt = " ".join(words)
    x, y = CAP_X, 20
    if any(hls):
        a = hls.index(True)
        b = len(hls) - hls[::-1].index(True)
        pre = " ".join(words[:a])
        hx = x + (f.getlength(pre + " ") if pre else 0)
        d.rectangle((hx - 12, y + 2, hx + f.getlength(" ".join(words[a:b])) + 12, y + lh - 6), fill=BLUE + (255,))
    ds.text((x, y + 6), txt, font=f, fill=(0, 0, 0, 210))
    d.text((x, y + 4), txt, font=f, fill=WHITE + (255,))
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    shadow.alpha_composite(img)
    return shadow


CAP_CHUNKS = None


def draw_captions(c, t):
    global CAP_CHUNKS
    if CAP_CHUNKS is None:
        CAP_CHUNKS = _chunks()
    for s0, e0, words, hls in CAP_CHUNKS:
        if s0 <= t < e0:
            im = caption_img(words, hls)
            p = ease_out(prog(t, s0, 0.12))
            paste(c, im, 0, CAP_Y - 20 + (1 - p) * 10, p)


def kicker(c, t, t0, text, y=SAFE_TOP + 30, dark=True):
    d = ImageDraw.Draw(c)
    pk = ease_out(prog(t, t0, 0.4))
    d.rectangle((M, y + 6, M + 26, y + 32), fill=BLUE + (int(255 * pk),))
    put_text(c, text, M + 46, y, 34, t, t0, WHITE if dark else BLACK, BODY, 0.12)


# --------------------------------------------------------------------------- scenes
def s_hook(t, img):
    """0.85–6.62  Open on the founder's face, then two quick brand cards."""
    if t < 2.95:
        c = founder(img, t, OFFSET, MED, MED * 1.04, 2.1)
        c.alpha_composite(grad_bottom(0.62, 0.7))
        c.alpha_composite(grad_top(0.22, 0.6))
        kicker(c, t, OFFSET, "WHY I'M BUILDING URBN")
        bt = 1.75
        if t >= bt:
            b = check_badge("Order placed")
            pb = ease_out(prog(t, bt, 0.35))
            paste(c, scaled(b, 0.85 + 0.15 * pb), M, CAP_Y - 110 + (1 - pb) * 20, pb)
        draw_captions(c, t)
        return c
    cards = [
        (2.95, 4.28, BLUE, (255, 255, 255), 0.13, "Send money", "in seconds.", "₦250,000 sent", WHITE, (205, 212, 255)),
        (4.28, 6.62, WHITE, (225, 225, 225), 1.0, "Book a flight", "without talking to anyone.", "Flight confirmed", BLACK, (110, 110, 110)),
    ]
    for i, (s, e, bg, wmc, wma, big, sub, badge, fg, subc) in enumerate(cards):
        if s <= t < e:
            c = bg_card(bg, wmc, wma, t, s)
            ts = s
            d = ImageDraw.Draw(c)
            # index marker
            pm = ease_out(prog(t, ts, 0.4))
            d.rectangle((M, 300, M + 34, 334), fill=(BLUE if bg != BLUE else WHITE) + (int(255 * pm),))
            put_text(c, f"0{i + 2}", M + 58, 293, 40, t, ts, fg, BODY, 0)
            put_text(c, big, M, 760, 148, t, ts, fg, HEAD, -0.045)
            put_text(c, sub, M, 945, 58, t, ts + 0.12, subc, BODYM, -0.01)
            bt = ts + 0.55
            if t >= bt:
                b = check_badge(badge)
                pb = ease_out(prog(t, bt, 0.35))
                paste(c, scaled(b, 0.85 + 0.15 * pb), M, 1110 + (1 - pb) * 30, pb)
            return c
    return solid(BLACK)


def s_founder_cut(t, img, t0, z0, z1=None, dur=None):
    c = founder(img, t, t0, z0, z1, dur)
    c.alpha_composite(grad_bottom(0.62, 0.7))
    draw_captions(c, t)
    return c


# --- street map -------------------------------------------------------------
MAP_W, MAP_H = 2400, 4300
XS = [80, 400, 760, 1090, 1440, 1780, 2110, 2350]
YS = [y + 560 for y in [120, 470, 850, 1230, 1600, 1990, 2360, 2740, 3120, 3480]]
ROAD = 30
PATH = [(1, 9), (1, 7), (3, 7), (3, 5), (5, 5), (5, 3), (3, 3), (3, 1)]


def _build_map():
    rnd = random.Random(7)
    im = Image.new("RGBA", (MAP_W, MAP_H), (6, 8, 15, 255))
    d = ImageDraw.Draw(im)
    houses = []
    for xi in range(len(XS) - 1):
        for yi in range(len(YS) - 1):
            bx0, bx1 = XS[xi] + ROAD, XS[xi + 1] - ROAD
            by0, by1 = YS[yi] + ROAD, YS[yi + 1] - ROAD
            y = by0 + 14
            while y < by1 - 70:
                hh = rnd.randint(60, 100)
                x = bx0 + 14
                while x < bx1 - 60:
                    hw = rnd.randint(60, 120)
                    if x + hw > bx1 - 14:
                        break
                    if y + hh > by1 - 14:
                        break
                    shade = rnd.choice([(20, 25, 40), (24, 30, 48), (17, 21, 34)])
                    d.rectangle((x, y, x + hw, y + hh), fill=shade + (255,))
                    houses.append((x, y, hw, hh))
                    x += hw + rnd.randint(14, 26)
                y += hh + rnd.randint(14, 26)
    for x in XS:
        d.rectangle((x - ROAD // 2, 0, x + ROAD // 2, MAP_H), fill=(12, 15, 26, 255))
        d.line((x, 0, x, MAP_H), fill=(28, 34, 54, 255), width=2)
    for y in YS:
        d.rectangle((0, y - ROAD // 2, MAP_W, y + ROAD // 2), fill=(12, 15, 26, 255))
        d.line((0, y, MAP_W, y), fill=(28, 34, 54, 255), width=2)
    return im, houses


MAP, HOUSES = None, None
PTS = [(XS[a], YS[b]) for a, b in PATH]
SEGL = [math.dist(PTS[i], PTS[i + 1]) for i in range(len(PTS) - 1)]
PLEN = sum(SEGL)


def path_at(u):
    dist = u * PLEN
    for i, L in enumerate(SEGL):
        if dist <= L or i == len(SEGL) - 1:
            f = clamp(dist / L)
            (x0, y0), (x1, y1) = PTS[i], PTS[i + 1]
            return x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, i
        dist -= L


MAP_T0, MAP_T1 = 9.10, 16.25
WALK0, WALK1 = 9.15, 16.0
ASK_TIMES = [11.45, 12.25, 12.95, 13.75, 14.6, 15.3]


def walk_u(t):
    q = prog(t, WALK0, WALK1 - WALK0)
    return ease_in_out(q) * 0.6 + 0.4 * q


def s_map(t, img):
    global MAP, HOUSES
    if MAP is None:
        MAP, HOUSES = _build_map()
    u = walk_u(t)
    px, py, seg = path_at(u)
    # camera: follows walker, gentle zoom-out across the scene
    z = 1.18 - 0.16 * ease_in_out(prog(t, MAP_T0, MAP_T1 - MAP_T0))
    cw, ch = W / z, H / z
    cx = clamp(px, cw / 2, MAP_W - cw / 2)
    cy = clamp(py - 260, ch / 2, MAP_H - ch / 2)
    x0, y0 = cx - cw / 2, cy - ch / 2
    c = MAP.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
    d = ImageDraw.Draw(c)

    def S(x, y):
        return (x - x0) * z, (y - y0) * z

    # trail
    pts = []
    acc = 0
    for i, L in enumerate(SEGL):
        pts.append(PTS[i])
        if acc + L >= u * PLEN:
            break
        acc += L
    pts.append((px, py))
    sp = [S(*p) for p in pts]
    d.line(sp, fill=BLUE + (255,), width=int(9 * z), joint="curve")
    # ask markers: houses beside the path, popping as the walker passes
    for k, ta in enumerate(ASK_TIMES):
        hx, hy, sgi = path_at(walk_u(ta))
        (ax, ay), (bx, by) = PTS[sgi], PTS[sgi + 1]
        side = 1 if k % 2 == 0 else -1
        if ax == bx:
            mx, my = hx + side * 120, hy
        else:
            mx, my = hx, hy + side * 120
        if t >= ta:
            p = ease_out(prog(t, ta, 0.3))
            answered = t >= ta + 0.9
            col = (70, 76, 96) if answered else WHITE
            b = dot(42, col)
            b = scaled(b, 0.6 + 0.4 * p)
            sx, sy = S(mx, my)
            paste(c, b, sx - b.width / 2, sy - b.height / 2, p)
            q = T("?" if not answered else "×", 54, BLACK if not answered else (150, 155, 175), HEAD, 0)[0]
            paste(c, q, sx - q.width / 2, sy - q.height / 2 - 4, p)
    # walker
    wx, wy = S(px, py)
    g = glow(46, BLUE, 0.7)
    paste(c, g, wx - g.width / 2, wy - g.height / 2)
    ring_p = (t * 1.4) % 1
    rg = scaled(dot(26, BLUE, ring=2), 1 + ring_p * 1.6)
    paste(c, rg, wx - rg.width / 2, wy - rg.height / 2, 1 - ring_p)
    dd = dot(16, WHITE)
    paste(c, dd, wx - dd.width / 2, wy - dd.height / 2)
    dd = dot(11, BLUE)
    paste(c, dd, wx - dd.width / 2, wy - dd.height / 2)

    c.alpha_composite(grad_top(0.42, 0.95))
    c.alpha_composite(grad_bottom(0.78, 0.7))
    dr = ImageDraw.Draw(c)
    pk = ease_out(prog(t, MAP_T0 + 0.05, 0.4))
    dr.rectangle((M, 286, M + 26, 312), fill=BLUE + (int(255 * pk),))
    put_text(c, "RENTING IN NIGERIA", M + 46, 280, 34, t, MAP_T0 + 0.05, WHITE, BODY, 0.12)
    put_text(c, "Street to street.", M, 350, 104, t, 9.12, WHITE, HEAD, -0.04)
    put_text(c, "“Is there any vacant", M, 500, 66, t, 12.55, (200, 205, 225), HEAD2, -0.02)
    put_text(c, "house around here?”", M, 582, 66, t, 12.85, (200, 205, 225), HEAD2, -0.02)
    return c


def s_photo(t, img, name, t0, t1, cx=0.5, cy=0.42, z0=1.0, z1=1.08, bw=0.35):
    ph = founder_photo(name)
    z = z0 + (z1 - z0) * ease_in_out(prog(t, t0, t1 - t0))
    w, h = W / z, H / z
    x0 = clamp(ph.width * cx - w / 2, 0, ph.width - w)
    y0 = clamp(ph.height * cy - h / 2, 0, ph.height - h)
    c = ph.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h))
    if bw:
        g = c.convert("L").convert("RGB")
        c = Image.blend(c, g, bw)
    c = c.convert("RGBA")
    c.alpha_composite(vignette(0.7))
    c.alpha_composite(grad_bottom(0.6, 0.8))
    draw_captions(c, t)
    return c


def s_question(t, img):
    """21.6–25.3  'Why is housing still disconnected?'"""
    t0 = 21.62
    c = bg_card(BLACK, (34, 34, 34), 1.0, t, t0)
    top_bar(c, t, t0)
    put_text(c, "Why is", M, 610, 150, t, 21.74, WHITE)
    put_text(c, "housing", M, 775, 150, t, 22.25, WHITE)
    put_text(c, "still", M, 940, 150, t, 22.85, WHITE)
    # 'disconnected?' splits in two as it lands
    left, padl = T("discon", 134, BLUE, HEAD, -0.045)
    right, padr = T("nected?", 134, BLUE, HEAD, -0.045)
    ts = 23.35
    if t >= ts:
        p = ease_out(prog(t, ts, 0.45))
        sep = 34 * ease_out(prog(t, 23.95, 0.9))
        y = 1105 + (1 - p) * 60
        lw = left.width - 2 * padl
        paste(c, left, M - padl - sep * 0.15, y, p)
        paste(c, right, M - padr + lw + 4 + sep, y - sep * 0.12, p)
        if sep > 2:
            d = ImageDraw.Draw(c)
            x = M + lw + sep * 0.45
            d.line((x, y + 40, x, y + 185), fill=(255, 255, 255, int(120 * prog(t, 24.0, 0.4))), width=2)
    bottom_rule(c, t, t0)
    return c


PROBLEMS = [
    (25.38, ["Renting is", "difficult."]),
    (27.02, ["Tenancy is", "fragmented."]),
    (28.97, ["Properties run on", "WhatsApp & notebooks."]),
]


def s_problems(t, img):
    """25.3–32.95  Founder + stacked problem statements."""
    z = MED if t < 27.0 else (1.26 if t < 28.95 else MED)
    t_shot = 25.3 if t < 27.0 else (27.0 if t < 28.95 else 28.95)
    c = founder(img, t, t_shot, z, z * 1.02, 2.0)
    c.alpha_composite(grad_bottom(0.55, 0.92))
    y = 1385
    active = max(i for i, (s, _) in enumerate(PROBLEMS) if t >= s - 0.05) if t >= PROBLEMS[0][0] - 0.05 else -1
    for i, (s, lines) in enumerate(PROBLEMS):
        if t < s - 0.05:
            continue
        a = 1.0 if i == active else 0.0
        if i != active:
            continue
        d = ImageDraw.Draw(c)
        pk = ease_out(prog(t, s - 0.05, 0.3))
        d.rectangle((M, y - 50, M + 26, y - 24), fill=BLUE + (int(255 * pk),))
        put_text(c, f"0{i + 1} / 03", M + 44, y - 58, 32, t, s - 0.05, (190, 195, 215), BODY, 0.06)
        size = 76 if i < 2 else 66
        for li, line in enumerate(lines):
            put_text(c, line, M, y + li * int(size * 1.12), size, t, s - 0.05 + li * 0.12, WHITE, HEAD, -0.04,
                     hl=(line if li == 1 else None), hl_color=WHITE, hl_bg=BLUE if li == 1 else None)
    return c


CHIPS = [
    (34.55, "Tenants", 90, 470, (-1, -0.4)),
    (35.66, "Managers", 690, 330, (0.3, -0.6)),
    (36.45, "Records", 90, 1010, (-1, 0.3)),
    (37.15, "Payments", 540, 1100, (0.4, 0.5)),
]


def s_juggle(t, img):
    """33.0–39.95  Owners juggling everything — chips float around the founder."""
    c = founder(img, t, 33.0, MED, MED * 1.04, 7.0)
    c.alpha_composite(grad_bottom(0.62, 0.7))
    spread = ease_in_out(prog(t, 38.3, 1.6))
    for k, (s, label, x, y, (dx, dy)) in enumerate(CHIPS):
        if t < s:
            continue
        p = ease_out(prog(t, s, 0.35))
        bob = math.sin(t * 2.2 + k * 1.7) * 10
        im = pill(label)
        im = scaled(im, 0.8 + 0.2 * p)
        xx = x + dx * spread * 60
        yy = y + bob + dy * spread * 60 + (1 - p) * 24
        paste(c, im, xx, yy, p * (1 - 0.45 * spread))
    draw_captions(c, t)
    return c


def s_reveal(t, img):
    """43.8–44.85  'At Urbn' — brand slam."""
    t0 = 43.80
    c = solid(BLUE)
    wm = watermark(WHITE, 0.08, 2300)
    paste(c, wm, 380 - (t - t0) * 30, 160)
    p = ease_out(prog(t, 43.86, 0.5))
    s = 1.06 - 0.06 * p
    lg = fit_w(tint(LOGO_W, WHITE), 620 * s)
    paste(c, lg, (W - lg.width) / 2, (H - lg.height) / 2 - 40, min(1, p * 2.2))
    d = ImageDraw.Draw(c)
    q = ease_out(prog(t, 43.95, 0.7))
    d.line((M, 160, M + (W - 2 * M) * q, 160), fill=(255, 255, 255, 140), width=2)
    d.line((W - M - (W - 2 * M) * q, H - 160, W - M, H - 160), fill=(255, 255, 255, 140), width=2)
    return c


def s_presence(t, img):
    """47.95–51.45  'We're giving physical properties a digital presence.'"""
    t0 = 47.95
    c = bg_card(WHITE, (232, 232, 232), 1.0, t, t0)
    top_bar(c, t, t0, dark=False)
    put_text(c, "We're giving", M, 420, 92, t, 48.0, (90, 90, 90), HEAD2, -0.03)
    put_text(c, "physical properties", M, 530, 110, t, 48.55, BLACK, HEAD, -0.045)
    put_text(c, "a digital presence.", M, 665, 110, t, 49.55, BLACK, HEAD, -0.045,
             hl="digital presence.", hl_color=BLUE)
    card, pad = property_card(W - 2 * M)
    tc = 49.85
    if t >= tc:
        p = ease_out(prog(t, tc, 0.6))
        y = 960 + (1 - p) * 220
        paste(c, card, M - pad, y - pad, min(1, p * 1.5))
        # pulse around the DPI code block
        tp = 50.45
        if t >= tp:
            q = prog(t, tp, 0.9)
            ch = card.height - 2 * pad
            cw = card.width - 2 * pad
            k = cw / 1210
            bx0, by0 = M + 54 * k, y + (692 - 390) * k
            bx1, by1 = M + 1156 * k, y + (982 - 390) * k
            g = 10 + 18 * q
            d = ImageDraw.Draw(c)
            d.rounded_rectangle((bx0 - g, by0 - g, bx1 + g, by1 + g), 44, outline=BLUE + (int(255 * (1 - q)),), width=4)
            put_text(c, "DIGITAL PROPERTY IDENTITY", M, y + ch + 50, 34, t, tp, BLUE, BODY, 0.1)
    return c


NODES = [
    (51.49, "Owners", (220, 680)),
    (53.32, "Renters", (780, 650)),
    (54.27, "Agents", (190, 1230)),
    (55.16, "Records", (720, 1270)),
    (55.97, "Services", (450, 1400)),
]
CENTER = (480, 980)
_rnd = random.Random(11)
SAT = []
for _i in range(30):
    ang = _rnd.uniform(0, math.tau)
    rr = _rnd.uniform(470, 640)
    SAT.append((56.85 + _i * 0.045, (CENTER[0] + math.cos(ang) * rr * 0.92, CENTER[1] + math.sin(ang) * rr * 1.05),
                _rnd.uniform(3, 7)))


def s_network(t, img):
    """51.45–59.2  Connecting properties to owners, renters, agents, records, services…"""
    t0 = 51.45
    SS = 2
    base = bg_card(BLACK, (28, 28, 28), 1.0, t, t0, wm_x=520, wm_y=520)
    lay = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rot = (t - t0) * 0.012
    cx0, cy0 = CENTER

    def R(p):
        x, y = p[0] - cx0, p[1] - cy0
        return ((cx0 + x * math.cos(rot) - y * math.sin(rot)) * SS,
                (cy0 + x * math.sin(rot) + y * math.cos(rot)) * SS)

    nodes_pos = [R(p) for _, _, p in NODES]
    # satellites
    for ts, p, r in SAT:
        if t < ts:
            continue
        q = ease_out(prog(t, ts, 0.4))
        sp = R(p)
        near = min(range(len(NODES)), key=lambda i: math.dist(sp, nodes_pos[i]))
        if t >= NODES[near][0]:
            npos = nodes_pos[near]
            ex = npos[0] + (sp[0] - npos[0]) * q
            ey = npos[1] + (sp[1] - npos[1]) * q
            d.line((npos[0], npos[1], ex, ey), fill=(255, 255, 255, int(55 * q)), width=2 * SS)
        rr = r * SS * q
        d.ellipse((sp[0] - rr, sp[1] - rr, sp[0] + rr, sp[1] + rr), fill=(200, 205, 230, int(200 * q)))
    # main spokes
    cc = R(CENTER)
    for k, (ts, label, p) in enumerate(NODES):
        if t < ts:
            continue
        q = ease_out(prog(t, ts, 0.45))
        np_ = nodes_pos[k]
        ex, ey = cc[0] + (np_[0] - cc[0]) * q, cc[1] + (np_[1] - cc[1]) * q
        d.line((cc[0], cc[1], ex, ey), fill=BLUE + (255,), width=4 * SS)
        if q > 0.95:
            ph = ((t - ts) * 0.8 + k * 0.23) % 1
            px, py = cc[0] + (np_[0] - cc[0]) * ph, cc[1] + (np_[1] - cc[1]) * ph
            d.ellipse((px - 7 * SS, py - 7 * SS, px + 7 * SS, py + 7 * SS), fill=(160, 175, 255, 255))
    for k, (ts, label, p) in enumerate(NODES):
        if t < ts:
            continue
        q = ease_out(prog(t, ts + 0.25, 0.35))
        x, y = nodes_pos[k]
        r = 20 * SS * q
        d.ellipse((x - r, y - r, x + r, y + r), fill=WHITE + (255,))
        r2 = 9 * SS * q
        d.ellipse((x - r2, y - r2, x + r2, y + r2), fill=BLUE + (255,))
    lay = lay.resize((W, H), Image.LANCZOS)
    base.alpha_composite(lay)
    # center node
    p = ease_out(prog(t, t0 + 0.02, 0.45))
    box = 210
    cn = Image.new("RGBA", (box, box), (0, 0, 0, 0))
    cn_fill = Image.new("RGBA", (box, box), BLUE + (255,))
    cn_fill.putalpha(rounded_mask((box, box), 48))
    cn.alpha_composite(cn_fill)
    ic = fit_h(tint(ICON, WHITE), 112)
    cn.alpha_composite(ic, ((box - ic.width) // 2, (box - ic.height) // 2))
    g = glow(170, BLUE, 0.5)
    pulse = 0.85 + 0.15 * math.sin(t * 3.2)
    paste(base, g, CENTER[0] - g.width / 2, CENTER[1] - g.height / 2, p * pulse)
    cn = scaled(cn, 0.6 + 0.4 * p)
    paste(base, cn, CENTER[0] - cn.width / 2, CENTER[1] - cn.height / 2, p)
    # labels
    for k, (ts, label, pp) in enumerate(NODES):
        x, y = nodes_pos[k][0] / SS, nodes_pos[k][1] / SS
        below = y > CENTER[1] + 100
        put_text(base, label, x, y + (36 if below else -112), 60, t, ts + 0.1,
                 WHITE, HEAD, -0.03, align="center")
    put_text(base, "Connecting every property", M, 290, 66, t, 51.49, WHITE, HEAD, -0.03)
    put_text(base, "to everything around it.", M, 374, 66, t, 56.85, (140, 150, 190), HEAD, -0.03)
    return base


def s_phone_card(t, img, t0, bg, fg, l1, l2, hl, key, sub, accent=BLUE):
    if bg == BLUE:
        c = bg_card(BLUE, WHITE, 0.10, t, t0)
    else:
        c = bg_card(bg, (232, 232, 232), 1.0, t, t0)
    put_text(c, l1, M, 250, 112, t, t0 + 0.05, fg, HEAD, -0.045)
    put_text(c, l2, M, 382, 112, t, t0 + 0.3, fg, HEAD, -0.045, hl=hl,
             hl_color=(WHITE if bg == BLUE else BLUE), hl_bg=(BLACK if bg == BLUE else None))
    ph, pad = phone(key, 660)
    p = ease_out(prog(t, t0, 0.8))
    y = 600 + (1 - p) * 260 - (t - t0) * 18
    paste(c, ph, (W - ph.width) / 2, y - pad, min(1, p * 1.4))
    if sub:
        put_text(c, sub, M, 535, 36, t, t0 + 0.5, (fg if bg == BLUE else (110, 110, 110)), BODY, 0.08)
    return c


def s_identity(t, img):
    """68.2–73.42  History. Identity. Connected to the digital world."""
    t0 = 68.22
    c = bg_card(BLACK, (30, 30, 30), 1.0, t, t0)
    put_text(c, "It has history.", M, 275, 120, t, 68.27, WHITE, HEAD, -0.045)
    put_text(c, "An identity.", M, 420, 120, t, 69.63, WHITE, HEAD, -0.045, hl="identity.", hl_color=WHITE, hl_bg=BLUE)
    put_text(c, "And it connects to the digital world.", M, 590, 50, t, 71.27, (165, 170, 195), BODY, -0.01)
    specs = [("home_lagos", 340, 185, 860, -7, 71.30), ("listings", 340, 880, 860, 7, 71.42),
             ("home_ph", 400, 530, 810, 0, 71.55)]
    for key, w, cx, top, ang, ts in specs:
        if t < ts:
            continue
        ph, pad = phone(key, w)
        p = ease_out(prog(t, ts, 0.8))
        im = ph.rotate(ang * p, resample=Image.BICUBIC, expand=True) if ang else ph
        drift = (t - ts) * 10
        paste(c, im, cx - im.width / 2, top - pad + (1 - p) * 420 - drift, min(1, p * 1.5))
    c.alpha_composite(grad_bottom(0.86, 0.9, (0, 0, 0)))
    return c


def s_final(t, img):
    """75.7–79.0  'The digital infrastructure for housing.'"""
    t0 = 75.72
    c = bg_card(BLACK, (34, 34, 34), 1.0, t, t0)
    top_bar(c, t, t0)
    put_text(c, "The digital", M, 690, 150, t, 75.84, WHITE)
    put_text(c, "infrastructure", M, 855, 150, t, 76.35, WHITE)
    put_text(c, "for housing.", M, 1020, 150, t, 77.78, WHITE, hl="housing.", hl_color=WHITE, hl_bg=BLUE)
    bottom_rule(c, t, t0)
    return c


def s_end(t, img):
    """79.0–84.2  End card."""
    t0 = 79.0
    c = bg_card(BLACK, (26, 26, 26), 1.0, t, t0, wm_x=520, wm_y=380)
    p = ease_out(prog(t, t0 + 0.1, 1.1))
    lg = fit_w(tint(LOGO_W, WHITE), 560 * (0.96 + 0.04 * p))
    paste(c, lg, (W - lg.width) / 2, 760 - lg.height / 2 + (1 - p) * 20, p)
    put_text(c, "This is only the beginning.", W / 2, 1010, 54, t, 80.2, (200, 200, 205), BODY, -0.01,
             align="center", rise=False, dur=0.9)
    d = ImageDraw.Draw(c)
    q = ease_out(prog(t, 80.6, 0.9))
    d.rectangle((W / 2 - 17, 1150, W / 2 + 17, 1184), fill=BLUE + (int(255 * q),))
    put_text(c, "Digital infrastructure for housing", W / 2, 1230, 32, t, 81.0, (130, 130, 140), BODY, 0.08,
             align="center", rise=False, dur=0.9)
    fade = prog(t, 83.1, 1.1)
    if fade > 0:
        c.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fade))))
    return c


# --------------------------------------------------------------------------- timeline
TIMELINE = [
    (0.00, 6.62, s_hook),
    (6.62, 9.10, lambda t, im: s_founder_cut(t, im, 6.62, CLOSE, CLOSE * 1.03, 2.4)),
    (9.10, 16.25, s_map),
    (16.25, 18.62, lambda t, im: s_photo(t, im, "DSC00718.jpg", 16.25, 18.62, 0.5, 0.38, 1.0, 1.07)),
    (18.62, 21.62, lambda t, im: s_founder_cut(t, im, 18.62, MED, MED * 1.03, 3.0)),
    (21.62, 25.30, s_question),
    (25.30, 32.95, s_problems),
    (32.95, 39.98, s_juggle),
    (39.98, 43.80, lambda t, im: s_founder_cut(t, im, 39.98, CLOSE, CLOSE * 1.03, 3.8)),
    (43.80, 44.86, s_reveal),
    (44.86, 47.95, lambda t, im: s_founder_cut(t, im, 44.86, MED, MED * 1.03, 3.1)),
    (47.95, 51.45, s_presence),
    (51.45, 59.20, s_network),
    (59.20, 62.12, lambda t, im: s_phone_card(t, im, 59.20, BLUE, WHITE, "Finding a home", "becomes easier.",
                                              "easier.", "listings", None)),
    (62.12, 64.32, lambda t, im: s_phone_card(t, im, 62.12, WHITE, BLACK, "Managing one", "becomes simpler.",
                                              "simpler.", "dashboard", None)),
    (64.32, 68.22, lambda t, im: s_founder_cut(t, im, 64.32, CLOSE, CLOSE * 1.03, 3.9)),
    (68.22, 73.42, s_identity),
    (73.42, 75.72, lambda t, im: s_founder_cut(t, im, 73.42, MED, MED * 1.04, 2.3)),
    (75.72, 79.00, s_final),
    (79.00, TOTAL, s_end),
]


def frame_at(t, foot):
    img = foot.get(min(t, SRC_DUR - 0.1))
    for s, e, fn in TIMELINE:
        if s <= t < e:
            c = fn(t, img)
            break
    else:
        c = solid(BLACK)
    # Settle: graphics cards ease in from a slight scale on each cut.
    return c.convert("RGB")


def main():
    args = sys.argv[1:]
    if args and args[0] == "--still":
        foot = Footage()
        for i in range(1, len(args), 2):
            t, out = float(args[i]), args[i + 1]
            frame_at(t, foot).save(out)
        return
    out = args[0] if args else os.path.join(ROOT, "edit", "video_only.mp4")
    t_from, t_to = 0.0, TOTAL - OFFSET   # output time; source time = output + OFFSET
    if "--from" in args:
        t_from = float(args[args.index("--from") + 1])
    if "--to" in args:
        t_to = float(args[args.index("--to") + 1])
    foot = Footage()
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", out],
        stdin=subprocess.PIPE)
    n0, n1 = int(round(t_from * FPS)), int(round(t_to * FPS))
    for n in range(n0, n1):
        t = n / FPS + OFFSET
        enc.stdin.write(frame_at(t, foot).tobytes())
        if n % 150 == 0:
            print(f"  {t:6.2f}s", flush=True)
    enc.stdin.close()
    enc.wait()


if __name__ == "__main__":
    main()
