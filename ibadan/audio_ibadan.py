"""'Ibadan is Urbn' — sound design and score.

The shout is a formant-synthesised voice; distance is simulated with
low-pass filtering, hill echoes and reverb that clear up as the message
gets through. Music: an afro groove (shaker, log drum, talking drum) at
104 BPM, built around a talking-drum phrase that 'speaks' the rhythm of
"Ì-bà-dàn is Ur-bn".

    python3 ibadan/audio_ibadan.py OUT.wav
"""
import os
import sys

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "edit"))
import audio as A  # noqa: E402  (filters, reverb and percussion helpers)

SR = A.SR
TOTAL = 28.5  # story time (tau), as in animate.py

# Output time <-> story time (keep in sync with animate.WARP). Music and
# effects are written in story time and converted; voices are placed in
# output time directly.
WARP = [(0.0, 0.0), (11.6, 11.6), (15.3, 14.2), (22.1, 21.0), (25.3, 22.6), (31.2, 28.5)]
TOTAL_OUT = WARP[-1][0]
N = int(TOTAL_OUT * SR)
rng = np.random.default_rng(11)
lp, hp, bp, reverb = A.lp, A.hp, A.bp, A.reverb
add_out = A.add


def T(tau):
    """story time -> output time"""
    return float(np.interp(tau, [b for _, b in WARP], [a for a, _ in WARP]))


def Tinv(t):
    return float(np.interp(t, [a for a, _ in WARP], [b for _, b in WARP]))


def add(buf, sig, tau, gain=1.0, pan=0.0):
    A.add(buf, sig, T(tau), gain, pan)
BPM = 104
B = 60 / BPM
S16 = B / 4

# ------------------------------------------------------------------ voice synthesis
FORM = {  # F1, F2, F3 (Hz), relative level
    "i": (310, 2250, 2950, 1.0), "a": (780, 1250, 2550, 1.0), "er": (520, 1350, 1700, 1.0),
    "e": (500, 1850, 2550, 1.0), "n": (260, 1600, 2600, 0.32), "h": (700, 1300, 2600, 0.0),
}
PHRASE = [("i", .15, 1.00), ("b", .05, 1.0), ("a", .21, 1.18), ("d", .04, 1.1), ("a", .17, 1.06), ("n", .10, 1.0),
          ("_", .06, 1.0), ("i", .09, .98), ("z", .08, .98), ("_", .05, 1.0), ("er", .32, 1.26), ("b", .05, 1.1),
          ("n", .40, .86)]


def voice(segs, f0=210, breath=0.08, rough=0.0):
    """Very small formant synthesiser: glottal saw source -> per-segment formant bank."""
    n = int(sum(d for _, d, _ in segs) * SR) + int(0.1 * SR)
    f = np.zeros(n)
    amp = np.zeros(n)
    i = 0
    bounds = []
    for k, d, pm in segs:
        m = int(d * SR)
        f[i:i + m] = f0 * pm
        amp[i:i + m] = 0 if k in ("_", "b", "d") else (0.15 if k == "z" else FORM.get(k, (0, 0, 0, 1))[3])
        bounds.append((k, i, i + m))
        i += m
    f[i:] = f[i - 1] * 0.9
    sm = int(0.03 * SR)
    f = np.convolve(np.pad(f, sm, mode="edge"), np.ones(2 * sm + 1) / (2 * sm + 1), "valid")
    amp = np.convolve(np.pad(amp, sm, mode="edge"), np.ones(2 * sm + 1) / (2 * sm + 1), "valid")
    tt = np.arange(n) / SR
    f *= 1 + 0.012 * np.sin(2 * np.pi * 5.5 * tt) + 0.006 * rng.standard_normal(n).cumsum() / np.sqrt(n)
    ph = np.cumsum(f) / SR
    src = 2 * (ph % 1) - 1 + rough * rng.standard_normal(n) * 0.3
    src = A.lp(src, 4500)
    out = np.zeros(n)
    for k, s0, s1 in bounds:
        if k in ("_", "b", "d"):
            if k in ("b", "d"):   # plosive burst
                L = int(0.012 * SR)
                out[s1:s1 + L] += bp(rng.standard_normal(L), 300 if k == "b" else 2500, 5000) * 0.25
            continue
        if k == "z":
            seg = bp(rng.standard_normal(s1 - s0), 3500, 8000) * 0.35
            out[s0:s1] += seg
            continue
        F1, F2, F3, lvl = FORM[k]
        w = np.zeros(n)
        pad = int(0.035 * SR)
        a, b = max(0, s0 - pad), min(n, s1 + pad)
        w[a:b] = np.hanning(b - a) ** 0.6
        filt = bp(src, F1 * .8, F1 * 1.25) * 1.0 + bp(src, F2 * .88, F2 * 1.12) * .55 + bp(src, F3 * .9, F3 * 1.1) * .3
        out += filt * w * lvl
    out *= amp
    out += bp(rng.standard_normal(n), 900, 4000) * breath * amp
    return out / (np.abs(out).max() + 1e-9)


