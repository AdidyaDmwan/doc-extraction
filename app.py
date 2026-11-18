import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from src import db
from src.review import (
    STATUS_APPROVED,
    STATUS_CORRECTED,
    build_invoice,
    clean_items,
    final_data,
    find_file,
    invoice_differs,
)
from src.validate import AUTO_APPROVED, CONFIDENCE_THRESHOLD, NEEDS_REVIEW, validate

st.set_page_config(page_title="Document Extraction", layout="wide")
db.init_db()

STATUS_LABEL = {
    AUTO_APPROVED: "Disetujui otomatis",
    NEEDS_REVIEW: "Perlu review",
    STATUS_APPROVED: "Disetujui manusia",
    STATUS_CORRECTED: "Dikoreksi manusia",
}
ITEM_COLUMNS = ["description", "quantity", "unit_price", "amount"]


@st.cache_data(show_spinner=False)
def render_preview(path_str: str) -> bytes:
    """Kembalikan gambar pratinjau dokumen (halaman pertama jika PDF)."""
    path = Path(path_str)
    if path.suffix.lower() == ".pdf":
        import fitz  # PyMuPDF

        with fitz.open(path_str) as doc:
            return doc[0].get_pixmap(dpi=110).tobytes("png")
    return path.read_bytes()


def show_preview(filename: str):
    path = find_file(filename)
    if path is None:
        st.warning(f"File '{filename}' tidak ditemukan di folder data.")
        return
    try:
        st.image(render_preview(str(path)), caption=filename)
    except Exception as e:  # noqa: BLE001
        st.warning(f"Pratinjau tidak bisa ditampilkan: {e}")


def items_dataframe(items: list) -> pd.DataFrame:
    df = pd.DataFrame(items or [], columns=ITEM_COLUMNS)
    return df.astype(
        {"description": "object", "quantity": "float64", "unit_price": "float64", "amount": "float64"}
    )


st.title("Document Extraction Pipeline")
st.caption("Ekstraksi invoice dengan AI, validasi aturan, dan review manusia untuk dokumen yang meragukan.")

if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

tab_dash, tab_review, tab_upload = st.tabs(["Dashboard", "Antrean Review", "Upload"])

# ---------------------------------------------------------------- Dashboard
with tab_dash:
    docs = db.get_documents()
    if not docs:
        st.info("Belum ada dokumen. Jalankan `python run_pipeline.py` atau unggah dokumen di tab Upload.")
    else:
        df = pd.DataFrame(
            [
                {
                    "filename": r["filename"],
                    "status": r["status"],
                    "confidence": (json.loads(r["data_json"]).get("confidence") if r["data_json"] else None),
                    "model": r["model_used"],
                    "detik": r["processing_seconds"],
                    "alasan": "; ".join(json.loads(r["reasons"] or "[]")),
                }
                for r in docs
            ]
        )
        total = len(df)
        n_auto = int((df["status"] == AUTO_APPROVED).sum())
        n_review = int((df["status"] == NEEDS_REVIEW).sum())
        n_human = int(df["status"].isin([STATUS_APPROVED, STATUS_CORRECTED]).sum())

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total dokumen", total)
        c2.metric("Disetujui otomatis", n_auto)
        c3.metric("Menunggu review", n_review)
        c4.metric("Sudah ditinjau manusia", n_human)
        c5.metric("Waktu median", f"{df['detik'].median():.1f} dtk")
        st.caption(f"Threshold confidence saat ini: {CONFIDENCE_THRESHOLD}")

        st.subheader("Jumlah dokumen per status")
        st.bar_chart(df["status"].map(lambda s: STATUS_LABEL.get(s, s)).value_counts())

        st.subheader("Daftar dokumen")
        options = ["Semua"] + sorted(df["status"].unique())
        chosen = st.selectbox("Filter status", options, format_func=lambda s: STATUS_LABEL.get(s, s))
        shown = df if chosen == "Semua" else df[df["status"] == chosen]
        st.dataframe(shown, hide_index=True)

        # Export data akhir (koreksi manusia jika ada, selain itu hasil AI)
        export_rows = []
        for r in docs:
            if r["status"] == NEEDS_REVIEW:
                continue  # belum dikonfirmasi
            data = final_data(r)
            if data is None:
                continue
            export_rows.append(
                {
                    "filename": r["filename"],
                    "status": r["status"],
                    **{k: data.get(k) for k in [
                        "vendor_name", "invoice_number", "invoice_date", "currency", "subtotal", "tax", "total"
                    ]},
                    "jumlah_item": len(data.get("line_items") or []),
                }
            )
        st.download_button(
            "Unduh data yang sudah final (CSV)",
            pd.DataFrame(export_rows).to_csv(index=False).encode("utf-8"),
            file_name="invoices_final.csv",
            mime="text/csv",
            disabled=not export_rows,
        )
        st.caption("Dokumen yang masih menunggu review tidak ikut diekspor.")

