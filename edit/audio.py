"""Urbn founder film — voice clean-up, original score and sound design.

    python3 edit/audio.py OUT.wav
"""
import os
import subprocess
import sys

import numpy as np
import soundfile as sf
from scipy.signal import butter, fftconvolve, sosfilt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000
TOTAL = 84.2
N = int(TOTAL * SR)
rng = np.random.default_rng(3)

BPM = 80
OFFSET = 0.85  # keep in sync with render.OFFSET
BEAT = 60 / BPM


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x, axis=0)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x, axis=0)


def bp(x, f0, f1, order=2):
    return sosfilt(butter(order, [f0, f1], "band", fs=SR, output="sos"), x, axis=0)


def env_adsr(n, a, r, sustain_n=None):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    na = min(na, n)
    e[:na] = np.linspace(0, 1, na) ** 1.5
    if nr > 0 and nr < n:
        e[-nr:] *= np.linspace(1, 0, nr) ** 1.5
    return e


def add(buf, sig, t, gain=1.0, pan=0.0):
    """Mix mono or stereo signal into stereo buf at time t."""
    i = int(t * SR)
    if i >= len(buf):
        return
    if sig.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        sig = np.stack([sig * l * 1.414, sig * r * 1.414], 1)
    n = min(len(sig), len(buf) - i)
    buf[i:i + n] += sig[:n] * gain


def reverb_ir(seconds=3.2, damp=5500, seed=0):
    r = np.random.default_rng(seed)
    n = int(seconds * SR)
    tt = np.arange(n) / SR
    ir = r.standard_normal((n, 2)) * np.exp(-tt * 6.9 / seconds)[:, None]
    ir = lp(ir, damp)
    ir[: int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))[:, None]
    return ir / np.sqrt((ir ** 2).sum(0))


def reverb(x, wet=0.35, seconds=3.2, damp=5500):
    ir = reverb_ir(seconds, damp)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    y = np.stack([fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], 1)
    return x * (1 - wet) + y * wet * 2.2


# ---------------------------------------------------------------- instruments
def pad(notes, dur, a=1.6, r=2.2, bright=1.0, detune=0.11):
    n = int((dur + r) * SR)
    tt = np.arange(n) / SR
    out = np.zeros((n, 2))
    for k, m in enumerate(notes):
        f = midi(m)
        for v, (dt, pan) in enumerate([(-detune, -0.7), (0, 0), (detune, 0.7)]):
            ff = f * 2 ** (dt / 12)
            ph = rng.uniform(0, 2 * np.pi)
            s = np.zeros(n)
            nh = int(min(14, 3800 * bright / ff))
            for h in range(1, max(2, nh)):
                s += np.sin(2 * np.pi * ff * h * tt + ph * h) / h ** 1.55
            s *= 1 + 0.15 * np.sin(2 * np.pi * (0.13 + 0.05 * v) * tt + k)
            l, rr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
            out[:, 0] += s * l
            out[:, 1] += s * rr
    e = np.ones(n)
    na = int(a * SR)
    e[:na] = np.linspace(0, 1, na) ** 2
    nd = int(dur * SR)
    e[nd:] = np.linspace(1, 0, n - nd) ** 2
    out *= e[:, None]
    return lp(out, 2400 * bright) / (len(notes) * 3)


def pluck(m, dur=0.9, bright=1.0):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f = midi(m)
    s = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt) * np.exp(-tt * 9)
         + 0.12 * np.sin(6 * np.pi * f * tt) * np.exp(-tt * 14))
    e = np.exp(-tt * 4.2 / dur * 0.9)
    e[: int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))
    return lp(s * e, 5000 * bright)


def bell(m, dur=3.0):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f = midi(m)
    s = (np.sin(2 * np.pi * f * tt) * np.exp(-tt * 1.4) + 0.4 * np.sin(2 * np.pi * f * 2.76 * tt) * np.exp(-tt * 3.5)
         + 0.2 * np.sin(2 * np.pi * f * 5.4 * tt) * np.exp(-tt * 6))
    s[: int(0.002 * SR)] *= np.linspace(0, 1, int(0.002 * SR))
    return s