def distance(x, q):
    """q=0: far, muffled, echoing off the hills. q=1: close and clear."""
    y = lp(x, 350 + 7000 * q ** 1.6, 4) if q < 0.98 else x.copy()
    out = np.zeros(len(y) + int(1.6 * SR))
    out[:len(y)] += y
    for dly, g in [(0.38, 0.55), (0.77, 0.32), (1.21, 0.18)]:
        k = int(dly * SR)
        out[k:k + len(y)] += lp(y, 2500) * g * (1.1 - q)
    st = reverb(out, wet=0.55 - 0.35 * q, seconds=2.2, damp=4000)
    return st * (0.3 + 0.7 * q)


def shout(q, f0=215, pitch2=None):
    v = voice(PHRASE, f0, breath=0.12, rough=0.25)
    if pitch2:
        v2 = voice(PHRASE, f0 * pitch2, breath=0.12, rough=0.25)
        L = int(0.03 * SR)
        v = v + np.r_[np.zeros(L), v2[:-L]] * 0.8
        v /= np.abs(v).max()
    return distance(v, q)


def runner_vocal(kind):
    if kind == "eh":      # "Eh?!" rising
        segs = [("e", .32, 1.0)]
        v = voice(segs, 150, 0.15)
        tt = np.arange(len(v)) / SR
        return v * 0.9
    if kind == "huh":
        return voice([("h", .05, 1), ("a", .26, 1.15)], 140, 0.25) * 0.8
    if kind == "ehn":
        return voice([("e", .18, 1.0), ("n", .22, 1.25)], 155, 0.12)
    return voice([("a", .75, 1.15), ("h", .1, .9)], 135, 0.2)  # "Ahhh"


# ------------------------------------------------------------------ recorded sound effects
SFX_DIR = os.path.join(HERE, "sfx")


def load_sfx(name, t0=None, t1=None):
    """Decode a recorded effect to mono 48 kHz float (returns None if missing)."""
    import subprocess
    path = os.path.join(SFX_DIR, name)
    if not os.path.exists(path):
        return None
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).astype(float)
    if t0 is not None:
        x = x[int(t0 * SR):int(t1 * SR) if t1 else None]
    return x


# ------------------------------------------------------------------ percussion / instruments
def dundun(f0, bend=0.0, dur=0.32):
    """Talking drum: membrane with a pitch slide (squeezed tension cords)."""
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f = f0 * 2 ** (bend * (1 - np.exp(-tt * 14)) / 12)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) + 0.35 * np.sin(1.59 * ph) * np.exp(-tt * 18) + 0.15 * np.sin(2.14 * ph) * np.exp(-tt * 25)
    s *= np.exp(-tt * 7)
    s[: int(0.004 * SR)] += bp(rng.standard_normal(int(0.004 * SR)), 1500, 6000) * 0.8
    return np.tanh(s * 1.4)


def logdrum(f0, dur=0.55):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f = f0 * (1 + 1.0 * np.exp(-tt * 45))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 4.5)
    return np.tanh(s * 2.2) * 0.8


