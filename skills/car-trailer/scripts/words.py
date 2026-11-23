"""Word-level timestamps for short windows of the export, in source seconds.

    uv run --no-project --python 3.12 --with mlx-whisper python -I words.py <export> <start:dur> [<start:dur> ...]

Set HF_HOME to a folder that already holds mlx-community/whisper-large-v3-turbo (and
HF_HUB_OFFLINE=1) to skip the download. Needs ffmpeg on PATH or FFMPEG set.
Prints one line per segment: word@start-end ...
"""
import os, subprocess, sys, tempfile
import mlx_whisper

ff = os.environ.get("FFMPEG", "ffmpeg")
src = sys.argv[1]
with tempfile.TemporaryDirectory() as tmp:
    for win in sys.argv[2:]:
        a, d = (float(x) for x in win.split(":"))
        wav = os.path.join(tmp, "w.wav")
        subprocess.run([ff, "-loglevel", "error", "-y", "-ss", str(a), "-t", str(d), "-i", src, "-map", "0:a:0",
                        "-ac", "1", "-ar", "16000", wav], check=True)
        r = mlx_whisper.transcribe(wav, path_or_hf_repo="mlx-community/whisper-large-v3-turbo", word_timestamps=True)
        print(f"== {a:.2f}+{d:.2f}")
        for s in r["segments"]:
            print(" ".join(f"{w['word'].strip()}@{a + w['start']:.2f}-{a + w['end']:.2f}" for w in s["words"]))
