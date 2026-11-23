"""Synthesise an original drift-phonk bed (808 slides, cowbell riff, trap hats, clap, dark pad).

    uv run --no-project --python 3.12 --with numpy --with scipy --with soundfile \
        python -I make_beat.py <out.wav> [--bpm 140] [--bars 40] [--key F] [--seed 7]

Everything is generated from oscillators and noise here: no samples, no model, so the track is
the person's own work. Writes <out>.wav (48 kHz stereo 24-bit), <out>.beats.json (exact beat
times, so cut.py snaps to the true grid) and prints the section map:
  bars 0-3 intro (filtered pad + cowbell, light hats)  ·  bar 4 drop
  2-bar breakdown at the middle  ·  last 2 bars outro
"""
import argparse, json, os
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt

SR = 48000
NOTE = {"C": 0, "Db": 1, "D": 2, "Eb": 3, "E": 4, "F": 5, "Gb": 6, "G": 7, "Ab": 8, "A": 9, "Bb": 10, "B": 11}

def hz(semis_from_a4):
    return 440.0 * 2 ** (semis_from_a4 / 12)

def midi_hz(m):
    return hz(m - 69)

def filt(x, kind, f, order=2):
    f = [x / (SR / 2) for x in f] if kind == "band" else f / (SR / 2)
    sos = butter(order, f, btype={"low": "lowpass", "high": "highpass", "band": "bandpass"}[kind], output="sos")
    return sosfilt(sos, x)

def env(n, a, d, sus=0.0):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * (sus + (1 - sus) * np.exp(-t / d))
    return e

def kick(rng):
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 45 + 140 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / 0.22)
    click = filt(rng.standard_normal(n), "high", 3000) * np.exp(-t / 0.004) * 0.5
    return np.tanh(2.2 * (body + click))

def clap(rng):
    n = int(0.32 * SR); t = np.arange(n) / SR
    noise = filt(rng.standard_normal(n), "band", [900, 5500])
    e = np.zeros(n)
    for off in (0, 0.010, 0.021):  # three hand hits then the tail
        k = int(off * SR); e[k:] += np.exp(-(t[: n - k]) / 0.008) * 0.7
    e += np.exp(-np.maximum(t - 0.021, 0) / 0.11) * (t >= 0.021)
    snap = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.03) * 0.4
    return np.tanh(1.6 * (noise * e + snap))

def hat(rng, open_=False):
    n = int((0.22 if open_ else 0.05) * SR); t = np.arange(n) / SR
    x = filt(rng.standard_normal(n), "high", 7500)
    return x * np.exp(-t / (0.07 if open_ else 0.012)) * 0.55

def cowbell(freq, length=0.22):
    """The 808 cowbell: two detuned squares through a bandpass, short decay; pitched for a riff."""
    n = int(length * SR); t = np.arange(n) / SR
    sq = np.sign(np.sin(2 * np.pi * freq * t)) + np.sign(np.sin(2 * np.pi * freq * 1.48 * t))
    x = filt(sq, "band", [freq * 0.9, min(freq * 3.2, 20000)])
    e = np.exp(-t / 0.06) * 0.7 + np.exp(-t / 0.22) * 0.3
    return x * e * 0.35

def bass808(f0, f1, length, glide=0.06):
    n = int(length * SR); t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / glide) if f0 != f1 else np.full(n, f0)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + 0.25 * np.sin(2 * ph)
    e = np.minimum(1, t / 0.004) * np.exp(-t / max(length * 0.9, 0.2))
    rel = np.minimum(1, (length - t) / 0.03)
    return np.tanh(2.6 * x) * e * rel * 0.8

def pad(freqs, length, rng):
    n = int(length * SR); t = np.arange(n) / SR
    x = np.zeros((2, n))
    for f in freqs:
        for ch, det in enumerate((-0.12, 0.12)):
            for d2 in (-0.07, 0.0, 0.07):
                ff = f * 2 ** ((det + d2) / 12)
                saw = 2 * ((t * ff + rng.random()) % 1) - 1
                x[ch] += saw
    x = np.stack([filt(c, "low", 1400) for c in x])
    e = np.minimum(1, t / 0.25) * np.minimum(1, (length - t) / 0.3)
    return x * e / (len(freqs) * 3) * 0.5

