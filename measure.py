#!/usr/bin/env python3
"""V13 measurement: every common image format on the same photos (11 Nov 2026).

Data (veri/): foto/*.png = 11 NASA public-domain photos, downscaled from the originals to 1600 px (lossless PNG);
ekran/*.png = 3 screenshots of our own video frames; orijinal/*.jpg = the NASA original JPEGs.
Quality is measured with SSIMULACRA2 (libjxl): 80 = "impossible to distinguish from the original in a side-by-side
comparison at 1:1". Every encode is decoded again and scored against the original PNG.

Parts:
  same_quality : for JPEG, WebP, HEIC, AVIF, JPEG XL, the smallest file that still scores >= 80 (bisection on quality)
  lossless     : BMP, PNG, WebP lossless, AVIF lossless, JPEG XL lossless, on photos and screenshots
  gif          : GIF (256 colours) on the hero photo: size and score
  same_size    : the hero photo squeezed into the same small budget in every format (for the side-by-side picture)
  resave       : JPEG saved 100 times (same settings / quality changing a little each time), WebP 100 times
  transcode    : JPEG -> JPEG XL lossless recompression of the original JPEGs, size and byte-exact round trip
  cross        : the same_size pictures scored again with two older measures (SSIM and PSNR, ffmpeg), because
                 SSIMULACRA2 was written by one of the JPEG XL authors
Usage: python3 olcum.py [parts...]   → sonuc/olcum.json (merged), sonuc/gorsel/*.png for the video

Before measuring, run srgb_yap.py: cjpeg (from PPM) and cwebp drop a PNG's colour profile while the other tools keep it,
so every source must be plain sRGB without a profile (one NASA photo was Adobe RGB; found 11 Nov 2026).
"""
import hashlib, json, shutil, statistics, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "veri"
OUT = HERE / "sonuc"; OUT.mkdir(exist_ok=True)
VIS = OUT / "gorsel"; VIS.mkdir(exist_ok=True)
B = "/opt/homebrew/bin/"
JT = "/opt/homebrew/opt/jpeg-turbo/bin/"
TARGET = 80.0
HERO = "astronaut-2-S84-40242"
WORK = Path(tempfile.mkdtemp(prefix="v13-"))


def run(*a):
    r = subprocess.run([str(x) for x in a], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(map(str, a))}: {r.stderr[:300]}")
    return r.stdout


def timed(*a):
    t = time.perf_counter(); run(*a); return time.perf_counter() - t


def score(orig: Path, dec: Path) -> float:
    return float(run(B + "ssimulacra2", orig, dec).strip().split()[-1])


def ppm(src: Path) -> Path:
    p = WORK / (src.stem + ".ppm")
    if not p.exists():
        run("ffmpeg", "-loglevel", "error", "-y", "-i", src, "-pix_fmt", "rgb24", p)
    return p


# name -> (encode(src_png, q, out) argv, decode(enc, out_png) argv, ext, q range)
LOSSY = {
    "JPEG":    (lambda s, q, o: [JT + "cjpeg", "-quality", str(round(q)), "-outfile", o, ppm(s)],
                lambda e, o: ["sh", "-c", f"'{JT}djpeg' -outfile '{o}.ppm' '{e}' && ffmpeg -loglevel error -y -i '{o}.ppm' '{o}'"], "jpg", (5, 100)),
    "WebP":    (lambda s, q, o: [B + "cwebp", "-quiet", "-q", f"{q:.0f}", s, "-o", o], lambda e, o: [B + "dwebp", "-quiet", e, "-o", o], "webp", (0, 100)),
    "HEIC":    (lambda s, q, o: [B + "heif-enc", "-q", f"{q:.0f}", s, "-o", o], lambda e, o: [B + "heif-dec", e, o], "heic", (0, 100)),
    "AVIF":    (lambda s, q, o: [B + "avifenc", "-q", f"{q:.0f}", s, o], lambda e, o: [B + "avifdec", e, o], "avif", (0, 99)),
    "JPEG XL": (lambda s, q, o: [B + "cjxl", "--quiet", s, o, "-q", f"{q:.1f}"], lambda e, o: [B + "djxl", "--quiet", e, o], "jxl", (1, 99)),
}


def encode_score(fmt, src, q, tag="x"):
    enc_f, dec_f, ext, _ = LOSSY[fmt]
    enc = WORK / f"{src.stem}-{fmt.replace(' ', '')}-{tag}.{ext}"
    dec = WORK / f"{src.stem}-{fmt.replace(' ', '')}-{tag}.png"
    t = timed(*enc_f(src, q, enc))
    run(*dec_f(enc, dec))
    return enc.stat().st_size, score(src, dec), t, enc, dec


