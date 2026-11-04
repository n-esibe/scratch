"""Natural ambient soundtrack for the ship reel (no music), synthesized:
0-3 s  engine hum + choppy waves lapping against the hull + hull creaks + light wind
3.0 s  one distant ship horn
3-6 s  engine fades, water calms
6-10 s quiet, clean sea sound behind the poster."""
import sys
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile

SR = 48000
N = int(SR * 10.0)
T = np.arange(N) / SR
rng = np.random.default_rng(42)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo / (SR / 2), hi / (SR / 2)], btype='band', output='sos'), x)


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc / (SR / 2), output='sos'), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc / (SR / 2), btype='high', output='sos'), x)


def norm(x):
    return x / (np.max(np.abs(x)) + 1e-12)


def smooth_env(points):
    """piecewise-linear envelope from (time, value) points, smoothed"""
    ts, vs = zip(*points)
    e = np.interp(T, ts, vs)
    return lp(e, 6, 1)


def pink(n):
    w = rng.standard_normal(n)
    f = np.fft.rfft(w)
    k = np.arange(len(f)); k[0] = 1
    return norm(np.fft.irfft(f / np.sqrt(k), n))


L = np.zeros(N); R = np.zeros(N)


def add(sig, start=0.0, pan=0.0, gain=1.0):
    i = int(start * SR)
    if i >= N:
        return
    j = min(N, i + len(sig))
    L[i:j] += sig[:j - i] * gain * np.sqrt(0.5 * (1 - pan))
    R[i:j] += sig[:j - i] * gain * np.sqrt(0.5 * (1 + pan))


# ---------------- engine hum (fades 3 -> 5.6 s) ----------------
engine_env = smooth_env([(0, 1), (3.0, 1), (4.4, 0.35), (5.6, 0.0), (10, 0)])
f0 = 23.0 * (1 + 0.004 * np.sin(2 * np.pi * 0.3 * T))
ph = 2 * np.pi * np.cumsum(f0) / SR
eng = np.zeros(N)
for k in range(1, 26):
    f = 23.0 * k
    a = np.exp(-((np.log(f) - np.log(110)) ** 2) / 1.2)    # energy centred ~110 Hz
    eng += a * np.sin(k * ph + rng.uniform(0, 6.28))
chug = 1 + 0.25 * np.sin(ph / 2)                              # diesel firing pulse
mech = bp(rng.standard_normal(N), 140, 520) * 0.35
eng = lp(norm(eng * chug) + norm(mech) * 0.25, 650)
add(norm(eng) * engine_env, pan=-0.25, gain=0.30)

# ---------------- hull creaks ----------------
def creak(dur, r0, r1, amp):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    rate = r0 + (r1 - r0) * (tt / dur) + 6 * np.sin(2 * np.pi * 7 * tt)
    phase = np.cumsum(rate) / SR
    imp = np.zeros(n)
    idx = np.where(np.diff(np.floor(phase)) > 0)[0]
    imp[idx] = rng.uniform(0.6, 1.0, len(idx))
    s = bp(imp, 230, 280, 2) * 2.2 + bp(imp, 520, 600, 2) * 1.4 + bp(imp, 940, 1080, 2) * 0.8
    e = np.sin(np.pi * tt / dur) ** 0.7
    return amp * norm(s) * e

add(creak(0.55, 28, 55, 1.0), 0.75, pan=-0.35, gain=0.05)
add(creak(0.4, 40, 22, 1.0), 2.05, pan=-0.2, gain=0.04)
add(creak(0.5, 30, 48, 1.0), 3.6, pan=-0.45, gain=0.022)

