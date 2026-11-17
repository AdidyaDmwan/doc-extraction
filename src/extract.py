import logging
import mimetypes
import os

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from .normalize import normalize_currency
from .schema import Invoice

load_dotenv()

logger = logging.getLogger(__name__)

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY tidak ditemukan. Pastikan file .env ada di root project "
        "dan berisi: GEMINI_API_KEY=key_anda"
    )

# Model utama (bisa diganti lewat .env tanpa mengubah kode)
PRIMARY_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Model cadangan, dipisah koma. Bisa diganti lewat .env: GEMINI_FALLBACK_MODELS=a,b,c
_fallback_raw = os.getenv(
    "GEMINI_FALLBACK_MODELS", "gemini-3.1-flash-lite,gemini-2.5-flash-lite"
)
FALLBACK_MODELS = [m.strip() for m in _fallback_raw.split(",") if m.strip()]

# Urutan percobaan tanpa duplikat: utama dulu, lalu cadangan
MODELS = list(dict.fromkeys([PRIMARY_MODEL] + FALLBACK_MODELS))

client = genai.Client(api_key=API_KEY)

PROMPT = """Ekstrak data dari dokumen invoice ini sesuai skema.
Aturan:
- Jika sebuah field tidak ada atau tidak terbaca, isi null. JANGAN menebak.
- Tanggal harus dalam format YYYY-MM-DD.
- Field 'currency' harus berupa kode mata uang ISO 4217 tiga huruf (misalnya IDR untuk Rupiah/Rp, USD untuk dolar AS). Jangan menulis simbol seperti 'Rp' atau '$'.
- Angka ditulis tanpa simbol mata uang dan tanpa pemisah ribuan (contoh: 1500000).
- Isi 'confidence' dengan jujur (0.0 sampai 1.0).
- Daftarkan di 'uncertain_fields' setiap field yang Anda ragukan."""

# Kode error yang layak dicoba ulang / dialihkan ke model lain
RETRYABLE_CODES = (429, 500, 503, 504)
SWITCH_MODEL_CODES = RETRYABLE_CODES + (404,)


def _is_retryable(exc: BaseException) -> bool:
    """Coba ulang model yang sama hanya untuk rate limit (429) dan error server (5xx)."""
    return isinstance(exc, errors.APIError) and exc.code in RETRYABLE_CODES


@retry(
    retry=retry_if_exception(_is_retryable),
    wait=wait_exponential(multiplier=2, min=2, max=15),
    stop=stop_after_attempt(3),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_gemini(model: str, data: bytes, mime: str):
    return client.models.generate_content(
        model=model,
        contents=[types.Part.from_bytes(data=data, mime_type=mime), PROMPT],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Invoice,
            temperature=0,
        ),
    )


def extract_invoice_with_model(path: str) -> tuple[Invoice, str]:
    """Ekstrak invoice dan kembalikan (hasil, nama model yang dipakai).

    Jika model gagal setelah beberapa kali coba ulang, otomatis pindah ke model cadangan.
    """
    mime = mimetypes.guess_type(path)[0] or "application/pdf"
    with open(path, "rb") as f:
        data = f.read()

    last_error = None
    for model in MODELS:
        try:
            resp = _call_gemini(model, data, mime)
        except errors.APIError as e:
            if e.code in SWITCH_MODEL_CODES:
                logger.warning("Model %s gagal (%s). Mencoba model cadangan...", model, e.code)
                last_error = e
                continue
            raise  # error lain (misalnya 400/403) tidak akan membaik dengan ganti model

        invoice = resp.parsed
        if invoice is None:
            # Cadangan: parse manual dari teks JSON jika .parsed kosong
            invoice = Invoice.model_validate_json(resp.text)
        # Rapikan penulisan mata uang ke kode ISO (aturan pasti, bukan tebakan AI)
        invoice.currency = normalize_currency(invoice.currency)
        return invoice, model

    raise RuntimeError(f"Semua model gagal. Error terakhir: {last_error}")


def extract_invoice(path: str) -> Invoice:
    """Versi sederhana: hanya mengembalikan hasil ekstraksi."""
    invoice, _ = extract_invoice_with_model(path)
    return invoice