def smallest_at(fmt, src, target=TARGET):
    lo, hi = LOSSY[fmt][3]
    best = None
    for _ in range(8):
        q = (lo + hi) / 2
        size, sc, t, enc, dec = encode_score(fmt, src, q)
        if sc >= target:
            best = (q, size, sc, t); hi = q
        else:
            lo = q
    if best is None:
        size, sc, t, enc, dec = encode_score(fmt, src, LOSSY[fmt][3][1])
        best = (LOSSY[fmt][3][1], size, sc, t)
    return best


def part_same_quality():
    rows = {}
    for src in sorted((DATA / "foto").glob("*.png")):
        rows[src.stem] = {}
        for fmt in LOSSY:
            q, size, sc, t = smallest_at(fmt, src)
            rows[src.stem][fmt] = {"q": round(q, 2), "size": size, "score": round(sc, 2), "enc_s": round(t, 3)}
            print(f"  {src.stem[:28]:28} {fmt:8} q={q:6.2f} {size:9d} B  score {sc:5.1f}  {t:.2f} s", flush=True)
    summ = {}
    for fmt in LOSSY:
        rel = [rows[k][fmt]["size"] / rows[k]["JPEG"]["size"] for k in rows]
        summ[fmt] = {"median_vs_jpeg": round(statistics.median(rel), 4), "total": sum(rows[k][fmt]["size"] for k in rows),
                     "median_enc_s": round(statistics.median(rows[k][fmt]["enc_s"] for k in rows), 3)}
    return {"target": TARGET, "rows": rows, "summary": summ}


def part_lossless():
    out = {}
    for group in ("foto", "ekran"):
        tot = {"original_raw": 0}
        for src in sorted((DATA / group).glob("*.png")):
            w, h = map(int, run("ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", src).strip().split(","))
            tot["original_raw"] += w * h * 3
            cands = {
                "BMP": (["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-pix_fmt", "bgr24", WORK / "l.bmp"], WORK / "l.bmp"),
                "PNG": (["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-pix_fmt", "rgb24", "-compression_level", "9", "-pred", "mixed", WORK / "l.png"], WORK / "l.png"),
                "WebP": ([B + "cwebp", "-quiet", "-lossless", "-m", "6", src, "-o", WORK / "l.webp"], WORK / "l.webp"),
                "AVIF": ([B + "avifenc", "-l", src, WORK / "l.avif"], WORK / "l.avif"),
                "JPEG XL": ([B + "cjxl", "--quiet", src, WORK / "l.jxl", "-d", "0"], WORK / "l.jxl"),
            }
            for k, (argv, f) in cands.items():
                run(*argv)
                tot[k] = tot.get(k, 0) + f.stat().st_size
        out[group] = tot
        print(f"  lossless {group}: " + ", ".join(f"{k} {v}" for k, v in tot.items()), flush=True)
    return out


def part_gif():
    src = DATA / "foto" / f"{HERO}.png"
    g = WORK / "hero.gif"; back = VIS / "gif-hero.png"
    run("ffmpeg", "-loglevel", "error", "-y", "-i", src, "-vf", "split[a][b];[a]palettegen=max_colors=256[p];[b][p]paletteuse", g)
    run("ffmpeg", "-loglevel", "error", "-y", "-i", g, "-frames:v", "1", "-update", "1", "-pix_fmt", "rgb24", back)
    return {"size": g.stat().st_size, "score": round(score(src, back), 2), "png_size": src.stat().st_size}


def part_same_size(jpeg_q=25):
    src = DATA / "foto" / f"{HERO}.png"
    budget, _, _, _, _ = encode_score("JPEG", src, jpeg_q, tag="budget")   # the budget = what JPEG needs at quality 25
    res = {"budget": budget, "jpeg_q": jpeg_q}
    for fmt in LOSSY:
        lo, hi = LOSSY[fmt][3]
        best = None
        for _ in range(9):
            q = (lo + hi) / 2
            size, sc, t, enc, dec = encode_score(fmt, src, q, tag="b")
            if size <= budget:
                best = (q, size, sc); shutil.copy(dec, VIS / f"same-size-{fmt.replace(' ', '')}.png"); lo = q
            else:
                hi = q
        if best:
            res[fmt] = {"q": round(best[0], 2), "size": best[1], "score": round(best[2], 2)}
            print(f"  same size {fmt:8} q={best[0]:6.2f} {best[1]} B score {best[2]:.1f}", flush=True)
        else:
            res[fmt] = None
            print(f"  same size {fmt:8} cannot reach {budget} B", flush=True)
    shutil.copy(src, VIS / "original-hero.png")
    return res