def sub(m, dur, a=0.05, r=0.6):
    n = int((dur + r) * SR)
    tt = np.arange(n) / SR
    s = np.sin(2 * np.pi * midi(m) * tt) + 0.15 * np.sin(4 * np.pi * midi(m) * tt)
    return s * env_adsr(n, a, r)


def kick(f0=110, f1=42, dur=0.45, click=0.3):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-tt * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-tt * 7.5 / dur * 0.45)
    s[: int(0.003 * SR)] += click * rng.standard_normal(int(0.003 * SR))
    return s


def impact(size=1.0):
    n = int(3.5 * SR)
    tt = np.arange(n) / SR
    f = 34 + 120 * np.exp(-tt * 14)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 1.3)
    nz = lp(rng.standard_normal(n), 1800) * np.exp(-tt * 9) * 0.55
    hi = hp(rng.standard_normal(n), 4000) * np.exp(-tt * 18) * 0.12
    s = (boom * 1.0 + nz + hi) * size
    s[: int(0.002 * SR)] *= np.linspace(0, 1, int(0.002 * SR))
    return reverb(s, wet=0.3, seconds=3.0, damp=3500)


def riser(dur=1.9):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    p = tt / dur
    nz = rng.standard_normal(n)
    out = np.zeros(n)
    # sweep a band-pass upward in blocks
    blk = 2048
    for i in range(0, n, blk):
        c = 300 * (20 ** p[i])
        out[i:i + blk] = bp(nz[max(0, i - 4096):i + blk], c * 0.7, min(c * 1.6, 20000))[-len(out[i:i + blk]):]
    tone = np.sin(2 * np.pi * np.cumsum(110 * 2 ** (p * 3)) / SR) * 0.25
    s = (out * 0.8 + tone) * p ** 2.6
    s[-int(0.03 * SR):] *= np.linspace(1, 0, int(0.03 * SR))
    return reverb(s, wet=0.25, seconds=1.8)


def whoosh(dur=0.55, hi=1.0):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    p = tt / dur
    nz = rng.standard_normal(n)
    out = np.zeros(n)
    blk = 1024
    for i in range(0, n, blk):
        c = 400 + 3500 * hi * np.sin(np.pi * p[i]) ** 1.5
        seg = bp(nz[max(0, i - 2048):i + blk], c * 0.6, min(c * 1.5, 20000))
        out[i:i + blk] = seg[-len(out[i:i + blk]):]
    e = np.sin(np.pi * p) ** 2.2
    s = out * e
    st = np.stack([s * (1 - 0.6 * p), s * (0.4 + 0.6 * p)], 1)  # gentle L->R travel
    return st * 0.9


def tick(f=2600, dur=0.05):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    return np.sin(2 * np.pi * f * tt) * np.exp(-tt * 90) + 0.3 * hp(rng.standard_normal(n), 6000) * np.exp(-tt * 300)


def blip(m=84, dur=0.22):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    a = np.sin(2 * np.pi * midi(m) * tt) * np.exp(-tt * 22)
    b = np.zeros(n)
    k = int(0.06 * SR)
    b[k:] = np.sin(2 * np.pi * midi(m + 7) * tt[: n - k]) * np.exp(-tt[: n - k] * 18)
    return (a + b) * 0.5


def pop(m=79, dur=0.3):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f = midi(m) * (1 + 0.5 * np.exp(-tt * 60))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 16)


# ---------------------------------------------------------------- score v2
# Driving, curious, cinematic: D Phrygian ostinato (the b2 Eb keeps it
# unresolved), clock-like hats, pulsing bass, then a full drop at "At Urbn".
SBPM = 96
SB = 60 / SBPM          # beat
S16 = SB / 4
GRID0 = 0.85            # first downbeat = first frame of the cut


_cache = {}


def saw_note(m, dur, bright=1.0, decay=6.0, nh=24):
    """Band-limited saw with a filter-like decaying brightness (cached)."""
    key = (m, round(dur, 3), round(bright, 2), decay)
    if key in _cache:
        return _cache[key]
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f = midi(m)
    s = np.zeros(n)
    cut = 600 + 5000 * bright
    for h in range(1, nh + 1):
        if f * h > 16000:
            break
        # higher harmonics die faster -> plucky "string" envelope
        amp = (1 / h) * np.exp(-tt * decay * (1 + h * f / cut))
        s += amp * np.sin(2 * np.pi * f * h * tt)
    e = np.ones(n)
    a = int(0.003 * SR)
    e[:a] = np.linspace(0, 1, a)
    r = int(min(0.03, dur / 3) * SR)
    e[-r:] *= np.linspace(1, 0, r)
    _cache[key] = s * e
    return _cache[key]


