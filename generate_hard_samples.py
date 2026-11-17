"""Buat versi 'sulit' dari invoice dummy: dimiringkan, diburamkan, diberi noise,
bayangan, dan kompresi JPEG. Ground truth tetap sama karena isi dokumennya sama.

Pemakaian:
    python generate_hard_samples.py
Hasil:
    data/hard_samples/hard_invoice_XXX.jpg
    data/ground_truth_hard.csv  (ada kolom tambahan: difficulty)
"""
import csv
import io
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageOps

SRC_DIR = Path("data/samples")
OUT_DIR = Path("data/hard_samples")
GT_IN = Path("data/ground_truth.csv")
GT_OUT = Path("data/ground_truth_hard.csv")

# Tiga tingkat kesulitan. Setiap rentang (min, max) diundi per dokumen.
LEVELS = {
    "ringan": dict(dpi=150, angle=(1.0, 2.5), blur=(0.3, 0.6), noise=(6, 10),
                   shadow=(0.05, 0.12), quality=(70, 85)),
    "sedang": dict(dpi=120, angle=(3.0, 6.0), blur=(0.6, 1.0), noise=(10, 15),
                   shadow=(0.12, 0.22), quality=(45, 60)),
    "berat": dict(dpi=100, angle=(6.0, 10.0), blur=(1.0, 1.5), noise=(16, 22),
                  shadow=(0.20, 0.35), quality=(25, 38)),
}


def render_pdf(path: Path, dpi: int) -> Image.Image:
    """Ubah halaman pertama PDF menjadi gambar RGB."""
    import fitz  # PyMuPDF

    with fitz.open(str(path)) as doc:
        pix = doc[0].get_pixmap(dpi=dpi)
        png_bytes = pix.tobytes("png")
    return Image.open(io.BytesIO(png_bytes)).convert("RGB")


def add_shadow(img: Image.Image, strength: float, rng: random.Random) -> Image.Image:
    """Bayangan gradasi seperti foto dengan pencahayaan tidak merata."""
    grad = Image.linear_gradient("L").resize(img.size)
    grad = grad.point(lambda p: int(255 * (1 - strength * (1 - p / 255))))
    if rng.random() < 0.5:
        grad = ImageOps.flip(grad)
    if rng.random() < 0.5:
        grad = grad.rotate(90, expand=True).resize(img.size)
    return ImageChops.multiply(img, grad.convert("RGB"))


def add_noise(img: Image.Image, sigma: float) -> Image.Image:
    noise = Image.effect_noise(img.size, sigma).convert("RGB")
    return ImageChops.add(img, noise, 1.0, -128)


def degrade(img: Image.Image, cfg: dict, rng: random.Random) -> Image.Image:
    img = add_shadow(img, rng.uniform(*cfg["shadow"]), rng)
    img = img.filter(ImageFilter.GaussianBlur(rng.uniform(*cfg["blur"])))
    img = add_noise(img, rng.uniform(*cfg["noise"]))
    angle = rng.uniform(*cfg["angle"]) * rng.choice([-1, 1])
    return img.rotate(angle, expand=True, fillcolor=(235, 235, 235), resample=Image.BICUBIC)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(GT_IN, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    level_names = list(LEVELS)
    out_rows = []
    for i, row in enumerate(rows):
        level = level_names[i % len(level_names)]
        cfg = LEVELS[level]
        rng = random.Random(1000 + i)  # seed tetap agar hasilnya bisa diulang

        img = render_pdf(SRC_DIR / row["filename"], cfg["dpi"])
        img = degrade(img, cfg, rng)

        out_name = "hard_" + Path(row["filename"]).stem + ".jpg"
        img.save(OUT_DIR / out_name, "JPEG", quality=rng.randint(*cfg["quality"]))

        out_rows.append({**row, "filename": out_name, "difficulty": level})

    with open(GT_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        writer.writeheader()
        writer.writerows(out_rows)

    counts = {lv: sum(r["difficulty"] == lv for r in out_rows) for lv in LEVELS}
    print(f"Selesai: {len(out_rows)} gambar di {OUT_DIR}/ dan {GT_OUT}")
    print("Tingkat kesulitan:", counts)


if __name__ == "__main__":
    main()