def shaker(acc=1.0):
    n = int(0.07 * SR)
    tt = np.arange(n) / SR
    env = np.minimum(1, tt / 0.012) * np.exp(-tt * 55)
    return hp(rng.standard_normal(n), 5500, 4) * env * acc


def clap():
    n = int(0.25 * SR)
    tt = np.arange(n) / SR
    env = np.zeros(n)
    for k in (0, 0.011, 0.023):
        i = int(k * SR)
        env[i:] += np.exp(-(tt[: n - i]) * 60)
    env += np.exp(-tt * 14) * 0.5
    return bp(rng.standard_normal(n), 900, 5000) * env * 0.6


def kal(m, dur=0.6):
    """Kalimba-ish pluck."""
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f = A.midi(m)
    s = np.sin(2 * np.pi * f * tt) * np.exp(-tt * 6) + 0.25 * np.sin(2 * np.pi * f * 5.4 * tt) * np.exp(-tt * 30)
    s[: int(0.002 * SR)] *= np.linspace(0, 1, int(0.002 * SR))
    return s


L_, M_, H_ = 150, 185, 228
DRUM_PHRASE = [(0, L_, 0.0), (1, L_, -1.0), (2, L_, -1.5), (4, M_, 0.0), (5, H_, 1.0), (7, M_, -3.0)]  # 16ths


def talking_phrase(buf, t0, gain=0.3, pan=0.15):
    for k16, f0, bend in DRUM_PHRASE:
        add(buf, dundun(f0, bend, 0.34 if k16 < 7 else 0.6), t0 + k16 * S16, gain, pan=pan)


def grid(t0, t1, step, origin=0.0):
    """Regular grid in OUTPUT time between story times t0..t1 (tempo stays steady
    through stretched beats); yields story times so add() lands on the grid."""
    o0, o1 = T(t0), T(t1)
    k = int(np.ceil((o0 - origin) / step - 1e-6))
    t = origin + k * step
    while t < o1 - 1e-6:
        yield k, Tinv(t)
        k += 1
        t += step


