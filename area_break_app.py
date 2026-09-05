"""
AREA BREAK - address parser for collections portfolios
=====================================================
Upload a file with an ADDRESS column, get AREA / MUNICIPALITY / FINAL AREA /
ZIP CODE filled in, plus an audit trail showing how every row was resolved.

Run:  streamlit run area_break_app.py
Needs: streamlit, pandas, openpyxl, xlsxwriter   (python-calamine optional, faster reads)
Keep ph_zip_reference.csv in the same folder as this file.
"""

from __future__ import annotations

import io
import time
from pathlib import Path

import pandas as pd
import streamlit as st

from area_engine import (
    AREA_MODES,
    FINAL_AREA_MODES,
    DEFAULT_REFERENCE,
    Reference,
    break_addresses,
)

OUTPUT_COLS = ["AREA", "MUNICIPALITY", "FINAL AREA", "ZIP CODE"]
AUDIT_COL = "MATCH SOURCE"

st.set_page_config(page_title="Area Break", page_icon="◧", layout="wide")

# --------------------------------------------------------------------------
# styling - quiet slate shell, one signal colour on the coverage readout
# --------------------------------------------------------------------------
st.markdown(
    """
    <style>
      .stApp { background:#0f1620; }
      section[data-testid="stSidebar"] { background:#141d29; border-right:1px solid #22303f; }
      h1,h2,h3,h4,p,label,span,div { color:#dbe4ee; }
      .ab-title { font-size:2.05rem; font-weight:700; letter-spacing:-.02em; margin:0; color:#f2f6fa; }
      .ab-sub { color:#7d8fa3; font-size:.9rem; margin:.15rem 0 1.4rem; }
      .ab-card { background:#141d29; border:1px solid #22303f; border-radius:10px;
                 padding:1rem 1.15rem; margin-bottom:.7rem; }
      .ab-kpi { font-size:1.7rem; font-weight:700; color:#f2f6fa; line-height:1.1; }
      .ab-lab { font-size:.72rem; letter-spacing:.09em; text-transform:uppercase; color:#7d8fa3; }
      .ab-bar { height:9px; border-radius:5px; background:#22303f; overflow:hidden; margin-top:.55rem; }
      .ab-bar > i { display:block; height:100%; background:#3ddc97; }
      .ab-warn { color:#f2b544; }
      .stButton>button, .stDownloadButton>button {
          background:#3ddc97; color:#0f1620; border:0; border-radius:7px;
          font-weight:650; padding:.5rem 1.15rem; }
      .stButton>button:hover, .stDownloadButton>button:hover { background:#57e8a9; color:#0f1620; }
      div[data-testid="stDataFrame"] { border:1px solid #22303f; border-radius:8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<p class="ab-title">Area Break</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="ab-sub">Parses a free-text address column into AREA, MUNICIPALITY, '
    "FINAL AREA and ZIP CODE. Every row is tagged with how it was resolved.</p>",
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------
# reference table
# --------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def load_default_reference(mtime: float):
    return Reference.from_csv(DEFAULT_REFERENCE)


@st.cache_data(show_spinner=False)
def read_reference_df(path: str):
    return pd.read_csv(path, dtype=str).fillna("")


with st.sidebar:
    st.markdown('<p class="ab-lab">Reference table</p>', unsafe_allow_html=True)

    ref_upload = st.file_uploader(
        "Custom ZIP reference (optional)",
        type=["csv"],
        help="Columns: ZIP CODE, MUNICIPALITY, PROVINCE, REGION, ISLAND GROUP. "
             "Replaces the bundled table entirely.",
    )

    if ref_upload is not None:
        reference = Reference.from_csv(ref_upload)
        st.success(f"Custom table loaded — {len(reference.by_zip):,} ZIP codes")
    else:
        if not Path(DEFAULT_REFERENCE).exists():
            st.error("ph_zip_reference.csv is missing. Put it beside this script.")
            st.stop()
        reference = load_default_reference(Path(DEFAULT_REFERENCE).stat().st_mtime)
        st.caption(f"Bundled table — {len(reference.by_zip):,} ZIP codes, "
                   f"{len({r['PROVINCE'] for r in reference.by_zip.values()})} provinces")

    st.divider()
    st.markdown('<p class="ab-lab">Output rules</p>', unsafe_allow_html=True)

    area_mode = st.selectbox("AREA column", list(AREA_MODES), index=0)
    final_mode = st.selectbox("FINAL AREA column", list(FINAL_AREA_MODES), index=0)

    st.divider()
    st.markdown('<p class="ab-lab">Matching</p>', unsafe_allow_html=True)
    use_fallback = st.checkbox(
        "Scan address text when the ZIP fails",
        value=True,
        help="If no ZIP is found — or the ZIP is not in the reference — look for a "
             "known municipality or province name inside the address string.",
    )
    keep_source_zip = st.checkbox(
        "Keep the ZIP as written in the address",
        value=True,
        help="Off: use the reference table's ZIP for the matched municipality instead.",
    )

    st.divider()
    with st.expander("Reference table preview"):
        if ref_upload is None:
            st.dataframe(read_reference_df(str(DEFAULT_REFERENCE)).head(300),
                         use_container_width=True, height=280)
            st.download_button(
                "Download reference CSV",
                Path(DEFAULT_REFERENCE).read_bytes(),
                file_name="ph_zip_reference.csv",
                mime="text/csv",
            )
        else:
            st.caption("Showing your uploaded table.")


# --------------------------------------------------------------------------
# file input
# --------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def read_source(data: bytes, name: str, sheet: str | None):
    buf = io.BytesIO(data)
    if name.lower().endswith((".csv", ".txt")):
        return pd.read_csv(buf, dtype=str, keep_default_na=False, na_values=[""])
    try:
        return pd.read_excel(buf, sheet_name=sheet or 0, dtype=str, engine="calamine")
    except Exception:
        buf.seek(0)
        return pd.read_excel(buf, sheet_name=sheet or 0, dtype=str)


@st.cache_data(show_spinner=False)
def sheet_names(data: bytes, name: str):
    if name.lower().endswith((".csv", ".txt")):
        return []
    return pd.ExcelFile(io.BytesIO(data)).sheet_names


uploaded = st.file_uploader("Source file", type=["xlsx", "xlsm", "xls", "csv"])

if uploaded is None:
    st.info("Upload the file with the address column to begin.")
    st.stop()

raw = uploaded.getvalue()
sheets = sheet_names(raw, uploaded.name)
sheet = st.selectbox("Sheet", sheets) if len(sheets) > 1 else (sheets[0] if sheets else None)

with st.spinner("Reading file…"):
    df = read_source(raw, uploaded.name, sheet)

df.columns = [str(c).strip() for c in df.columns]

# --- address column: guess, let the user correct -------------------------
guess = next((c for c in df.columns if "ADDRESS" in c.upper()), df.columns[0])
addr_col = st.selectbox(
    "Address column", list(df.columns), index=list(df.columns).index(guess)
)

c1, c2, c3 = st.columns(3)
c1.markdown(f'<div class="ab-card"><div class="ab-lab">Rows</div>'
            f'<div class="ab-kpi">{len(df):,}</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="ab-card"><div class="ab-lab">Columns</div>'
            f'<div class="ab-kpi">{len(df.columns)}</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="ab-card"><div class="ab-lab">Blank addresses</div>'
            f'<div class="ab-kpi">{int(df[addr_col].isna().sum()):,}</div></div>',
            unsafe_allow_html=True)

with st.expander("Preview source"):
    st.dataframe(df.head(50), use_container_width=True)

if not st.button("Run area break", type="primary"):
    st.stop()


# --------------------------------------------------------------------------
# process
# --------------------------------------------------------------------------
t0 = time.time()
with st.spinner(f"Breaking {len(df):,} addresses…"):
    broken = pd.DataFrame(
        break_addresses(
            df[addr_col].tolist(),
            reference,
            area_mode=area_mode,
            final_area_mode=final_mode,
            use_text_fallback=use_fallback,
            keep_source_zip=keep_source_zip,
        ),
        index=df.index,
    )
elapsed = time.time() - t0

# Existing AREA / MUNICIPALITY / FINAL AREA / ZIP CODE columns are filled in
# place so the original column order survives; anything missing is appended.
out = df.copy()
for col in OUTPUT_COLS + [AUDIT_COL]:
    out[col] = broken[col]

resolved = broken["MUNICIPALITY"].ne("")
rate = resolved.mean() if len(broken) else 0.0

st.markdown(
    f'<div class="ab-card"><div class="ab-lab">Resolved</div>'
    f'<div class="ab-kpi">{resolved.sum():,} / {len(broken):,} '
    f'<span style="font-size:1rem;color:#3ddc97">{rate:.2%}</span></div>'
    f'<div class="ab-bar"><i style="width:{rate*100:.2f}%"></i></div>'
    f'<div class="ab-lab" style="margin-top:.6rem">{elapsed:.1f}s</div></div>',
    unsafe_allow_html=True,
)

left, right = st.columns([1, 1])
with left:
    st.markdown('<p class="ab-lab">How each row matched</p>', unsafe_allow_html=True)
    st.dataframe(
        broken[AUDIT_COL].value_counts().rename_axis("source").reset_index(name="rows"),
        use_container_width=True, hide_index=True,
    )
with right:
    st.markdown('<p class="ab-lab">FINAL AREA breakdown</p>', unsafe_allow_html=True)
    st.dataframe(
        broken["FINAL AREA"].replace("", "(unresolved)")
        .value_counts().rename_axis("final area").reset_index(name="rows"),
        use_container_width=True, hide_index=True,
    )

st.markdown('<p class="ab-lab">AREA breakdown</p>', unsafe_allow_html=True)
st.dataframe(
    broken["AREA"].replace("", "(unresolved)")
    .value_counts().rename_axis("area").reset_index(name="rows"),
    use_container_width=True, hide_index=True, height=280,
)

# --- exceptions ----------------------------------------------------------
exc_mask = ~resolved
exceptions = out.loc[exc_mask, [addr_col] + OUTPUT_COLS + [AUDIT_COL]]

if len(exceptions):
    st.markdown(
        f'<p class="ab-lab ab-warn">{len(exceptions):,} unresolved — '
        "add the ZIP to the reference table and re-run</p>",
        unsafe_allow_html=True,
    )
    st.dataframe(exceptions.head(500), use_container_width=True)

    unknown = (
        broken.loc[broken[AUDIT_COL] == "ZIP NOT IN REFERENCE", "ZIP CODE"]
        .value_counts().rename_axis("zip code").reset_index(name="rows")
    )
    if len(unknown):
        st.markdown('<p class="ab-lab">ZIP codes missing from the reference</p>',
                    unsafe_allow_html=True)
        st.dataframe(unknown, use_container_width=True, hide_index=True)
else:
    st.success("Every row resolved.")

st.markdown('<p class="ab-lab">Result preview</p>', unsafe_allow_html=True)
st.dataframe(out.head(200), use_container_width=True)


# --------------------------------------------------------------------------
# export
# --------------------------------------------------------------------------
def to_excel(main: pd.DataFrame, extra: pd.DataFrame) -> bytes:
    """Size-adaptive write. Excel caps a sheet at 1,048,576 rows."""
    buf = io.BytesIO()
    big = len(main) > 200_000
    with pd.ExcelWriter(
        buf, engine="xlsxwriter",
        engine_kwargs={"options": {"constant_memory": big, "strings_to_numbers": False}},
    ) as xl:
        main.to_excel(xl, sheet_name="AREA BREAK", index=False)
        wb, ws = xl.book, xl.sheets["AREA BREAK"]
        txt = wb.add_format({"num_format": "@"})
        for i, col in enumerate(main.columns):
            width = min(max(12, int(main[col].astype(str).str.len().head(2000).max() or 12) + 2), 55)
            ws.set_column(i, i, width, txt if col == "ZIP CODE" else None)
        ws.freeze_panes(1, 0)
        ws.autofilter(0, 0, max(len(main), 1), len(main.columns) - 1)
        if not big:
            # constant_memory streams rows out as they are written, so row 0 can
            # no longer be touched once the data is in. Only restyle when it can.
            head = wb.add_format({"bold": True, "bg_color": "#1F3247",
                                  "font_color": "#FFFFFF", "border": 1,
                                  "border_color": "#2E4359"})
            for i, col in enumerate(main.columns):
                ws.write(0, i, col, head)
        if len(extra):
            extra.to_excel(xl, sheet_name="EXCEPTIONS", index=False)
    return buf.getvalue()


if len(out) > 1_048_575:
    st.warning(
        f"{len(out):,} rows exceeds the Excel sheet limit of 1,048,576. "
        "Download as CSV instead, or split the source file."
    )
    st.download_button(
        "Download CSV", out.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"AREA-BREAK_{Path(uploaded.name).stem}.csv", mime="text/csv",
    )
else:
    with st.spinner("Building workbook…"):
        xlsx = to_excel(out, exceptions)
    st.download_button(
        "Download Excel", xlsx,
        file_name=f"AREA-BREAK_{Path(uploaded.name).stem}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.download_button(
        "Download CSV", out.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"AREA-BREAK_{Path(uploaded.name).stem}.csv", mime="text/csv",
    )
