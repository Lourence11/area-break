"""
Area Break - address column -> AREA / MUNICIPALITY / FINAL AREA / ZIP CODE
==========================================================================

The interface is a React + Tailwind component (frontend/dist, pre-built, so
no Node is needed to run it). This script is the back end: it receives events
from the component, runs area_engine, and sends back what the page shows.

    streamlit run area_break_app.py

Front-end development (only if you change the React code):
    cd frontend && npm install && npm run dev
    set AREA_BREAK_DEV=http://localhost:5173   (Windows)   then run Streamlit
"""

from __future__ import annotations

import base64
import io
import os
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from area_engine import (
    AREA_MODES,
    DEFAULT_REFERENCE,
    FINAL_AREA_MODES,
    Reference,
    break_addresses,
)

HERE = Path(__file__).resolve().parent
DIST = HERE / "frontend" / "dist"
DEV_URL = os.environ.get("AREA_BREAK_DEV")

OUTPUT_COLS = ["AREA", "MUNICIPALITY", "FINAL AREA", "ZIP CODE"]
AUDIT_COL = "MATCH SOURCE"
RESOLVED_SOURCES = {"ZIP", "TEXT-MUNICIPALITY", "TEXT-PROVINCE"}
PAGE_ROWS = 25
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_ISLAND, _NCR_CITY, _NCR_PROV, _REGION, _PROVINCE = list(FINAL_AREA_MODES)

OPTIONS = {
    "areaModes": [
        {"value": "Province", "label": "Province"},
        {"value": "Administrative region", "label": "Region"},
        {"value": "Island group", "label": "Island group"},
    ],
    "finalModes": [
        {"value": _ISLAND, "label": "Island group", "example": "NCR · NORTH LUZON · SOUTH LUZON · VISAYAS · MINDANAO"},
        {"value": _NCR_CITY, "label": "NCR city, else province", "example": "MAKATI · QUEZON CITY · CAVITE"},
        {"value": _NCR_PROV, "label": "NCR or provincial", "example": "NCR · PROVINCIAL"},
        {"value": _REGION, "label": "Region", "example": "NCR · REGION III · REGION IV-A"},
        {"value": _PROVINCE, "label": "Province", "example": "METRO MANILA · BULACAN · RIZAL"},
    ],
}
DEFAULT_RULES = {"areaMode": "Province", "finalMode": _ISLAND, "fallback": True}
_LABEL = {o["value"]: o["label"] for o in OPTIONS["areaModes"] + OPTIONS["finalModes"]}

if DEV_URL:
    _ui = components.declare_component("area_break_ui", url=DEV_URL)
else:
    if not (DIST / "index.html").exists():
        raise SystemExit("frontend/dist is missing. Run `npm install && npm run build` in frontend/.")
    _ui = components.declare_component("area_break_ui", path=str(DIST))


# --------------------------------------------------------------------------
# page shell: hide Streamlit's own chrome so the component is the whole page
# --------------------------------------------------------------------------
st.set_page_config(page_title="Area Break", page_icon=str(HERE / "favicon.png"), layout="wide")
st.markdown(
    """
    <style>
      header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
      [data-testid="stStatusWidget"], #MainMenu, footer { display: none !important; }
      .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] { background: #f3f5f8; }
      @media (prefers-color-scheme: dark) {
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] { background: #0e141c; }
      }
      .block-container, [data-testid="stMainBlockContainer"] {
        padding: 0 !important; max-width: 100% !important; }
      [data-testid="stVerticalBlock"] { gap: 0 !important; }
      [data-testid="stElementContainer"], .element-container, [data-stale] {
        opacity: 1 !important; transition: none !important; }
      iframe { border: 0 !important; display: block; }
    </style>
    """,
    unsafe_allow_html=True,
)

ss = st.session_state


# --------------------------------------------------------------------------
# reference table
# --------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def bundled_reference(mtime: float) -> Reference:
    return Reference.from_csv(DEFAULT_REFERENCE)


def reference_info(ref: Reference, name: str | None) -> dict:
    return {
        "zips": len(ref.by_zip),
        "provinces": len({r["PROVINCE"] for r in ref.by_zip.values()}),
        "custom": name is not None,
        "name": name or "Bundled table",
    }


def current_reference() -> Reference:
    if ss.get("ref_custom") is not None:
        return ss.ref_custom
    return bundled_reference(DEFAULT_REFERENCE.stat().st_mtime)


# --------------------------------------------------------------------------
# reading files
# --------------------------------------------------------------------------
def sheet_names(data: bytes, name: str) -> list[str]:
    if name.lower().endswith((".csv", ".txt")):
        return []
    try:
        return pd.ExcelFile(io.BytesIO(data), engine="calamine").sheet_names
    except Exception:
        return pd.ExcelFile(io.BytesIO(data)).sheet_names


