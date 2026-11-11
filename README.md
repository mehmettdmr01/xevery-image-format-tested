# Every image format, tested on the same photos

Measurements behind the video **"Every Image Format, Tested on the Same Photos"** (Twelve Reasons).
Video: (link coming)

JPEG, WebP, HEIC, AVIF and JPEG XL compared **at the same visual quality**: for every format and every photo, the
smallest file that still scores at least 80 on [SSIMULACRA 2](https://github.com/cloudinary/ssimulacra2)
("impossible to distinguish from the original in a side-by-side comparison at 1:1"), found by bisection on the
quality setting. Every file is decoded again and scored against the original. Also: lossless (BMP, PNG, WebP, AVIF,
JPEG XL), GIF, the same photo squeezed into the same small size, saving a JPEG or WebP 100 times, and JPEG → JPEG XL
lossless recompression.

**Caveat:** SSIMULACRA 2 was written by Jon Sneyers, one of the JPEG XL authors. The same-size test is therefore also
scored with SSIM and PSNR (ffmpeg); in all three, JPEG comes last.

## Run it yourself

```
brew install jpeg-turbo webp libheif libavif jpeg-xl ffmpeg   # ssimulacra2 comes with jpeg-xl's tools or build it from libjxl
python3 srgb.py      # convert every photo to plain sRGB without a colour profile (see below)
python3 measure.py   # → sonuc/olcum.json and sonuc/gorsel/*.png
```

Folders (the script was written in Turkish first): `veri/foto/` = test photos as PNG (longest side 1600 px),
`veri/ekran/` = screenshots, `veri/orijinal/` = the original NASA JPEGs, `sonuc/` = results. In `results.json`,
`foto` = photos and `ekran` = screenshots.

Encoders: libjpeg-turbo 3.2.1 (`cjpeg`), libwebp 1.6.0, libheif 1.23.7 with x265, libavif 1.4.2 with aom 3.15.3,
libjxl 0.12.0. Default speed/effort settings; only the quality setting is searched. Apple M1, 11 November 2026.

**Colour profiles matter.** `cjpeg` (reading PPM) and `cwebp` drop a PNG's ICC profile; `heif-enc`, `avifenc` and
`cjxl` keep it. One NASA photo was Adobe RGB, so JPEG and WebP were first scored with the wrong colours on it. `srgb.py`
converts every source to sRGB pixels and strips the profile before measuring.

Photos (NASA, public domain; https://images.nasa.gov/details/ + ID): s64-31845, s90-38573, S84-40242, KSC-20251111-PH-JBS01_0011, sl4-143-4707, iss045e013851, as11-37-5545, PIA03606, GSFC_20171208_Archive_e002076, KSC-20180307-PH_CSH01_0015, KSC-20240525-PH-RKL01_0006.

## Results

### Same quality (SSIMULACRA 2 ≥ 80): file size in bytes, and compared with the JPEG of the same photo

| Photo | JPEG | WebP | HEIC | AVIF | JPEG XL |
|---|---:|---:|---:|---:|---:|
| astronaut-0-s64-31845 | 258,363 (100%) | 280,480 (109%) | 225,538 (87%) | 178,029 (69%) | 133,411 (52%) |
| astronaut-1-s90-38573 | 367,518 (100%) | 326,958 (89%) | 222,803 (61%) | 180,241 (49%) | 163,167 (44%) |
| astronaut-2-S84-40242 | 363,562 (100%) | 336,058 (92%) | 297,598 (82%) | 247,744 (68%) | 251,332 (69%) |
| aurora-0-KSC-20251111-PH-JBS01_0011 | 412,414 (100%) | 396,644 (96%) | 386,963 (94%) | 323,077 (78%) | 293,088 (71%) |
| earth-0-sl4-143-4707 | 579,299 (100%) | 540,480 (93%) | 462,844 (80%) | 390,557 (67%) | 354,089 (61%) |
| earth-2-iss045e013851 | 319,974 (100%) | 303,654 (95%) | 237,601 (74%) | 183,494 (57%) | 195,133 (61%) |
| moon-0-as11-37-5545 | 276,776 (100%) | 252,678 (91%) | 191,713 (69%) | 196,339 (71%) | 162,341 (59%) |
| nebula-0-PIA03606 | 640,739 (100%) | 524,472 (82%) | 466,639 (73%) | 442,483 (69%) | 445,366 (70%) |
| nebula-1-GSFC_20171208_Archive_e002076 | 341,532 (100%) | 381,872 (112%) | 252,450 (74%) | 240,158 (70%) | 180,530 (53%) |
| plant-0-KSC-20180307-PH_CSH01_0015 | 467,420 (100%) | 438,228 (94%) | 194,192 (42%) | 146,080 (31%) | 158,329 (34%) |
| rocket-0-KSC-20240525-PH-RKL01_0006 | 281,843 (100%) | 366,706 (130%) | 202,064 (72%) | 187,316 (66%) | 166,727 (59%) |
| **median, compared with JPEG** | **100.0%** | **93.8%** | **73.9%** | **68.1%** | **59.2%** |

### The same photo in the same space (JPEG at quality 25 = 94,494 bytes; every other format as close as it gets without going over)

| Format | Size (bytes) | SSIMULACRA 2 | SSIM | PSNR |
|---|---:|---:|---:|---:|
| AVIF | 88,243 | 67.7 | 0.9017 | 35.26 dB |
| HEIC | 90,213 | 67.7 | 0.9007 | 35.05 dB |
| JPEG XL | 94,389 | 66.2 | 0.8904 | 34.37 dB |
| WebP | 94,344 | 61.4 | 0.8867 | 34.44 dB |
| JPEG | 94,494 | 40.8 | 0.8559 | 32.36 dB |

### Lossless

| Format | 11 photos (bytes) | 3 screenshots (bytes) |
|---|---:|---:|
| BMP | 67,008,594 | 18,662,562 |
| PNG | 34,664,311 | 399,016 |
| WebP | 26,186,378 | 183,960 |
| AVIF | 32,339,590 | 595,928 |
| JPEG XL | 24,412,794 | 202,206 |

Raw pixels: 66,998,400 bytes (photos), 18,662,400 bytes (screenshots).

### GIF (astronaut photo)

GIF: 1,283,195 bytes, SSIMULACRA 2 score 72.0. PNG of the same photo: 3,727,478 bytes.

### Saving again and again (astronaut photo, SSIMULACRA 2 score after N saves)

| Saves | 1 | 2 | 5 | 10 | 25 | 50 | 100 |
|---|---:|---:|---:|---:|---:|---:|---:|
| JPEG, same setting (quality 80) | 77.1 | 76.7 | 75.6 | 74.8 | 74.0 | 74.0 | 74.0 |
| JPEG, quality 75-85 changing every save | 78.1 | 74.5 | 65.4 | 56.8 | 44.1 | 38.6 | 34.1 |
| WebP, same setting (quality 80) | 71.5 | 64.1 | 52.9 | 43.1 | 25.9 | 17.6 | 16.9 |

### JPEG → JPEG XL, lossless

11 original NASA JPEGs, 81,675,958 bytes → 60,655,965 bytes as JPEG XL
(25.7% smaller). Converted back with `djxl`: 11 of 11 files byte-for-byte identical to the original (sha256).
