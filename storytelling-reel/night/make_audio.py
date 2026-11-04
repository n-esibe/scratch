"""Sound design for the night reel (no music), synthesized:
0.0 s      hook: ship engine, waves, one ship horn
2.5-5.0 s  engine fades away -> only waves and wind
5.0 s      light bell / sparkle accent for the transition
7.5-10 s   quiet sea + soft wind under the end frame
9.0 s      short click for the CTA button (added in post)"""
import sys
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile

SR = 48000
N = int(SR * 10.0)
T = np.arange(N) / SR
rng = np.random.default_rng(7)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo / (SR / 2), hi / (SR / 2)], btype='band', output='sos'), x)


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc / (SR / 2), output='sos'), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc / (SR / 2), btype='high', output='sos'), x)


def norm(x):
    return x / (np.max(np.abs(x)) + 1e-12)


def env(points):
    ts, vs = zip(*points)
    return lp(np.interp(T, ts, vs), 6, 1)


def pink(n):
    f = np.fft.rfft(rng.standard_normal(n))
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


def reverb(x, secs, decay, bright=4000, wet=0.5):
    n = int(secs * SR); it = np.arange(n) / SR
    ir = lp(rng.standard_normal(n), bright) * np.exp(-it * decay)
    ir /= np.sqrt(np.sum(ir ** 2))
    y = fftconvolve(x, ir)
    return norm(np.pad(x, (0, len(y) - len(x))) * (1 - wet) + norm(y) * wet)


# ---------------- engine: full at the hook, fades 2.5 -> 4.6 s ----------------
eng_env = env([(0, 1), (2.5, 1), (3.6, 0.3), (4.6, 0), (10, 0)])
f0 = 23.0 * (1 + 0.004 * np.sin(2 * np.pi * 0.3 * T))
ph = 2 * np.pi * np.cumsum(f0) / SR
eng = np.zeros(N)
for k in range(1, 26):
    f = 23.0 * k
    eng += np.exp(-((np.log(f) - np.log(110)) ** 2) / 1.2) * np.sin(k * ph + rng.uniform(0, 6.28))
eng = lp(norm(eng * (1 + 0.25 * np.sin(ph / 2))) + 0.25 * norm(bp(rng.standard_normal(N), 140, 520)), 650)
add(norm(eng) * eng_env, pan=-0.2, gain=0.30)

# ---------------- hull creaks (only while the ship is close) ----------------
def creak(dur, r0, r1):
    n = int(dur * SR); tt = np.arange(n) / SR
    phase = np.cumsum(r0 + (r1 - r0) * tt / dur + 6 * np.sin(2 * np.pi * 7 * tt)) / SR
    imp = np.zeros(n); idx = np.where(np.diff(np.floor(phase)) > 0)[0]
    imp[idx] = rng.uniform(0.6, 1.0, len(idx))
    s = bp(imp, 230, 280) * 2.2 + bp(imp, 520, 600) * 1.4 + bp(imp, 940, 1080) * 0.8
    return norm(s) * np.sin(np.pi * tt / dur) ** 0.7

add(creak(0.5, 28, 52), 1.1, pan=-0.3, gain=0.045)
add(creak(0.4, 42, 24), 2.1, pan=-0.15, gain=0.035)

# ---------------- waves: wash + slaps + gurgles ----------------
chop = env([(0, 1), (2.5, 1), (4.6, 0.6), (7.5, 0.5), (10, 0.45)])
for ch, pan in ((0, -0.7), (1, 0.7)):
    wash = lp(hp(pink(N), 90), 1500)
    swell = 0.65 + 0.35 * np.sin(2 * np.pi * (0.21 + 0.03 * ch) * T + ch * 1.7) ** 2
    add(norm(wash) * swell * (0.5 + 0.5 * chop), pan=pan, gain=0.2)


def slap(amp, bright):
    n = int(0.35 * SR); tt = np.arange(n) / SR
    x = rng.standard_normal(n)
    s = bp(x, 180, 900 + 900 * bright) * np.exp(-tt / 0.07) * np.minimum(1, tt / 0.006)
    s += 0.5 * lp(x, 300) * np.exp(-tt / 0.12)
    return amp * norm(s)


def bubble(f, amp):
    n = int(0.06 * SR); tt = np.arange(n) / SR
    return amp * np.sin(2 * np.pi * np.cumsum(f * (1 + 2.5 * tt / 0.06)) / SR) * np.exp(-tt / 0.018)