def music():
    m = np.zeros((N, 2))
    O = 0.0  # bar grid origin

    def shakers(t0, t1, g):
        for k, t in grid(t0, t1, S16, O):
            sw = 0.012 if k % 2 else 0.0
            add(m, shaker(1.0 if k % 4 == 2 else 0.6), t + sw, g, pan=0.25 if k % 2 else -0.25)

    def logs(t0, t1, g, roots=(38, 38, 41, 36)):
        pat = [0, 3, 6, 10, 12]  # syncopated 16th positions in a bar
        for k, t in grid(t0, t1, B * 4, O):
            r = roots[k % len(roots)]
            for p in pat:
                if t + p * S16 < t1:
                    add(m, logdrum(A.midi(r - 12 + (12 if p == 10 else 0))), t + p * S16, g)

    def kicks(t0, t1, g):
        for k, t in grid(t0, t1, B, O):
            add(m, A.kick(110, 46, 0.4, 0.02), t, g)

    def claps(t0, t1, g):
        for k, t in grid(t0, t1, B, O):
            if k % 2 == 1:
                add(m, clap(), t, g)

    def kals(t0, t1, g, notes):
        for k, t in grid(t0, t1, S16 * 2, O):
            if (k * 5) % 7 in (0, 2, 3, 5):
                add(m, kal(notes[k % len(notes)]), t, g, pan=0.4 if k % 2 else -0.4)

    CUR = [62, 65, 67, 69, 72, 74, 69, 67]           # D minor pentatonic: curious
    LIFT = [65, 69, 72, 74, 77, 76, 72, 69]          # F major colour for the payoff

    # 0–3.2 wide: drone + a muffled talking-drum answer
    add(m, A.pad([38, 45, 50], 3.6, a=0.6, r=1.0, bright=0.5), 0.0, 0.6)
    shakers(0.4, 3.2, 0.025)
    talking_phrase(m, 2.35, 0.18)
    # 3.2–11.6 curious groove
    shakers(3.2, 11.6, 0.045)
    logs(3.2, 11.6, 0.14)
    kals(3.2, 11.6, 0.05, CUR)
    talking_phrase(m, 5.8, 0.2, -0.2)
    talking_phrase(m, 10.9, 0.2, 0.2)
    # 11.6–17.0 energy up after the first clear shout
    shakers(11.6, 17.0, 0.05)
    logs(11.6, 17.0, 0.17)
    kicks(13.3, 17.0, 0.22)
    claps(13.3, 17.0, 0.1)
    kals(11.6, 17.0, 0.06, CUR)
    talking_phrase(m, 16.2, 0.24)
    # 17.0–18.8 climb: roll + riser, then silence for the phone reveal
    for k, t in grid(17.0, 18.75, S16, O):
        add(m, dundun(M_ + 40 * (t - 17.0), 0.5, 0.15), t, 0.08 + 0.16 * (t - 17.0) / 1.75, pan=0.1)
    add(m, A.riser(1.75), 17.0, 0.18)
    # 18.8–21.0 near-silence (UI chime in sfx), tiny lift into the payoff
    add(m, A.pad([53, 60, 65, 69], 2.2, a=0.6, r=0.3, bright=0.9), 18.9, 0.35)
    # 21.0–end: payoff groove in F, full kit
    shakers(21.0, 27.6, 0.055)
    logs(21.0, 27.6, 0.2, roots=(41, 41, 38, 36))
    kicks(21.0, 27.6, 0.26)
    claps(21.0, 27.6, 0.12)
    kals(21.0, 27.6, 0.07, LIFT)
    add(m, A.pad([53, 60, 65, 69, 72], T(27.6) - T(21.0), a=0.05, r=1.2, bright=1.0), 21.0, 0.5)
    talking_phrase(m, 24.0, 0.26, -0.1)
    talking_phrase(m, 27.25, 0.34)             # the drum says it one last time
    return reverb(m, wet=0.18, seconds=1.6, damp=7000)


# ------------------------------------------------------------------ recorded voices
VOICE_DIR = os.path.join(HERE, "voice")
# (file, start, end) in the raw recordings — mapped from the slates
TAKES = {
    "S0": ("shouter.m4a", 0.95, 2.12),     # warm-up take, used for the far-away echo from the city
    "S1": ("shouter.m4a", 5.30, 7.30),
    "S2": ("shouter.m4a", 9.02, 10.90),
    "S3": ("shouter.m4a", 14.45, 17.88),   # "I… BA… DAN… IS… URBN!"
    "S4": ("shouter.m4a", 19.05, 21.45),
    "R1": ("runner.m4a", 4.95, 6.25),      # "Oga, wetin you dey talk?!"
    "R2": ("runner.m4a", 11.45, 12.42),    # "Ibadan na… TURBO??" (first of two takes)
    "R3": ("runner.m4a", 15.85, 17.92),    # "Ibadan na URBAN?! Since when?!"
    "R4": ("runner.m4a", 30.15, 32.85),    # "Wait o… wait…" (panting)
    "R5": ("runner.m4a", 35.75, 38.90),    # "Ah!… Ibadan is Urbn!"
    "R6": ("runner.m4a", 40.25, 41.85),    # "IBADAN IS URBN!"
}


def take(name):
    """Cut a take and clean it: rumble cut, denoise, gentle compression, level match."""
    import subprocess
    f, t0, t1 = TAKES[name]
    nr = 16 if f.startswith("runner") else 9
    chain = ",".join([f"atrim={t0}:{t1}", "asetpts=PTS-STARTPTS", "highpass=f=90",
                      f"afftdn=nr={nr}:nf=-38:tn=1", "equalizer=f=250:t=q:w=1:g=-2",
                      "equalizer=f=3500:t=q:w=1:g=2", "acompressor=threshold=-20dB:ratio=3:attack=5:release=90",
                      "aresample=48000"])
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(VOICE_DIR, f), "-af", chain, "-ac", "1",
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).astype(float)
    x /= np.sqrt(np.mean(x ** 2)) + 1e-9
    x *= 10 ** (-20 / 20)   # every take to -20 dBFS RMS
    fade = int(0.012 * SR)
    x[:fade] *= np.linspace(0, 1, fade)
    x[-fade * 3:] *= np.linspace(1, 0, fade * 3)
    return x