def read_table(data: bytes, name: str, sheet: str | None) -> pd.DataFrame:
    if name.lower().endswith((".csv", ".txt")):
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                return pd.read_csv(io.BytesIO(data), dtype=str, encoding=enc, keep_default_na=False, na_values=[""])
            except UnicodeDecodeError:
                continue
    try:
        df = pd.read_excel(io.BytesIO(data), sheet_name=sheet or 0, dtype=str, engine="calamine")
    except Exception:
        df = pd.read_excel(io.BytesIO(data), sheet_name=sheet or 0, dtype=str)
    return df


def load_frame(sheet: str | None):
    df = read_table(ss.raw, ss.fname, sheet)
    df.columns = [str(c).strip() for c in df.columns]
    ss.df = df
    ss.sheet = sheet
    ss.addr_col = next((c for c in df.columns if "ADDRESS" in c.upper()), df.columns[0])
    ss.result = None


def file_state() -> dict | None:
    if ss.get("df") is None:
        return None
    df, col = ss.df, ss.addr_col
    s = df[col]
    filled = s.dropna().astype(str).str.strip()
    filled = filled[filled.ne("")]
    return {
        "name": ss.fname,
        "rows": int(len(df)),
        "columns": list(df.columns),
        "sheets": ss.sheets,
        "sheet": ss.sheet,
        "addrCol": col,
        "blanks": int(len(df) - len(filled)),
        "samples": filled.head(3).tolist(),
    }


# --------------------------------------------------------------------------
# running
# --------------------------------------------------------------------------
def run(rules: dict, nonce: int):
    df, col = ss.df, ss.addr_col
    t0 = time.perf_counter()
    broken = pd.DataFrame(
        break_addresses(
            df[col].tolist(),
            current_reference(),
            area_mode=rules["areaMode"],
            final_area_mode=rules["finalMode"],
            use_text_fallback=rules["fallback"],
        ),
        index=df.index,
    )
    elapsed = time.perf_counter() - t0

    # existing AREA / MUNICIPALITY / FINAL AREA / ZIP CODE columns are filled
    # in place (original order kept); missing ones are appended
    out = df.copy()
    for c in OUTPUT_COLS + [AUDIT_COL]:
        out[c] = broken[c]
    ss.out = out

    id_col = next((c for c in df.columns if c != col and c not in OUTPUT_COLS + [AUDIT_COL]), None)
    ss.id_col = id_col
    blob = out[col].fillna("")
    for c in [id_col, "MUNICIPALITY", "AREA", "ZIP CODE"]:
        if c:
            blob = blob + " " + out[c].fillna("").astype(str)
    ss.blob = blob.str.upper()

    src = broken[AUDIT_COL]
    resolved = int(src.isin(RESOLVED_SOURCES).sum())
    counts = lambda s: [{"label": k, "rows": int(v)} for k, v in s.value_counts().items()]  # noqa: E731
    missing = broken.loc[src.eq("ZIP NOT IN REFERENCE"), "ZIP CODE"].value_counts()

    ss.result = {
        "id": nonce,
        "rows": int(len(df)),
        "resolved": resolved,
        "unresolved": int(len(df) - resolved),
        "rate": resolved / len(df) if len(df) else 0.0,
        "elapsed": elapsed,
        "settings": dict(rules),
        "areaModeLabel": _LABEL[rules["areaMode"]],
        "finalModeLabel": _LABEL[rules["finalMode"]],
        "islandMode": rules["finalMode"] == _ISLAND,
        "sources": [{"key": k, "rows": int(v)} for k, v in src.value_counts().items()],
        "final": counts(broken["FINAL AREA"]),
        "area": counts(broken["AREA"]),
        "review": int(src.ne("ZIP").sum()),
        "missingZips": [{"zip": k, "rows": int(v)} for k, v in missing.head(40).items()],
    }
    query_table({"view": "all", "q": "", "final": "", "source": "", "page": 0})