# ------------------------------------------------------------ Antrean Review
with tab_review:
    queue = db.get_documents([NEEDS_REVIEW])
    if not queue:
        st.success("Antrean kosong. Tidak ada dokumen yang menunggu review.")
    else:
        names = [r["filename"] for r in queue]
        st.write(f"**{len(names)}** dokumen menunggu review.")
        selected = st.selectbox("Pilih dokumen", names)
        row = db.get_document(selected)
        original = json.loads(row["data_json"]) if row["data_json"] else None
        reasons = json.loads(row["reasons"] or "[]")
        base = original or {}

        left, right = st.columns(2)
        with left:
            show_preview(selected)

        with right:
            st.warning("**Kenapa dokumen ini perlu ditinjau:**\n\n" + "\n".join(f"- {r}" for r in reasons))
            st.caption("Bandingkan isian di bawah dengan dokumen di sebelah kiri, lalu perbaiki jika ada yang salah.")

            key = lambda name: f"{name}_{selected}"  # noqa: E731  (state terpisah per dokumen)
            values = {}
            values["vendor_name"] = st.text_input("Nama vendor", base.get("vendor_name") or "", key=key("vendor"))
            col_a, col_b = st.columns(2)
            values["invoice_number"] = col_a.text_input("Nomor invoice", base.get("invoice_number") or "", key=key("number"))
            values["invoice_date"] = col_b.text_input("Tanggal (YYYY-MM-DD)", base.get("invoice_date") or "", key=key("date"))
            col_c, col_d, col_e, col_f = st.columns(4)
            values["currency"] = col_c.text_input("Mata uang", base.get("currency") or "", key=key("currency"))
            for col, field, label in [
                (col_d, "subtotal", "Subtotal"),
                (col_e, "tax", "Pajak"),
                (col_f, "total", "Total"),
            ]:
                orig_val = base.get(field)
                typed = col.number_input(
                    label, min_value=0.0, value=float(orig_val) if orig_val is not None else 0.0,
                    step=1.0, format="%.2f", key=key(field),
                )
                # Kolom kosong di hasil AI dan tidak diisi pengguna tetap dianggap kosong
                values[field] = None if (orig_val is None and typed == 0.0) else typed

            st.write("**Item invoice** (bisa diedit, tambah, atau hapus baris)")
            edited = st.data_editor(
                items_dataframe(base.get("line_items")),
                num_rows="dynamic",
                key=key("items"),
                column_config={
                    "description": st.column_config.TextColumn("Deskripsi"),
                    "quantity": st.column_config.NumberColumn("Qty"),
                    "unit_price": st.column_config.NumberColumn("Harga satuan"),
                    "amount": st.column_config.NumberColumn("Jumlah"),
                },
            )
            items = clean_items(edited.to_dict("records"))

            candidate = build_invoice(values, items, confidence=float(base.get("confidence") or 0.0))
            problems = validate(candidate)
            if problems:
                st.error("**Pemeriksaan otomatis atas isian ini:**\n\n" + "\n".join(f"- {p}" for p in problems))
            else:
                st.info("Isian ini lolos semua aturan validasi.")

            if st.button("Simpan dan setujui", type="primary", key=key("save")):
                corrected = candidate.model_dump()
                status = STATUS_CORRECTED if invoice_differs(original, corrected) else STATUS_APPROVED
                db.save_review(selected, status, json.dumps(corrected, ensure_ascii=False))
                st.session_state["flash"] = f"{selected}: {STATUS_LABEL[status].lower()}."
                st.rerun()

# -------------------------------------------------------------------- Upload
with tab_upload:
    st.write("Unggah satu invoice (PDF, PNG, atau JPG) untuk diproses langsung oleh pipeline.")
    uploaded = st.file_uploader("Pilih file", type=["pdf", "png", "jpg", "jpeg"])

    if uploaded is not None and st.button("Proses dokumen", type="primary"):
        try:
            from src.pipeline import process_file  # impor di sini agar tab lain tetap jalan tanpa API key

            folder = Path("data/uploads")
            folder.mkdir(parents=True, exist_ok=True)
            safe_name = f"{datetime.now():%Y%m%d_%H%M%S}_{Path(uploaded.name).name}"
            path = folder / safe_name
            path.write_bytes(uploaded.getvalue())

            with st.spinner("Memproses dokumen..."):
                status, reasons, seconds = process_file(path)
            st.session_state["last_upload"] = (safe_name, status, reasons, seconds)
        except RuntimeError as e:
            st.error(f"Pipeline tidak bisa dijalankan: {e}")

    if "last_upload" in st.session_state:
        name, status, reasons, seconds = st.session_state["last_upload"]
        st.subheader(f"Hasil: {name}")
        st.write(f"Status: **{STATUS_LABEL.get(status, status)}** ({seconds:.1f} detik)")
        if reasons:
            st.warning("Alasan:\n\n" + "\n".join(f"- {r}" for r in reasons))
            st.caption("Dokumen ini masuk Antrean Review.")
        row = db.get_document(name)
        if row and row["data_json"]:
            st.json(json.loads(row["data_json"]))
