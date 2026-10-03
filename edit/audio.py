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


# ---------------------------------------------------------------- score
def score():
    mus = np.zeros((N, 2))
    D2, F2, A2, Bb1, C2, G2 = 38, 41, 45, 34, 36, 43

    # A. Hook (0–6.62): light, quick, "everything is easy" pluck ostinato in F
    arp_a = [65, 72, 69, 77, 72, 69, 76, 72]   # F4 C5 A4 F5 C5 A4 E5 C5
    t = 0.12
    i = 0
    while t < 6.55:
        add(mus, pluck(arp_a[i % 8], 0.7), t, 0.16, pan=(-0.35 if i % 2 else 0.35))
        t += BEAT / 2
        i += 1
    add(mus, pad([53, 60, 64, 69], 6.3, a=0.6, r=0.05, bright=1.1), 0.0, 0.5)

    # B. Problem, intimate (6.62–25.3): dark Dm drone, sparse
    add(mus, pad([D2 + 12, A2 + 12, 53, 57], 9.2, a=2.5, r=2.0, bright=0.55), 6.9, 0.85)
    add(mus, pad([Bb1 + 12, 50, 53, 58], 9.0, a=2.5, r=2.5, bright=0.55), 15.6, 0.85)
    add(mus, sub(D2 - 12, 8.5, a=1.5, r=1.5), 6.9, 0.18)
    add(mus, sub(Bb1 - 12, 8.0, a=1.5, r=1.5), 15.6, 0.16)
    for k, tt in enumerate(np.arange(9.4, 16.0, BEAT * 2)):     # soft footsteps-like pulse under the map
        add(mus, kick(70, 40, 0.3, 0.05), tt, 0.10)
    for tt, m in [(16.4, 74), (18.8, 72), (21.75, 69)]:        # lonely high notes
        add(mus, bell(m, 3.0), tt, 0.035, pan=0.2)

    # C. Tension (25.3–43.8): pulse + ostinato, progression Dm–Bb–Gm–A
    prog_c = [([50, 57, 62, 65], D2), ([46, 53, 58, 62], Bb1 + 12), ([43, 50, 55, 58], G2 - 12 + 12), ([45, 52, 57, 61], A2 - 12 + 12)]
    t0 = 25.3
    bar = BEAT * 4
    k = 0
    tt = t0
    while tt < 43.3:
        chord, root = prog_c[k % 4]
        L = min(bar * 1.0, 43.55 - tt)
        add(mus, pad(chord, L, a=0.8, r=1.2, bright=0.65 + 0.03 * k), tt, 0.7 + 0.04 * k)
        add(mus, sub(root - 12, L - 0.1, a=0.2, r=0.5), tt, 0.17)
        k += 1
        tt += bar
    ost = [74, 69, 65, 69]
    tt, i = t0, 0
    while tt < 43.5:
        g = 0.035 + 0.07 * (tt - t0) / 18
        add(mus, pluck(ost[i % 4] - (0 if (int((tt - t0) / bar) % 4) < 2 else 2), 0.5, 0.7), tt, g,
            pan=(-0.4 if i % 2 else 0.4))
        tt += BEAT / 2
        i += 1
    tt = t0
    while tt < 43.5:
        g = 0.12 + 0.12 * (tt - t0) / 18
        add(mus, kick(95, 42, 0.4, 0.02), tt, g)
        tt += BEAT
    # Pre-drop silence 43.55–43.87 is left empty on purpose.

    # D. Vision (43.87–64.3): lift to F major, I–V–vi–IV
    prog_d = [([53, 60, 65, 69, 72], F2), ([48, 55, 64, 67, 72], C2 + 12), ([50, 57, 62, 65, 69], D2), ([46, 53, 62, 65, 70], Bb1 + 12)]
    t0 = 43.87
    tt, k = t0, 0
    while tt < 75.6:
        chord, root = prog_d[k % 4]
        L = min(bar, 75.75 - tt)
        bright = 0.85 + 0.02 * k
        add(mus, pad(chord, L, a=0.35, r=1.4, bright=bright), tt, 0.85 + 0.03 * k)
        add(mus, sub(root - 12, L - 0.05, a=0.05, r=0.6), tt, 0.2)
        k += 1
        tt += bar
    arp_d = [0, 2, 1, 3, 2, 4, 3, 2]
    tt, i = t0, 0
    while tt < 75.6:
        chord, _ = prog_d[int((tt - t0) / bar) % 4]
        m = chord[arp_d[i % 8] % len(chord)] + 12
        g = 0.05 + 0.06 * min(1, (tt - t0) / 25)
        add(mus, pluck(m, 0.65, 1.1), tt, g, pan=(-0.45 if i % 2 else 0.45))
        tt += BEAT / 2
        i += 1
    tt = t0
    while tt < 75.6:
        g = 0.16 + 0.10 * min(1, (tt - t0) / 25)
        add(mus, kick(105, 44, 0.45, 0.03), tt, g)
        tt += BEAT
    # E. lift: high shimmer layer from 64.3
    for tt in np.arange(64.32, 75.5, BEAT / 4):
        chord, _ = prog_d[int((tt - t0) / bar) % 4]
        add(mus, pluck(chord[int(tt * 7) % len(chord)] + 24, 0.3, 1.2), tt, 0.018, pan=rng.uniform(-0.8, 0.8))

    # F. Resolve (75.7 →): F add9 swell, long ring on the end card
    add(mus, pad([41, 53, 60, 65, 67, 72], 6.5, a=1.2, r=3.0, bright=1.0), 75.72, 0.9)
    add(mus, pad([41, 48, 57, 65, 67, 72, 76], 4.2, a=0.05, r=3.0, bright=1.15), 77.81, 1.0)
    add(mus, sub(F2 - 12, 4.0, a=0.02, r=2.5), 77.81, 0.26)
    for j, m in enumerate([77, 81, 84, 88]):
        add(mus, bell(m, 4.0), 79.1 + j * 0.18, 0.05, pan=-0.3 + 0.2 * j)

    mus = reverb(mus, wet=0.32, seconds=3.6, damp=6000)
    return mus


def sfx():
    s = np.zeros((N, 2))
    # hook
    add(s, whoosh(0.9, 0.6), 0.1, 0.18)
    for ts, tb in [(0.95, 1.5), (2.95, 3.5), (4.28, 4.83)]:
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
    auto = [(0, -10), (6.5, -10), (6.62, -19), (25.2, -18), (25.4, -17), (43.5, -14.5), (43.87, -16),
            (64.0, -16), (75.5, -14), (77.8, -11), (TOTAL, -11)]
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
    sf.write(out, mix.astype(np.float32), SR, subtype="FLOAT")
    sf.write(out.replace(".wav", "_music.wav"), (mus + fx).astype(np.float32), SR, subtype="FLOAT")
    print("peak", np.abs(mix).max())


if __name__ == "__main__":
    main()