def voices():
    v = np.zeros((N, 2))
    # shouter: three attempts, from far and muffled to close and clear
    add_out(v, distance(take("S1"), 0.08), 0.55, 0.75)
    add_out(v, distance(take("S2"), 0.5), 6.45, 1.05)
    add_out(v, distance(take("S3"), 0.96), 11.75, 0.95)
    # runner: close to camera, nearly dry
    for name, tau, g in [("R1", 3.45, 1.0), ("R2", 9.35, 1.0), ("R3", 14.4, 1.0), ("R4", 17.1, 0.9), ("R5", 21.0, 1.0)]:
        x = take(name)
        add_out(v, reverb(x, wet=0.08, seconds=0.9, damp=6000), T(tau), g, pan=-0.08)
    # together on the hill
    add_out(v, distance(take("S4"), 0.95), T(22.7), 0.85, pan=0.12)
    add_out(v, distance(take("R6"), 0.97), T(22.7) + 0.06, 0.75, pan=-0.12)
    # the chain: someone down in the city shouts it on
    add_out(v, distance(take("S0"), 0.02) * 0.6, T(23.3), 0.9, pan=0.45)
    return v


def loop_bed(x, n, xf_s=0.5):
    xf = int(xf_s * SR)
    bed = np.zeros(n + len(x))
    i = 0
    while i < n:
        seg = x.copy()
        seg[:xf] *= np.linspace(0, 1, xf)
        seg[-xf:] *= np.linspace(1, 0, xf)
        bed[i:i + len(seg)] += seg
        i += len(seg) - xf
    return bed[:n]


def ambience():
    """Recorded beds: the city (street noise) below, crickets on the hill, wind up top."""
    s = np.zeros((N, 2))
    tt = np.arange(N) / SR
    shots = [(0.0, 3.2, "wide"), (3.2, 6.2, "runner"), (6.2, 9.0, "tower"), (9.0, 11.6, "runner"),
             (11.6, 14.2, "tower"), (14.2, 17.0, "runner"), (17.0, 18.8, "tower"), (18.8, 21.0, "phone"),
             (21.0, 22.6, "runner"), (22.6, 24.6, "wide"), (24.6, TOTAL, "end")]

    def level(table):
        g = np.zeros(N)
        for a, b, kind in shots:
            g[(tt >= T(a)) & (tt < T(b))] = table[kind]
        sm = int(0.25 * SR)
        return np.convolve(g, np.ones(sm) / sm, "same")

    street = load_sfx("street2.m4a")
    if street is not None:
        x = hp(street, 80, 2)
        x /= np.sqrt(np.mean(x ** 2)) + 1e-9
        bed = loop_bed(x, N)
        near = lp(bed, 6000)
        far = lp(bed, 900)          # heard from up the hill: distant, muffled
        gn = level({"wide": 0.040, "runner": 0.0, "tower": 0.0, "phone": 0.0, "end": 0.0})
        gf = level({"wide": 0.0, "runner": 0.022, "tower": 0.016, "phone": 0.008, "end": 0.012})
        s += np.stack([near * gn + far * gf, np.roll(near, 900) * gn + np.roll(far, 900) * gf], 1)
    crick = load_sfx("street3_crickets.m4a")
    if crick is not None:
        x = hp(crick, 2500, 2)      # keep the crickets, lose the traffic
        x /= np.sqrt(np.mean(x ** 2)) + 1e-9
        bed = loop_bed(x, N, 0.8)
        g = level({"wide": 0.010, "runner": 0.022, "tower": 0.030, "phone": 0.006, "end": 0.0})
        s += np.stack([bed * g, np.roll(bed, 1500) * g], 1)
    wind = lp(rng.standard_normal(N), 600)
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.13 * tt)
    g = level({"wide": 0.02, "runner": 0.025, "tower": 0.05, "phone": 0.0, "end": 0.0})
    s += np.stack([wind * lfo * g, np.roll(wind, 2000) * lfo * g], 1)
    return s