def part_resave(n=100):
    src = DATA / "foto" / f"{HERO}.png"
    res = {}
    checkpoints = {1, 2, 5, 10, 25, 50, 100}
    for variant in ("jpeg-same", "jpeg-varying", "webp-same"):
        cur = WORK / "cur.ppm"
        run("ffmpeg", "-loglevel", "error", "-y", "-i", src, "-pix_fmt", "rgb24", cur)
        scores = {}
        for i in range(1, n + 1):
            if variant.startswith("jpeg"):
                q = 80 if variant == "jpeg-same" else 75 + (i * 7) % 11   # 75..85, a different app each time
                run(JT + "cjpeg", "-quality", str(q), "-outfile", WORK / "r.jpg", cur)
                run(JT + "djpeg", "-outfile", cur, WORK / "r.jpg")
            else:
                run(B + "cwebp", "-quiet", "-q", "80", cur, "-o", WORK / "r.webp")
                run(B + "dwebp", "-quiet", "-ppm", WORK / "r.webp", "-o", cur)
            if i in checkpoints:
                p = WORK / "r.png"
                run("ffmpeg", "-loglevel", "error", "-y", "-i", cur, p)
                scores[i] = round(score(src, p), 2)
                if i in (1, 100):
                    shutil.copy(p, VIS / f"resave-{variant}-{i}.png")
        res[variant] = scores
        print(f"  resave {variant}: {scores}", flush=True)
    return res


def part_transcode():
    rows = []
    for jpg in sorted((DATA / "orijinal").glob("*.jpg")):
        jxl = WORK / (jpg.stem + ".jxl"); back = WORK / (jpg.stem + "-back.jpg")
        run(B + "cjxl", "--quiet", jpg, jxl)
        run(B + "djxl", "--quiet", jxl, back)
        same = hashlib.sha256(jpg.read_bytes()).hexdigest() == hashlib.sha256(back.read_bytes()).hexdigest()
        rows.append({"name": jpg.stem, "jpeg": jpg.stat().st_size, "jxl": jxl.stat().st_size, "byte_exact": same})
        print(f"  transcode {jpg.stem[:30]:30} {jpg.stat().st_size:9d} -> {jxl.stat().st_size:9d}  exact={same}", flush=True)
    tot_j = sum(r["jpeg"] for r in rows); tot_x = sum(r["jxl"] for r in rows)
    return {"rows": rows, "total_jpeg": tot_j, "total_jxl": tot_x, "saving": round(1 - tot_x / tot_j, 4), "all_exact": all(r["byte_exact"] for r in rows)}


def part_cross():
    """SSIM (higher is better, 1 = identical) and PSNR in dB (higher is better) of the same_size pictures."""
    import re
    orig = VIS / "original-hero.png"
    res = {}
    for fmt in LOSSY:
        img = VIS / f"same-size-{fmt.replace(' ', '')}.png"
        out = {}
        for name, pat in (("ssim", r"All:([0-9.]+)"), ("psnr", r"average:([0-9.]+)")):
            log = subprocess.run(["ffmpeg", "-hide_banner", "-i", img, "-i", orig, "-lavfi", name, "-f", "null", "-"],
                                 capture_output=True, text=True).stderr
            out[name] = round(float(re.findall(pat, log)[-1]), 4)
        res[fmt] = out
        print(f"  cross {fmt:8} SSIM {out['ssim']:.4f} PSNR {out['psnr']:.2f}", flush=True)
    return res


if __name__ == "__main__":
    parts = sys.argv[1:] or ["transcode", "gif", "same_size", "cross", "lossless", "resave", "same_quality"]
    path = OUT / "olcum.json"
    res = json.loads(path.read_text()) if path.exists() else {}
    res["tools"] = {"cjpeg": run(JT + "cjpeg", "-version").strip() if False else "libjpeg-turbo 3.2.1", "cwebp": run(B + "cwebp", "-version").strip(),
                    "avifenc": "libavif 1.4.2 (aom 3.15.3)", "heif-enc": "libheif 1.23.7 (x265)", "cjxl": "libjxl 0.12.0", "date": time.strftime("%Y-%m-%d %H:%M")}
    for p in parts:
        print(f"== {p}", flush=True)
        res[p] = globals()[f"part_{p}"]()
        path.write_text(json.dumps(res, indent=1))
    shutil.rmtree(WORK)
    print("->", path)
