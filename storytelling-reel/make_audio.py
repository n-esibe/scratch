"""Synthesizes the 10 s soundtrack: gentle opening accent, warm pad, oud-like plucks
(Karplus-Strong, Hijaz mode on D), sea wash during the sea shot, soft whoosh transitions."""
import sys
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile

SR = 48000
DUR = 10.0
N = int(SR * DUR)
rng = np.random.default_rng(3)
t = np.arange(N) / SR


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def env_adsr(n, a, d, s, r, sus_len):
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    s_n = max(0, int(sus_len * SR))
    e = np.concatenate([
        np.linspace(0, 1, a_n, endpoint=False) ** 2,
        np.linspace(1, s, d_n, endpoint=False),
        np.full(s_n, s),
        np.linspace(s, 0, r_n) ** 1.5 * s / max(s, 1e-9) if s > 0 else np.zeros(r_n),
    ])
    out = np.zeros(n)
    out[:min(n, len(e))] = e[:n]
    return out


def place(buf, sig, start):
    i = int(start * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[:j - i]


# ---------- opening accent: soft bell + low warm thump ----------
def bell(f, dur=3.5, amp=0.35):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    partials = [(1.0, 1.0, 1.6), (2.0, 0.35, 1.1), (2.76, 0.25, 0.8), (5.4, 0.10, 0.4), (8.93, 0.05, 0.25)]
    s = sum(a * np.sin(2 * np.pi * f * r * tt) * np.exp(-tt / d) for r, a, d in partials)
    att = np.minimum(1, tt / 0.004)
    return amp * s * att


def thump(dur=1.2, amp=0.5):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f = 70 * np.exp(-tt * 2.5) + 42
    ph = 2 * np.pi * np.cumsum(f) / SR
    return amp * np.sin(ph) * np.exp(-tt * 4.0) * np.minimum(1, tt / 0.01)


# ---------- oud-like pluck (Karplus-Strong + body resonance) ----------
def pluck(f, dur=2.2, amp=0.5, bright=0.55):
    n = int(dur * SR)
    p = int(round(SR / f))
    buf = rng.uniform(-1, 1, p)
    # soften the excitation (plectrum on gut/nylon)
    sos = butter(2, min(0.99, 2 * f * 6 / SR * (1 + bright * 4)), output='sos')
    buf = sosfilt(sos, buf)
    out = np.empty(n)
    decay = 0.996
    idx = 0
    for i in range(n):
        v = buf[idx]
        nxt = buf[(idx + 1) % p]
        buf[idx] = decay * 0.5 * (v + nxt)
        out[i] = v
        idx = (idx + 1) % p
    # body resonances
    body = np.zeros_like(out)
    for fc, q, g in [(150, 4, 0.25), (260, 5, 0.45), (480, 6, 0.35)]:
        bw = fc / q
        sosb = butter(2, [max(20, fc - bw / 2) / (SR / 2), (fc + bw / 2) / (SR / 2)], btype='band', output='sos')
        body += g * sosfilt(sosb, out)
    sig = out * 0.8 + body * 1.4
    tt = np.arange(n) / SR
    sig *= np.exp(-tt * 1.1)
    sig /= np.max(np.abs(sig)) + 1e-9
    return amp * sig


# ---------- pad ----------
def pad_voice(f, start, end, amp, attack=1.6, release=1.6):
    n = int((end - start + release) * SR)
    tt = np.arange(n) / SR
    vib = 1 + 0.0025 * np.sin(2 * np.pi * 0.23 * tt + rng.uniform(0, 6))
    s = np.zeros(n)
    for det in (-0.004, 0.0, 0.0045):
        ph = 2 * np.pi * np.cumsum(f * (1 + det) * vib) / SR
        for h in range(1, 7):
            s += np.sin(h * ph + rng.uniform(0, 6)) / h ** 1.8
    e = env_adsr(n, attack, 0.5, 0.85, release, (end - start) - attack - 0.5)
    sig = s * e
    sos = butter(2, 1800 / (SR / 2), output='sos')
    return amp * sosfilt(sos, sig) / 3


# ---------- noise beds ----------
def colored_noise(n, lp, hp=None):
    x = rng.standard_normal(n)
    sos = butter(2, lp / (SR / 2), output='sos')
    x = sosfilt(sos, x)
    if hp:
        x = sosfilt(butter(2, hp / (SR / 2), btype='high', output='sos'), x)
    return x / (np.max(np.abs(x)) + 1e-9)


def whoosh(dur, amp, f0, f1):
    n = int(dur * SR)
    x = rng.standard_normal(n)
    out = np.zeros(n)
    blk = 512
    for i in range(0, n, blk):
        p = i / n
        fc = f0 * (f1 / f0) ** p
        sos = butter(2, [fc * 0.7 / (SR / 2), min(0.99, fc * 1.4 / (SR / 2))], btype='band', output='sos')
        out[i:i + blk] = sosfilt(sos, x[i:i + blk])
    e = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    return amp * out * e / (np.max(np.abs(out)) + 1e-9)


L = np.zeros(N)
Rch = np.zeros(N)


def add(sig, start, pan=0.0, gain=1.0):
    l = np.sqrt(0.5 * (1 - pan)) * gain
    r = np.sqrt(0.5 * (1 + pan)) * gain
    place(L, sig * l, start)
    place(Rch, sig * r, start)


# 1) Opening accent (first second)
add(bell(hz(74), amp=0.30), 0.03, pan=-0.15)        # D5
add(bell(hz(81), amp=0.16), 0.05, pan=0.25)         # A5
add(thump(amp=0.30), 0.0)

# 2) Pad: D drone, colour shift in the sea shot, warm resolve at the info shot
D3, A3, D4, Eb4, Fs4, G4, A4, Bb3 = 50, 57, 62, 63, 66, 67, 69, 58
for m, a in [(38, 0.07), (D3, 0.11), (A3, 0.10), (D4, 0.08)]:
    add(pad_voice(hz(m), 0.0, 10.0, a, attack=0.8), 0.0, pan=rng.uniform(-.3, .3))
add(pad_voice(hz(Bb3), 3.0, 6.2, 0.07, attack=1.0, release=1.0), 3.0, pan=-0.3)
add(pad_voice(hz(Fs4), 6.0, 10.0, 0.06, attack=0.9), 6.0, pan=0.3)

# 3) Oud-like plucks — Hijaz phrase; in shot 3 each pluck lands with a text line
phrase = [
    (0.55, D4, .42), (1.05, Eb4, .30), (1.35, Fs4, .34), (1.95, G4, .32), (2.45, Fs4, .30),
    (3.05, Eb4, .28), (3.9, A4, .30), (4.7, G4, .26), (5.4, Fs4, .26),
    (6.35, D4, .40), (6.95, A3, .34), (7.55, D4, .34), (8.15, Fs4, .36), (8.6, A4, .40),
    (9.15, D3, .30), (9.15, D4, .32),
]
for i, (st, m, a) in enumerate(phrase):
    add(pluck(hz(m), dur=2.4, amp=a), st, pan=(-0.2 if i % 2 else 0.2))
# little tremolo grace (typical oud ornament) before the final note
for k in range(4):
    add(pluck(hz(Eb4), dur=0.5, amp=0.10), 8.95 + k * 0.045, pan=0.1)

# 4) Sea wash during shot 2
sea_n = int(3.6 * SR)
st = np.arange(sea_n) / SR
sea_env = np.clip(np.minimum(st / 0.9, (3.6 - st) / 1.0), 0, 1) ** 1.5
swell = 0.6 + 0.4 * np.sin(2 * np.pi * 0.55 * st - 1.2) ** 2
wash_l = colored_noise(sea_n, 900, 80) * sea_env * swell * 0.16
wash_r = colored_noise(sea_n, 900, 80) * sea_env * np.roll(swell, 4000) * 0.16
place(L, wash_l, 2.8)
place(Rch, wash_r, 2.8)

# 5) Transitions
add(whoosh(1.1, 0.10, 300, 3500), 2.5, pan=-0.2)
add(whoosh(0.9, 0.07, 2500, 400), 5.5, pan=0.2)
add(bell(hz(86), amp=0.06), 6.0, pan=0.4)            # soft sparkle as the poster returns

# ---------- reverb ----------
ir_n = int(2.6 * SR)
it = np.arange(ir_n) / SR
ir_l = rng.standard_normal(ir_n) * np.exp(-it * 2.6)
ir_r = rng.standard_normal(ir_n) * np.exp(-it * 2.6)
lp = butter(1, 5000 / (SR / 2), output='sos')
ir_l, ir_r = sosfilt(lp, ir_l), sosfilt(lp, ir_r)
ir_l /= np.sqrt(np.sum(ir_l ** 2)); ir_r /= np.sqrt(np.sum(ir_r ** 2))
wet_l = fftconvolve(L, ir_l)[:N]
wet_r = fftconvolve(Rch, ir_r)[:N]
outL = L * 0.75 + wet_l * 0.45
outR = Rch * 0.75 + wet_r * 0.45

# master fade-out and normalise
fade = np.ones(N)
fs_ = int(9.2 * SR)
fade[fs_:] = np.linspace(1, 0, N - fs_) ** 1.5
fade[:int(0.004 * SR)] = np.linspace(0, 1, int(0.004 * SR))
hp = butter(2, 85 / (SR / 2), btype='high', output='sos')
low = butter(2, 250 / (SR / 2), output='sos')
outL = sosfilt(hp, outL) - 0.35 * sosfilt(low, outL)
outR = sosfilt(hp, outR) - 0.35 * sosfilt(low, outR)
outL *= fade; outR *= fade
peak = max(np.max(np.abs(outL)), np.max(np.abs(outR)))
out = np.stack([outL, outR], axis=1) / peak * 0.89
wavfile.write(sys.argv[1] if len(sys.argv) > 1 else 'soundtrack.wav', SR, (out * 32767).astype(np.int16))
print('ok', peak)