def bass_note(m, dur, bright=0.5):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f = midi(m)
    s = np.sin(2 * np.pi * f * tt) * 1.0 + saw_note(m, dur, bright, 7.0, 10) * 0.6
    e = np.exp(-tt * 3.0)
    e[-int(0.02 * SR):] *= np.linspace(1, 0, int(0.02 * SR))
    return s * e


def hat(open_=False, dur=None):
    dur = dur or (0.25 if open_ else 0.05)
    n = int(dur * SR)
    tt = np.arange(n) / SR
    s = hp(rng.standard_normal(n), 7000, 4) * np.exp(-tt * (12 if open_ else 70))
    return s


def snare(dur=0.3):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    body = np.sin(2 * np.pi * 185 * tt) * np.exp(-tt * 30)
    nz = bp(rng.standard_normal(n), 1500, 9000) * np.exp(-tt * 14)
    return body * 0.6 + nz * 0.8


def clock(dur=0.04):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * 3100 * tt) + 0.6 * np.sin(2 * np.pi * 4700 * tt)) * np.exp(-tt * 160)


def grid(t0, t1, step, phase=0.0):
    k0 = int(np.ceil((t0 - GRID0 - phase) / step - 1e-6))
    t = GRID0 + phase + k0 * step
    while t < t1 - 1e-6:
        yield k0, t
        k0 += 1
        t += step