def place(buf, x, at, gain=1.0, pan=0.0):
    i = int(round(at * SR))
    if i >= buf.shape[1]:
        return
    x = np.atleast_2d(x)
    if x.shape[0] == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        x = np.vstack([x[0] * l * 1.414, x[0] * r * 1.414])
    n = min(x.shape[1], buf.shape[1] - i)
    buf[:, i:i + n] += x[:, :n] * gain

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--bpm", type=float, default=140); ap.add_argument("--bars", type=int, default=40)
    ap.add_argument("--key", default="F"); ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    beat = 60 / a.bpm; step = beat / 4; bar = beat * 4
    total = a.bars * bar + 1.0
    drums, bass, bells, pads = (np.zeros((2, int(total * SR))) for _ in range(4))
    root = 29 + NOTE[a.key]  # F1 = midi 29 for key F: the 808's register
    # i - VI - VII - i in natural minor, two bars each (Fm Db Eb Fm in F)
    prog = [0, -4, -2, 0]
    minor = [0, 2, 3, 5, 7, 8, 10]
    # cowbell riff: (16th step, scale degree, octave) over two bars; syncopated, phonk-style
    riff = [(0, 0, 0), (3, 0, 0), (6, 2, 0), (8, 4, 0), (11, 3, 0), (14, 2, 0),
            (16, 0, 0), (19, 0, 0), (22, 2, 0), (24, 4, 0), (26, 5, 0), (28, 4, 0), (30, 3, 0)]
    K, C, H, HO = kick(rng), clap(rng), hat(rng), hat(rng, True)
    mid = a.bars // 2
    intro, brk, outro = range(0, 4), range(mid, mid + 2), range(a.bars - 2, a.bars)
    for b in range(a.bars):
        t0 = b * bar
        chord_root = root + prog[(b // 2) % 4]
        full = b not in intro and b not in brk
        # drums
        if full:
            for s in (0, 10) + ((7,) if b % 2 else (14,)):
                place(drums, K, t0 + s * step, 0.9)
            for s in (4, 12):
                place(drums, C, t0 + s * step, 0.55)
        if b not in brk:
            roll = b % 4 == 3 and full
            for s in range(0, 16, 2 if b in intro else 1):
                if roll and s >= 12:
                    for k in range(3):  # 1/16-triplet roll into the next bar
                        place(drums, H, t0 + (s + k / 3) * step, 0.35 + 0.1 * k, pan=0.25)
                    continue
                g = 0.42 if s % 4 == 2 else (0.3 if s % 2 == 0 else 0.22)
                place(drums, H, t0 + s * step, g * (0.6 if b in intro else 1.0), pan=0.25)
            if full:
                place(drums, HO, t0 + 14 * step, 0.25, pan=-0.2)
        # 808: on the kicks, slides up from the root into the 7th on the bar's last hit
        if full:
            hits = (0, 10) + ((7,) if b % 2 else (14,))
            hits = sorted(hits)
            for j, s in enumerate(hits):
                nxt = hits[j + 1] if j + 1 < len(hits) else 16
                f = midi_hz(chord_root)
                f_from = midi_hz(chord_root + 12) if (s == hits[-1] and b % 2) else f
                place(bass, bass808(f_from, f, (nxt - s) * step), t0 + s * step, 1.0)
        # cowbell riff (every bar pair), filtered in the intro and the breakdown
        if b % 2 == 0 and b not in outro:
            for s, deg, octv in riff:
                m = root + 36 + prog[(b // 2) % 4] * 0 + minor[deg % 7] + 12 * octv  # riff stays in key
                place(bells, cowbell(midi_hz(m)), t0 + s * step, 1.0, pan=(-0.3 if s % 2 else 0.3))
        # pad: the chord, two bars at a time
        if b % 2 == 0:
            m = chord_root + 24
            third = 3 if prog[(b // 2) % 4] == 0 else 4
            place(pads, pad([midi_hz(m), midi_hz(m + third), midi_hz(m + 7)], 2 * bar, rng), t0, 1.0)
    # sidechain pump on the pad and bells from the kick pattern
    t = np.arange(drums.shape[1]) / SR
    pump = np.ones_like(t)
    for b in range(a.bars):
        if b in intro or b in brk:
            continue
        for s in (0, 10) + ((7,) if b % 2 else (14,)):
            k0 = b * bar + s * step
            m = (t >= k0) & (t < k0 + 0.25)
            pump[m] = np.minimum(pump[m], 0.35 + 0.65 * ((t[m] - k0) / 0.25) ** 0.6)
    pads *= pump; bells *= 0.6 + 0.4 * pump
    # intro + breakdown: low-pass the music so the drop opens up
    def lp_sections(x, cut):
        y = x.copy()
        for rgn in (intro, brk):
            i0, i1 = int(rgn.start * bar * SR), int(rgn.stop * bar * SR)
            y[:, i0:i1] = np.stack([filt(c[i0:i1], "low", cut) for c in x])
        return y
    bells = lp_sections(bells, 1500); pads = lp_sections(pads, 700)
    # lo-fi: light bit-crush on the bells, vinyl crackle under everything
    bells = np.round(bells * 96) / 96
    crackle = np.zeros_like(drums)
    pops = rng.random(drums.shape[1]) < 18 / SR
    crackle[:, pops] = rng.standard_normal((2, pops.sum())) * 0.25
    crackle = np.stack([filt(c, "band", [1500, 9000]) for c in crackle]) + 0.004 * filt(rng.standard_normal(drums.shape), "high", 2000)
    mix = drums * 1.0 + bass * 0.95 + bells * 0.8 + pads * 0.55 + crackle
    mix = np.stack([filt(c, "high", 28) for c in mix])
    mix = np.tanh(1.3 * mix) / np.tanh(1.3)  # tape-ish glue
    mix *= 0.89 / np.max(np.abs(mix))         # about -1 dBFS peak
    fade = int(0.9 * SR); mix[:, -fade:] *= np.linspace(1, 0, fade)
    sf.write(a.out, mix.T, SR, subtype="PCM_24")
    beats = [round(i * beat, 5) for i in range(a.bars * 4)]
    json.dump(beats, open(os.path.splitext(a.out)[0] + ".beats.json", "w"))
    print(f"{a.out}: {a.bpm} BPM, {a.bars} bars, {total:.1f}s, key {a.key} minor")
    print(f"intro bars 0-3 (beats 0-15), drop at beat 16 ({16 * beat:.2f}s); breakdown bars {mid}-{mid + 1} "
          f"(beats {mid * 4}-{mid * 4 + 7}, {mid * bar:.2f}-{(mid + 2) * bar:.2f}s); outro bars {a.bars - 2}-{a.bars - 1}")

main()