def sfx():
    s = np.zeros((N, 2))
    # real grass recording (ibadan/sfx/grass.m4a) under the climb, louder when the camera is on the runner
    grass = load_sfx("grass.m4a", 0.2, 5.9)
    if grass is not None:
        g = hp(grass, 150, 2)
        g /= np.abs(g).max() + 1e-9
        o0, o1 = T(3.15), T(18.1)
        need = int((o1 - o0) * SR)
        bed = loop_bed(g, need, 0.4)
        tt = o0 + np.arange(need) / SR
        close = np.zeros(need)
        for a, b in [(3.2, 6.2), (9.0, 11.6), (14.2, 17.0)]:
            close[(tt >= T(a)) & (tt < T(b))] = 1
        sm = int(0.12 * SR)
        close = np.convolve(close, np.ones(sm) / sm, "same")
        gain = (0.05 + 0.13 * close) * np.clip((tt - o0) / 0.3, 0, 1) * np.clip((o1 - tt) / 0.6, 0, 1)
        a = int(o0 * SR)
        s[a:a + need] += np.stack([bed * gain * 0.95, np.roll(bed, 480) * gain * 1.05], 1)
    # soft footfalls; the grass recording carries the texture
    for k, t in grid(3.2, 17.9, 1 / 3.2):
        close = 1.0 if any(a <= t < b for a, b in [(3.2, 6.2), (9.0, 11.6), (14.2, 17.0)]) else 0.35
        n = int(0.12 * SR)
        tt = np.arange(n) / SR
        add(s, np.sin(2 * np.pi * 75 * tt) * np.exp(-tt * 40), t + rng.uniform(-0.01, 0.01), 0.09 * close,
            pan=-0.15 if k % 2 else 0.15)
    # UI / transitions
    add(s, A.tick(2200), 3.45, 0.10)
    add(s, A.tick(2200), 9.2, 0.10)
    add(s, A.whoosh(0.3, 1.2), 10.25, 0.18)         # strike-through on "TURBO"
    add_out(s, A.impact(0.7), 11.72, 0.3)           # the first clear shout
    add(s, A.tick(2200), 14.4, 0.10)
    add(s, A.bell(84, 2.0), 17.4, 0.05)             # phone glows
    add(s, A.whoosh(0.4, 0.8), 18.65, 0.2)
    add(s, A.blip(91), 19.15, 0.18)                 # app card
    add(s, A.bell(89, 2.5), 19.3, 0.05)
    add(s, A.impact(0.6), 21.0, 0.3)                # "Ahhh… Ibadan is Urbn!"
    add(s, A.impact(0.6), 24.6, 0.3)                # end card
    for k, t in enumerate(np.arange(23.3, 23.8, 0.11)):
        add(s, A.pop(79 + k * 2, 0.2), t, 0.04, pan=0.5)   # the chain from the city
    return s


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "mix.wav")
    m = music()
    v = voices()
    # duck the music under any voice
    env = np.sqrt(np.convolve((v ** 2).sum(1), np.ones(4800) / 4800, "same"))
    active = (env > 10 ** (-42 / 20)).astype(float)
    sm = int(0.15 * SR)
    duck = 1 - 0.72 * np.convolve(active, np.ones(sm) / sm, "same")
    m *= duck[:, None]
    mix = m * 0.9 + sfx() + ambience() + v
    fo = int(0.8 * SR)
    mix[-fo:] *= np.linspace(1, 0, fo)[:, None]
    sf.write(out, mix.astype(np.float32), SR, subtype="FLOAT")
    sf.write(out.replace(".wav", "_voices.wav"), v.astype(np.float32), SR, subtype="FLOAT")
    print("peak", np.abs(mix).max())


if __name__ == "__main__":
    main()
