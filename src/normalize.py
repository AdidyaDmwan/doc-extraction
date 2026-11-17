import re
from typing import Optional

# Alias mata uang yang jelas artinya. Sengaja tidak memetakan simbol ambigu seperti "$".
CURRENCY_ALIASES = {
    "rp": "IDR",
    "rp.": "IDR",
    "rupiah": "IDR",
    "idr": "IDR",
    "usd": "USD",
    "us$": "USD",
    "us dollar": "USD",
    "dolar as": "USD",
    "eur": "EUR",
    "euro": "EUR",
    "sgd": "SGD",
    "myr": "MYR",
}


def normalize_currency(value: Optional[str]) -> Optional[str]:
    """Ubah penulisan mata uang ke kode ISO 4217 (tiga huruf besar) bila jelas.

    Nilai yang tidak dikenali dibiarkan apa adanya, supaya validasi menandainya
    dan dokumen diarahkan ke review manusia (bukan ditebak).
    """
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    alias = CURRENCY_ALIASES.get(cleaned.lower())
    if alias:
        return alias
    if re.fullmatch(r"[A-Za-z]{3}", cleaned):
        return cleaned.upper()
    return cleaned