# ---------------- waves: continuous wash + slaps against the hull ----------------
chop = smooth_env([(0, 1), (3.0, 1), (5.2, 0.55), (6.5, 0.5), (10, 0.48)])
for ch, pan in ((0, -0.7), (1, 0.7)):
    wash = lp(hp(pink(N), 90), 1500)
    swell = 0.65 + 0.35 * np.sin(2 * np.pi * (0.21 + 0.03 * ch) * T + ch * 1.7) ** 2
    add(norm(wash) * swell * (0.45 + 0.55 * chop), pan=pan, gain=0.13)

def slap(amp, bright):
    n = int(0.35 * SR)
    tt = np.arange(n) / SR
    x = rng.standard_normal(n)
    s = bp(x, 180, 900 + 900 * bright) * np.exp(-tt / 0.07) * np.minimum(1, tt / 0.006)
    s += 0.5 * lp(x, 300) * np.exp(-tt / 0.12)
    return amp * norm(s)

def bubble(f, amp):
    n = int(0.06 * SR)
    tt = np.arange(n) / SR
    fr = f * (1 + 2.5 * tt / 0.06)
    return amp * np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-tt / 0.018)

t = 0.05
while t < 9.9:
    k = float(np.interp(t, T, chop))
    add(slap(rng.uniform(0.5, 1.0) * k, k), t, pan=rng.uniform(-0.6, 0.6), gain=0.16)
    for _ in range(rng.integers(1, 4)):
        add(bubble(rng.uniform(350, 1100), 0.5 * k), t + rng.uniform(0.02, 0.2), pan=rng.uniform(-.7, .7), gain=0.05)
    t += rng.uniform(0.22, 0.5) / max(0.45, k) * (1.0 if k > 0.6 else 1.6)

# ---------------- light night wind ----------------
wind_env = smooth_env([(0, 0.8), (3, 0.9), (6, 0.5), (10, 0.35)])
for ch, pan in ((0, -0.8), (1, 0.8)):
    w = bp(rng.standard_normal(N), 350, 1800)
    gust = 0.5 + 0.5 * np.sin(2 * np.pi * (0.13 + 0.05 * ch) * T + ch) ** 2
    add(norm(w) * gust * wind_env, pan=pan, gain=0.028)

# ---------------- one distant ship horn at 3.0 s ----------------
hd = 2.3
hn = int(hd * SR)
ht = np.arange(hn) / SR
hf = 92 * (1 + 0.02 * (1 - np.exp(-ht / 0.12)))     # slight pitch settle at onset
hph = 2 * np.pi * np.cumsum(hf) / SR
horn = sum((1 / k ** 0.9) * np.sin(k * hph) for k in range(1, 40))
horn += 0.6 * sum((1 / k) * np.sin(k * hph * 1.26) for k in range(1, 25))   # second whistle tone (major third)
henv = np.minimum(1, ht / 0.18) * np.clip((hd - ht) / 0.55, 0, 1)
horn = lp(norm(horn) * henv, 900, 4)                 # distance: highs absorbed
# outdoor reverb + an echo off the coast
irn = int(3.2 * SR); it = np.arange(irn) / SR
ir = lp(rng.standard_normal(irn), 2500) * np.exp(-it * 1.6)
ir[int(0.42 * SR)] += 6.0
horn_wet = fftconvolve(horn, ir / np.sqrt(np.sum(ir ** 2)))
horn_mix = norm(0.55 * np.pad(horn, (0, len(horn_wet) - len(horn))) + 0.6 * norm(horn_wet))
add(horn_mix, 3.0, pan=0.15, gain=0.30)

# ---------------- master ----------------
out = np.stack([L, R], 1)
out = sosfilt(butter(2, 28 / (SR / 2), btype='high', output='sos'), out, axis=0)
fade_in = np.minimum(1, T / 0.01)
fade_out = np.clip((10.0 - T) / 0.25, 0, 1)
out *= (fade_in * fade_out)[:, None]
out = out / np.max(np.abs(out)) * 0.66
wavfile.write(sys.argv[1] if len(sys.argv) > 1 else 'ambience.wav', SR, (out * 32767).astype(np.int16))
print('ok')