def query_table(q: dict):
    out = ss.out
    mask = pd.Series(True, index=out.index)
    if q.get("view") == "review":
        mask &= out[AUDIT_COL].ne("ZIP")
    if q.get("final"):
        mask &= out["FINAL AREA"].eq(q["final"])
    if q.get("source"):
        mask &= out[AUDIT_COL].eq(q["source"])
    text = (q.get("q") or "").strip().upper()
    if text:
        mask &= ss.blob.str.contains(text, regex=False, na=False)

    cols = [c for c in [ss.id_col, ss.addr_col] if c] + OUTPUT_COLS + [AUDIT_COL]
    total = int(mask.sum())
    pages = max(1, -(-total // PAGE_ROWS))
    n = min(max(int(q.get("page") or 0), 0), pages - 1)
    q = {**q, "page": n}
    page = out.loc[mask, cols].iloc[n * PAGE_ROWS:(n + 1) * PAGE_ROWS].fillna("").astype(str)
    ss.table = {
        "query": q,
        "rows": page.to_dict("records"),
        "total": total,
        "offset": n * PAGE_ROWS,
        "pages": pages,
        "columns": cols,
        "idCol": ss.id_col,
        "addrCol": ss.addr_col,
    }


# --------------------------------------------------------------------------
# exports
# --------------------------------------------------------------------------
def to_excel(main: pd.DataFrame, review: pd.DataFrame) -> bytes:
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
            # constant_memory streams rows out as they are written, so the
            # header can only be restyled for the in-memory path
            head = wb.add_format({"bold": True, "bg_color": "#0F1B2D", "font_color": "#FFFFFF", "border": 1})
            for i, col in enumerate(main.columns):
                ws.write(0, i, col, head)
        if len(review):
            review.to_excel(xl, sheet_name="NEEDS REVIEW", index=False)
    return buf.getvalue()


def export(fmt: str, nonce: int):
    if fmt == "reference":
        data, name, mime = DEFAULT_REFERENCE.read_bytes(), "ph_zip_reference.csv", "text/csv"
    else:
        out = ss.out
        stem = f"AREA-BREAK_{Path(ss.fname).stem}"
        if fmt == "csv" or len(out) > 1_048_575:
            data, name, mime = out.to_csv(index=False).encode("utf-8-sig"), f"{stem}.csv", "text/csv"
            if fmt != "csv":
                ss.error = {"nonce": nonce, "message": f"{len(out):,} rows is over Excel's sheet limit, so you got a CSV."}
        else:
            review = out[out[AUDIT_COL].ne("ZIP")]
            data, name, mime = to_excel(out, review), f"{stem}.xlsx", XLSX_MIME
    ss.download = {"nonce": nonce, "name": name, "mime": mime, "b64": base64.b64encode(data).decode()}


# --------------------------------------------------------------------------
# event handling
# --------------------------------------------------------------------------
def handle(ev: dict):
    kind, nonce = ev.get("type"), ev["nonce"]
    ss.download = None
    ss.error = None

    if kind == "upload":
        ss.raw = base64.b64decode(ev["b64"])
        ss.fname = ev["name"]
        ss.sheets = sheet_names(ss.raw, ss.fname)
        load_frame(ss.sheets[0] if ss.sheets else None)

    elif kind == "select":
        if ev.get("sheet") and ev["sheet"] != ss.sheet:
            load_frame(ev["sheet"])
        if ev.get("addrCol"):
            ss.addr_col = ev["addrCol"]
            ss.result = None

    elif kind == "clear":
        for k in ("raw", "fname", "sheets", "sheet", "df", "addr_col", "result", "out", "table", "blob"):
            ss.pop(k, None)

    elif kind == "run":
        run({**DEFAULT_RULES, **(ev.get("rules") or {})}, nonce)

    elif kind == "table" and ss.get("out") is not None:
        query_table(ev.get("query") or {})

    elif kind == "export" and (ev.get("fmt") == "reference" or ss.get("out") is not None):
        export(ev["fmt"], nonce)

    elif kind == "reference":
        if ev.get("reset"):
            ss.ref_custom, ss.ref_name = None, None
        else:
            ref = Reference.from_csv(io.BytesIO(base64.b64decode(ev["b64"])))
            if not ref.by_zip:
                raise ValueError("That CSV has no usable rows. It needs a ZIP CODE column with 4-digit codes.")
            ss.ref_custom, ss.ref_name = ref, ev["name"]
        if ss.get("result"):  # results follow the table they were built with
            run(ss.result["settings"], nonce)


event = ss.get("ui")
if event and event.get("nonce") != ss.get("last_nonce"):
    ss.last_nonce = event["nonce"]
    try:
        handle(event)
    except Exception as exc:  # surface the reason in the page, never a traceback
        ss.error = {"nonce": event["nonce"], "message": f"{type(exc).__name__}: {exc}"}
    ss.ack = event["nonce"]


_ui(
    state={
        "ack": ss.get("ack", 0),
        "rules": DEFAULT_RULES,
        "options": OPTIONS,
        "reference": reference_info(current_reference(), ss.get("ref_name")),
        "file": file_state(),
        "result": ss.get("result"),
        "table": ss.get("table") if ss.get("result") else None,
        "download": ss.get("download"),
        "error": ss.get("error"),
    },
    key="ui",
    default=None,
)
