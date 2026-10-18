"""Synthesises the drum samples (no downloads needed). Run: python generate_sounds.py"""
import wave
import numpy as np
from config import SOUND_DIR

SR = 44100


def _t(sec):
    return np.linspace(0, sec, int(SR * sec), endpoint=False)


def _highpass(x):
    return np.diff(x, prepend=0)


def _tom(sec, f_hi, f_lo, decay):
    t = _t(sec)
    f = f_lo + (f_hi - f_lo) * np.exp(-t * 14)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * decay)


def _metal(t, freqs, decay):
    return sum(np.sin(2 * np.pi * f * t) for f in freqs) * np.exp(-t * decay)


def _kick(sec=0.45):
    t = _t(sec)
    f = 145 * np.exp(-t * 18) + 48
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 8)


def _save(name, x):
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.9
    SOUND_DIR.mkdir(parents=True, exist_ok=True)
    with wave.open(str(SOUND_DIR / name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def generate():
    rng = np.random.default_rng(7)
    _save("kick.wav", _kick())
    t = _t(0.30)
    _save("snare.wav", rng.standard_normal(len(t)) * np.exp(-t * 22) * 0.7
          + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 28) * 0.6)
    t = _t(0.14)
    _save("hihat.wav", _highpass(rng.standard_normal(len(t))) * np.exp(-t * 45))
    _save("tom_hi.wav", _tom(0.35, 330, 210, 9))
    _save("tom_mid.wav", _tom(0.40, 250, 150, 8))
    _save("floor_tom.wav", _tom(0.55, 150, 82, 6))
    t = _t(1.4)
    _save("crash.wav", _highpass(rng.standard_normal(len(t))) * np.exp(-t * 3.2))
    t = _t(1.1)
    _save("ride.wav", _metal(t, [3100, 4300, 5700, 7300], 5) * 0.5
          + _highpass(rng.standard_normal(len(t))) * np.exp(-t * 9) * 0.35)
    t = _t(0.30)
    _save("cowbell.wav", (np.sign(np.sin(2 * np.pi * 562 * t)) + np.sign(np.sin(2 * np.pi * 845 * t)))
          * np.exp(-t * 14))


if __name__ == "__main__":
    generate()
    print("Wrote drum samples to", SOUND_DIR)