t = 0.05
while t < 9.9:
    k = float(np.interp(t, T, chop))
    add(slap(rng.uniform(0.5, 1.0) * k, k), t, pan=rng.uniform(-0.6, 0.6), gain=0.2)
    for _ in range(rng.integers(1, 4)):
        add(bubble(rng.uniform(350, 1100), 0.5 * k), t + rng.uniform(0.02, 0.2), pan=rng.uniform(-.7, .7), gain=0.045)
    t += rng.uniform(0.22, 0.5) / max(0.45, k) * (1.0 if k > 0.7 else 1.5)

# ---------------- wind: light, more noticeable once the engine is gone ----------------
wind_env = env([(0, 0.6), (2.5, 0.8), (4.0, 1.0), (5.5, 1.0), (7.5, 0.65), (10, 0.55)])
for ch, pan in ((0, -0.8), (1, 0.8)):
    w = bp(rng.standard_normal(N), 300, 1700)
    gust = 0.45 + 0.55 * np.sin(2 * np.pi * (0.13 + 0.05 * ch) * T + ch) ** 2
    add(norm(w) * gust * wind_env, pan=pan, gain=0.06)

# ---------------- hook: one ship horn right at the start ----------------
hd = 2.0
ht = np.arange(int(hd * SR)) / SR
hf = 92 * (1 + 0.02 * (1 - np.exp(-ht / 0.1)))
hph = 2 * np.pi * np.cumsum(hf) / SR
horn = sum((1 / k ** 0.9) * np.sin(k * hph) for k in range(1, 40))
horn += 0.6 * sum((1 / k) * np.sin(k * hph * 1.26) for k in range(1, 25))
horn = lp(norm(horn) * np.minimum(1, ht / 0.12) * np.clip((hd - ht) / 0.5, 0, 1), 1300, 4)
add(reverb(horn, 3.0, 1.7, 2500, 0.45), 0.08, pan=0.1, gain=0.26)

# ---------------- 5.0 s: light bell / sparkle for the transition ----------------
def bell(f, dur=2.6):
    tt = np.arange(int(dur * SR)) / SR
    parts = [(1.0, 1.0, 1.4), (2.0, 0.3, 0.9), (2.76, 0.22, 0.6), (5.4, 0.08, 0.3)]
    return sum(a * np.sin(2 * np.pi * f * r * tt) * np.exp(-tt / d) for r, a, d in parts) * np.minimum(1, tt / 0.003)

spark = np.zeros(int(3.2 * SR))
for i, (f, dt, a) in enumerate([(1568, 0.0, 1.0), (2093, 0.05, 0.7), (2637, 0.11, 0.55), (3136, 0.17, 0.45), (3951, 0.24, 0.35), (4699, 0.31, 0.25)]):
    b = bell(f) * a
    s0 = int(dt * SR); spark[s0:s0 + len(b)] += b[:len(spark) - s0]
shimmer = hp(rng.standard_normal(len(spark)), 6000) * np.exp(-np.arange(len(spark)) / SR / 0.5) * 0.08
spark = reverb(norm(spark + shimmer), 2.4, 2.0, 7000, 0.4)
add(spark, 4.98, pan=0.0, gain=0.2)

# ---------------- 9.0 s: short UI click for the CTA ----------------
cn = int(0.05 * SR); ct = np.arange(cn) / SR
click = 0.8 * hp(rng.standard_normal(cn), 2500) * np.exp(-ct / 0.0025) \
      + 0.6 * np.sin(2 * np.pi * 1800 * ct) * np.exp(-ct / 0.004) \
      + 0.5 * np.sin(2 * np.pi * 160 * ct) * np.exp(-ct / 0.012)
add(norm(click), 9.0, pan=0.0, gain=0.55)

# ---------------- master ----------------
out = np.stack([L, R], 1)
out = sosfilt(butter(2, 28 / (SR / 2), btype='high', output='sos'), out, axis=0)
out *= (np.minimum(1, T / 0.005) * np.clip((10.0 - T) / 0.3, 0, 1))[:, None]
out = out / np.max(np.abs(out)) * 0.7
wavfile.write(sys.argv[1] if len(sys.argv) > 1 else 'sound.wav', SR, (out * 32767).astype(np.int16))
print('ok')
