from typing import List, Optional

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: Optional[str] = Field(description="Nama barang/jasa")
    quantity: Optional[float] = Field(description="Jumlah barang")
    unit_price: Optional[float] = Field(description="Harga satuan, angka saja")
    amount: Optional[float] = Field(description="Jumlah harga baris ini, angka saja")


class Invoice(BaseModel):
    vendor_name: Optional[str] = Field(description="Nama perusahaan penerbit invoice")
    invoice_number: Optional[str] = Field(description="Nomor invoice/referensi")
    invoice_date: Optional[str] = Field(description="Tanggal invoice, format YYYY-MM-DD")
    currency: Optional[str] = Field(description="Kode mata uang, misalnya IDR")
    subtotal: Optional[float] = Field(description="Subtotal sebelum pajak, angka saja")
    tax: Optional[float] = Field(description="Total pajak, angka saja")
    total: Optional[float] = Field(description="Total akhir yang harus dibayar, angka saja")
    line_items: List[LineItem] = Field(description="Daftar barang/jasa pada invoice")
    confidence: float = Field(description="Keyakinan ekstraksi secara keseluruhan, 0.0 sampai 1.0")
    uncertain_fields: List[str] = Field(
        description="Nama field yang diragukan atau tidak terbaca jelas; list kosong jika yakin semua"
    )
