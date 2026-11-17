import csv
import random
from datetime import date, timedelta
from pathlib import Path

from faker import Faker
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

fake = Faker("id_ID")
random.seed(42)
Faker.seed(42)

OUT = Path("data/samples")
OUT.mkdir(parents=True, exist_ok=True)

PRODUCTS = [
    "Kertas A4 80gsm", "Tinta Printer Hitam", "Mouse Wireless", "Keyboard Mekanik",
    "Monitor 24 inci", "Kabel HDMI 2m", "Flashdisk 64GB", "Headset Gaming",
    "Meja Kerja Lipat", "Kursi Ergonomis", "Lampu LED Meja", "Stapler Besar",
    "Jasa Instalasi Jaringan", "Jasa Konsultasi IT", "Lisensi Software Tahunan",
]

# Format tanggal bervariasi supaya AI diuji ketahanannya
DATE_FORMATS = ["%d/%m/%Y", "%d %B %Y", "%Y-%m-%d", "%d-%m-%Y"]


def rupiah(n: int) -> str:
    return f"Rp {n:,.0f}".replace(",", ".")


def make_invoice(idx: int) -> dict:
    items = []
    for _ in range(random.randint(2, 6)):
        qty = random.randint(1, 10)
        price = random.randrange(10_000, 500_000, 5_000)
        items.append({
            "description": random.choice(PRODUCTS),
            "quantity": qty,
            "unit_price": price,
            "amount": qty * price,
        })
    subtotal = sum(i["amount"] for i in items)
    tax = round(subtotal * 0.11)  # PPN 11%
    d = date(2026, 1, 1) + timedelta(days=random.randint(0, 300))
    return {
        "filename": f"invoice_{idx:03d}.pdf",
        "vendor_name": fake.company(),
        "invoice_number": f"INV-{random.randint(2024, 2026)}-{random.randint(1000, 9999)}",
        "date_obj": d,
        "date_fmt": random.choice(DATE_FORMATS),
        "currency": "IDR",
        "items": items,
        "subtotal": subtotal,
        "tax": tax,
        "total": subtotal + tax,
        "layout": random.choice([0, 1, 2]),
    }


def draw_pdf(inv: dict):
    c = canvas.Canvas(str(OUT / inv["filename"]), pagesize=A4)
    w, h = A4
    date_str = inv["date_obj"].strftime(inv["date_fmt"])

    # Tiga layout berbeda: posisi header & label bervariasi
    if inv["layout"] == 0:
        c.setFont("Helvetica-Bold", 18)
        c.drawString(50, h - 60, inv["vendor_name"])
        c.setFont("Helvetica", 11)
        c.drawString(50, h - 85, f"Invoice No: {inv['invoice_number']}")
        c.drawString(50, h - 100, f"Tanggal: {date_str}")
    elif inv["layout"] == 1:
        c.setFont("Helvetica-Bold", 22)
        c.drawRightString(w - 50, h - 60, "INVOICE")
        c.setFont("Helvetica", 11)
        c.drawRightString(w - 50, h - 85, f"No. {inv['invoice_number']}")
        c.drawRightString(w - 50, h - 100, f"Date: {date_str}")
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, h - 60, inv["vendor_name"])
    else:
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(w / 2, h - 60, inv["vendor_name"])
        c.setFont("Helvetica", 10)
        c.drawCentredString(w / 2, h - 78, fake.address().replace("\n", ", ")[:80])
        c.setFont("Helvetica", 11)
        c.drawString(50, h - 115, f"Ref: {inv['invoice_number']}    Tgl: {date_str}")

    # Tabel item
    y = h - 170
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Deskripsi")
    c.drawString(290, y, "Qty")
    c.drawString(340, y, "Harga")
    c.drawString(450, y, "Jumlah")
    c.line(50, y - 4, w - 50, y - 4)
    c.setFont("Helvetica", 10)
    for it in inv["items"]:
        y -= 20
        c.drawString(50, y, it["description"])
        c.drawString(290, y, str(it["quantity"]))
        c.drawString(340, y, rupiah(it["unit_price"]))
        c.drawString(450, y, rupiah(it["amount"]))

    # Total
    y -= 40
    c.drawString(340, y, "Subtotal:")
    c.drawString(450, y, rupiah(inv["subtotal"]))
    y -= 18
    c.drawString(340, y, "PPN 11%:")
    c.drawString(450, y, rupiah(inv["tax"]))
    y -= 22
    c.setFont("Helvetica-Bold", 12)
    c.drawString(340, y, "TOTAL:")
    c.drawString(450, y, rupiah(inv["total"]))
    c.save()


def main(n: int = 40):
    rows = []
    for i in range(1, n + 1):
        inv = make_invoice(i)
        draw_pdf(inv)
        rows.append({
            "filename": inv["filename"],
            "vendor_name": inv["vendor_name"],
            "invoice_number": inv["invoice_number"],
            "invoice_date": inv["date_obj"].strftime("%Y-%m-%d"),
            "currency": inv["currency"],
            "subtotal": inv["subtotal"],
            "tax": inv["tax"],
            "total": inv["total"],
            "num_items": len(inv["items"]),
        })

    with open("data/ground_truth.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Selesai: {n} PDF di {OUT}/ dan data/ground_truth.csv")


if __name__ == "__main__":
    main()