def score():
    mus = np.zeros((N, 2))
    bar = SB * 4

    # Chord tables (MIDI). Tension: D Phrygian / Dm with Eb. Lift: F major family.
    OST_T = [[62, 69, 74, 75], [62, 69, 74, 72], [62, 69, 70, 74], [62, 68, 74, 75]]   # D A D Eb / … / Ab (tritone)
    PROG_C = [(50, [50, 57, 62, 65]), (46, [46, 53, 58, 62]), (43, [43, 50, 55, 58]), (45, [45, 52, 57, 61])]
    PROG_D = [(41, [53, 60, 65, 69]), (48, [48, 55, 64, 67]), (50, [50, 57, 62, 65]), (46, [46, 53, 62, 65])]

    def ostinato(t0, t1, table, gain, bright, octave=0, pan=0.45, accent=True):
        for k, t in grid(t0, t1, S16):
            pat = table[(k // 16) % len(table)]
            m = pat[k % 4] + octave
            g = gain * (1.25 if (accent and k % 4 == 0) else 1.0)
            add(mus, saw_note(m, S16 * 1.6, bright, 9.0), t, g, pan=pan if k % 2 else -pan)

    def bassline(t0, t1, roots, gain, bright=0.4, pattern=(1, 0, 1, 1, 0, 1, 1, 0)):
        for k, t in grid(t0, t1, SB / 2):
            if not pattern[k % len(pattern)]:
                continue
            r = roots[(k // 8) % len(roots)]
            m = r + (12 if k % 8 == 3 else 0)
            add(mus, bass_note(m, SB / 2 * 0.9, bright), t, gain)

    def kicks(t0, t1, gain, every=1.0, f0=120):
        for k, t in grid(t0, t1, SB * every):
            add(mus, kick(f0, 44, 0.42, 0.02), t, gain)

    def hats(t0, t1, gain, step=S16, open_on=None):
        for k, t in grid(t0, t1, step):
            o = open_on is not None and k % open_on == open_on // 2
            add(mus, hat(o), t, gain * (0.6 + 0.4 * (k % 2 == 0)) * (1.4 if o else 1), pan=0.3 if k % 2 else -0.3)

    def snares(t0, t1, gain):
        for k, t in grid(t0, t1, SB):
            if k % 2 == 1:
                add(mus, snare(), t, gain)

    # A. Hook 0.85–6.62: tense and moving from the first frame
    add(mus, pad([38, 50, 57, 63], 5.9, a=0.05, r=0.1, bright=0.6), GRID0, 0.55)    # D + Eb cluster drone
    ostinato(GRID0, 6.55, OST_T, 0.050, 0.55)
    bassline(GRID0, 6.55, [26], 0.20, 0.35)
    kicks(GRID0, 6.55, 0.22, every=2)
    hats(GRID0, 6.55, 0.035)
    add(mus, riser(1.4), 5.2, 0.10)
    # 6.62: hard stop (impact in sfx); clock keeps ticking -> curiosity, not calm

    # B. 6.62–25.3: suspense. Ticking clock + low drone + sparse heartbeat bass
    for k, t in grid(6.62, 25.25, SB / 2):
        add(mus, clock(), t, 0.05 if k % 2 == 0 else 0.03, pan=0.35 if k % 2 else -0.35)
    add(mus, pad([38, 45, 51], 9.0, a=1.2, r=2.0, bright=0.45), 6.8, 0.75)            # D A Eb
    add(mus, pad([34, 46, 53, 51], 9.2, a=2.0, r=2.0, bright=0.45), 15.6, 0.75)        # Bb with Eb
    bassline(9.1, 16.2, [26], 0.12, 0.25, pattern=(1, 0, 0, 1, 0, 0, 1, 0))            # walking pulse under the map
    ostinato(9.1, 16.2, [[74, 69, 75, 69]], 0.018, 0.35, pan=0.6, accent=False)        # distant, searching
    for t, m in [(16.4, 75), (17.6, 74), (18.8, 70), (20.0, 69)]:
        add(mus, bell(m, 2.5), t, 0.03, pan=0.25)
    add(mus, pad([62, 63, 69], 3.6, a=0.02, r=1.5, bright=0.7), 21.62, 0.35)           # question: unresolved cluster
    add(mus, sub(26, 3.4, a=0.01, r=1.0), 21.62, 0.25)

    # C. 25.3–43.55: the problem builds — ostinato, bass, kick, hats, filter opening
    t0, t1 = 25.3, 43.5
    for k, t in grid(t0, t1, bar):
        root, chord = PROG_C[k % 4]
        add(mus, pad(chord, min(bar, t1 - t) + 0.05, a=0.3, r=0.8, bright=0.55 + 0.25 * (t - t0) / (t1 - t0)), t, 0.6)
    for seg0 in np.arange(t0, t1, bar):
        bright = 0.35 + 0.6 * (seg0 - t0) / (t1 - t0)
        ostinato(seg0, min(seg0 + bar, t1), OST_T, 0.04 + 0.03 * (seg0 - t0) / (t1 - t0), bright)
    bassline(t0, t1, [26, 22, 19, 21], 0.20, 0.45)
    kicks(t0, t1, 0.26)
    hats(t0, t1, 0.03)
    hats(34.0, t1, 0.02, step=SB, open_on=2)
    snares(34.6, t1, 0.10)
    for k, t in grid(41.65, 43.5, S16):        # snare roll into the drop
        add(mus, snare(0.12), t, 0.03 + 0.10 * (t - 41.65) / 1.85)
    # 43.55–43.87 silence, then the drop

    # D. 43.87–64.3: drive — the vision. F major family, full kit.
    t0, t1 = 43.87, 75.6
    for k, t in grid(t0, t1, bar, phase=(43.87 - GRID0) % bar):
        root, chord = PROG_D[k % 4]
        add(mus, pad(chord, min(bar, t1 - t) + 0.05, a=0.08, r=1.0, bright=0.9), t, 0.75)
    arp = [0, 1, 2, 3, 2, 1, 3, 2]
    for k, t in grid(t0, t1, S16, phase=(43.87 - GRID0) % S16):
        _, chord = PROG_D[int((t - t0) / bar) % 4]
        m = chord[arp[k % 8]] + 12
        add(mus, saw_note(m, S16 * 1.5, 0.9, 8.0), t, 0.045, pan=0.5 if k % 2 else -0.5)
    for k, t in grid(t0, t1, SB / 2, phase=(43.87 - GRID0) % (SB / 2)):
        root = PROG_D[int((t - t0) / bar) % 4][0]
        add(mus, bass_note(root - 12 + (12 if k % 4 == 3 else 0), SB / 2 * 0.9, 0.5), t, 0.22)
    for k, t in grid(t0, t1, SB, phase=(43.87 - GRID0) % SB):
        add(mus, kick(125, 44, 0.42, 0.02), t, 0.30)
        if k % 2 == 1:
            add(mus, snare(), t, 0.13)
    hats(t0, t1, 0.03)
    # E. 64.3–75.6 lift: high octave arp + open hats
    for k, t in grid(64.32, t1, S16):
        _, chord = PROG_D[int((t - t0) / bar) % 4]
        add(mus, saw_note(chord[(k * 3) % 4] + 24, S16 * 1.2, 1.0, 10.0), t, 0.022, pan=0.7 if k % 2 else -0.7)
    hats(64.32, t1, 0.03, step=SB, open_on=2)
    for k, t in grid(74.1, 75.6, S16):        # roll into the final line
        add(mus, snare(0.12), t, 0.03 + 0.08 * (t - 74.1) / 1.5)

    # F. Resolve: hold on "the digital infrastructure…", land on "housing."
    add(mus, pad([38, 50, 57, 62, 64], 2.2, a=0.05, r=0.6, bright=0.8), 75.72, 0.7)
    add(mus, sub(26, 2.0, a=0.01, r=0.4), 75.72, 0.2)
    for k, t in grid(75.72, 77.75, SB / 2):
        add(mus, clock(), t, 0.06)
    add(mus, pad([41, 53, 60, 65, 67, 72, 76], 5.0, a=0.02, r=3.0, bright=1.1), 77.81, 1.0)
    add(mus, sub(29, 4.0, a=0.01, r=2.5), 77.81, 0.28)
    for j, m in enumerate([77, 81, 84, 88]):
        add(mus, bell(m, 4.0), 79.1 + j * 0.18, 0.05, pan=-0.3 + 0.2 * j)

    mus = reverb(mus, wet=0.22, seconds=2.6, damp=6500)
    return mus


def sfx():
    s = np.zeros((N, 2))
    # hook
    add(s, impact(0.5), 0.85, 0.22)            # first frame lands on a hit
    add(s, blip(88), 1.75, 0.12, pan=-0.2)     # "Order placed"
    for ts, tb in [(2.95, 3.5), (4.28, 4.83)]:
        add(s, tick(2400), ts, 0.22)
        add(s, blip(88), tb, 0.12, pan=-0.2)
    add(s, whoosh(0.35, 1.0), 2.80, 0.18)
    add(s, whoosh(0.35, 1.0), 4.13, 0.18)
    # the turn
    add(s, impact(0.7), 6.60, 0.35)
    add(s, whoosh(0.6, 0.5), 8.75, 0.22)
    for ta in [11.45, 12.25, 12.95, 13.75, 14.6, 15.3]:
        add(s, pop(83, 0.2), ta, 0.09, pan=0.3)
        add(s, tick(900, 0.06), ta + 0.9, 0.08, pan=-0.2)
    add(s, whoosh(0.5, 0.4), 15.95, 0.16)
    add(s, impact(0.55), 21.62, 0.3)
    add(s, tick(1400, 0.08), 23.95, 0.18)
    for ts in [25.38, 27.02, 28.97]:
        add(s, tick(2100), ts, 0.15)
    for k, ts in enumerate([34.55, 35.66, 36.45, 37.15]):
        add(s, pop([76, 79, 81, 84][k], 0.25), ts, 0.12, pan=[-0.5, 0.5, -0.5, 0.5][k])
    add(s, whoosh(1.2, 0.35), 38.2, 0.14)
    add(s, riser(1.9), 41.65, 0.42)
    add(s, impact(1.0), 43.84, 0.55)
    add(s, whoosh(0.45, 0.8), 47.75, 0.18)
    add(s, whoosh(0.5, 0.6), 49.8, 0.14)
    add(s, blip(91), 50.45, 0.12)
    add(s, pop(72, 0.35), 51.47, 0.18)
    for k, ts in enumerate([51.49, 53.32, 54.27, 55.16, 55.97]):
        add(s, pop([77, 79, 81, 84, 86][k], 0.28), ts + 0.25, 0.13, pan=[-0.5, 0.5, -0.5, 0.5, 0][k])
    for j in range(30):
        add(s, tick(3000 + 60 * (j % 9), 0.03), 56.85 + j * 0.045, 0.025, pan=rng.uniform(-0.8, 0.8))
    add(s, whoosh(0.45, 0.8), 59.0, 0.2)
    add(s, whoosh(0.45, 0.8), 61.92, 0.2)
    add(s, tick(2100), 68.27, 0.13)
    add(s, tick(2400), 69.63, 0.13)
    add(s, whoosh(0.8, 0.6), 71.1, 0.16)
    add(s, impact(0.45), 75.72, 0.22)
    add(s, riser(1.4), 76.4, 0.22)
    add(s, impact(1.0), 77.79, 0.5)
    add(s, whoosh(1.2, 0.3), 78.85, 0.12)
    return s


def voice():
    """Clean the founder's dialogue with ffmpeg: rumble cut, broadband denoise,
    de-box, presence, de-ess, gentle compression, normalised to -16 LUFS."""
    src = os.path.join(ROOT, "1001.mp4")
    tmp = os.path.join(ROOT, "edit", "_voice.wav")
    chain = ",".join([
        "highpass=f=75",
        "afftdn=nr=10:nf=-42:tn=1",
        "equalizer=f=280:t=q:w=1.1:g=-2.5",
        "equalizer=f=140:t=q:w=0.8:g=1.2",
        "equalizer=f=3600:t=q:w=1.0:g=2.2",
        "equalizer=f=11000:t=q:w=0.8:g=1.0",
        "deesser=i=0.35:m=0.5:f=0.5",
        "acompressor=threshold=-21dB:ratio=3:attack=6:release=120:makeup=2",
        "loudnorm=I=-16:TP=-2:LRA=7",
        "aresample=48000",
    ])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-af", chain, "-ac", "1", tmp], check=True)
    v, sr = sf.read(tmp)
    os.remove(tmp)
    assert sr == SR
    out = np.zeros(N)
    out[: min(N, len(v))] = v[:N]
    return out


def duck_curve(v):
    """Music gain that dips under speech (smooth attack/release)."""
    hop = 480
    env = np.sqrt(np.convolve(v ** 2, np.ones(hop * 4) / (hop * 4), "same"))[::hop]
    db = 20 * np.log10(env + 1e-9)
    speech = (db > -42).astype(float)
    g = np.zeros_like(speech)
    a_att, a_rel = 1 - np.exp(-1 / (0.06 * SR / hop)), 1 - np.exp(-1 / (0.5 * SR / hop))
    for i in range(len(speech)):
        prev = g[i - 1] if i else 0
        a = a_att if speech[i] > prev else a_rel
        g[i] = prev + (speech[i] - prev) * a
    gain_db = -6.0 * g
    gl = 10 ** (gain_db / 20)
    return np.interp(np.arange(N), np.arange(len(gl)) * hop, gl)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "edit", "mix.wav")
    v = voice()
    mus = score()
    fx = sfx()
    duck = duck_curve(v)
    # Score level automation (dB): bright hook, hushed confession, building
    # tension, lift at the reveal, music forward on the end card.
    auto = [(0, -11), (6.5, -11), (6.62, -15), (25.2, -15), (25.4, -12.5), (43.5, -10.5), (43.87, -13),
            (64.0, -13), (64.3, -11.5), (75.5, -10.5), (77.8, -11), (TOTAL, -11)]
    at, ag = zip(*auto)
    mus *= (10 ** (np.interp(np.arange(N) / SR, at, ag) / 20))[:, None]
    mus *= duck[:, None]
    fx *= 10 ** (-5 / 20)
    # keep music clear of the voice's presence band a touch
    mus = mus - 0.25 * bp(mus, 1800, 4500, 1)
    mix = np.stack([v, v], 1) + mus + fx
    # fade in/out
    fi = int(0.02 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)[:, None]
    # the cut starts at OFFSET (dead air before the first word is trimmed)
    k = int(OFFSET * SR)
    mix, mus, fx = mix[k:], mus[k:], fx[k:]
    fi = int(0.01 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)[:, None]
    sf.write(out, mix.astype(np.float32), SR, subtype="FLOAT")
    sf.write(out.replace(".wav", "_music.wav"), (mus + fx).astype(np.float32), SR, subtype="FLOAT")
    print("peak", np.abs(mix).max())


if __name__ == "__main__":
    main()
