#!/usr/bin/env python3
"""Normalize the test photos to plain sRGB with no colour profile (11 Nov 2026).

Why: cjpeg (reading PPM) and cwebp drop the PNG's ICC profile, while the HEIC/AVIF/JPEG XL tools keep it.
One source (plant-0, Adobe RGB 1998) was therefore scored with the wrong colours for JPEG and WebP.
Fix: convert any non-sRGB photo to sRGB pixels with macOS sips, then strip colour chunks from every PNG,
so every encoder sees identical sRGB pixels and ssimulacra2 interprets them the same way.
The originals with profiles are kept in veri/foto-icc/."""
import shutil, struct, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
FOTO = HERE / "veri/foto"; KEEP = HERE / "veri/foto-icc"; KEEP.mkdir(exist_ok=True)
SRGB = "/System/Library/ColorSync/Profiles/sRGB Profile.icc"
DROP = {b"iCCP", b"gAMA", b"cHRM", b"sRGB"}


def chunks(data):
    i = 8
    while i < len(data):
        n = struct.unpack(">I", data[i:i + 4])[0]
        yield data[i + 4:i + 8], data[i:i + 12 + n]
        i += 12 + n


def icc_name(data):
    for t, c in chunks(data):
        if t == b"iCCP":
            return c[8:88].split(b"\0")[0].decode(errors="replace")
    return None


for p in sorted(FOTO.glob("*.png")):
    data = p.read_bytes()
    if icc_name(data) is None:
        print(p.name, "no profile"); continue
    if not (KEEP / p.name).exists():
        shutil.copy2(p, KEEP / p.name)
    desc = subprocess.run(["sips", "-g", "profile", str(KEEP / p.name)], capture_output=True, text=True).stdout
    if "sRGB" not in desc:
        tmp = p.with_suffix(".srgb.png")
        subprocess.run(["sips", "-m", SRGB, str(KEEP / p.name), "--out", str(tmp)], check=True, capture_output=True)
        # sips may write 16-bit or add alpha; normalise to 8-bit rgb24 with ffmpeg
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-pix_fmt", "rgb24", str(p)], check=True)
        tmp.unlink(); data = p.read_bytes()
        print(p.name, "converted to sRGB from:", desc.strip().splitlines()[-1].strip())
    out = data[:8] + b"".join(c for t, c in chunks(data) if t not in DROP)
    p.write_bytes(out)
    print(p.name, "profile chunks stripped")
