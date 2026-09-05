"""
AREA BREAK engine
=================
Parses a free-text ADDRESS column into ZIP CODE / MUNICIPALITY / AREA / FINAL AREA.

Resolution order per row
------------------------
1. ZIP CODE  - pulled out of the address string (two source formats supported)
2. ZIP -> MUNICIPALITY / PROVINCE  via the reference table
3. If the ZIP is missing or not in the reference, fall back to scanning the
   address text for a known municipality name, then a known province name.
4. FINAL AREA - a roll-up of the above, per the selected mode.

Every row is tagged with a MATCH SOURCE so the output is auditable.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

# --------------------------------------------------------------------------
# text helpers
# --------------------------------------------------------------------------

_PUNCT = re.compile(r"[^A-Z0-9 ]+")
_WS = re.compile(r"\s+")


def deaccent(s: str) -> str:
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()


def norm(s) -> str:
    """Upper-case, de-accent, strip punctuation, collapse whitespace."""
    if s is None:
        return ""
    return _WS.sub(" ", _PUNCT.sub(" ", deaccent(str(s)).upper())).strip()


# Local spelling variants seen in bank address files -> canonical municipality.
ALIASES = {
    "KALOOKAN": "CALOOCAN",
    "KALOOCAN": "CALOOCAN",
    "MONTALBAN": "RODRIGUEZ",
    "PARANAQUE CITY": "PARANAQUE",
    "LASPINAS": "LAS PINAS",
    "LAS PINAS CITY": "LAS PINAS",
    "QC": "QUEZON CITY",
    "MLA": "MANILA",
    "DASMARINAS CITY": "DASMARINAS",
    "GMA": "GENERAL MARIANO ALVAREZ",
    "GEN TRIAS": "GENERAL TRIAS",
    "GEN MARIANO ALVAREZ": "GENERAL MARIANO ALVAREZ",
    "BIÑAN": "BINAN",
    "SAN JOSE DEL MONTE": "SAN JOSE DEL MONTE CITY",
    "SJDM": "SAN JOSE DEL MONTE CITY",
    "STA ROSA": "SANTA ROSA",
    "STA MARIA": "SANTA MARIA",
    "STA CRUZ": "SANTA CRUZ",
    "STO TOMAS": "SANTO TOMAS",
    "STA TERESITA": "SANTA TERESITA",
    "SAN PEDRO CITY": "SAN PEDRO",
    "TRECE MARTIREZ": "TREZE MARTIREZ",
    "MUNOZ": "SCIENCE CITY OF MUNOZ",
}

# Words that must never be treated as a municipality when scanning free text.
STOPWORDS = {
    "PHILIPPINES", "PHILS", "PH", "METRO MANILA", "MM", "NCR", "CITY",
    "PROVINCE", "BRGY", "BARANGAY", "PUROK", "BLK", "BLOCK", "LOT", "ST",
    "STREET", "AVE", "AVENUE", "RD", "ROAD", "SUBD", "SUBDIVISION", "PH",
    "VILLAGE", "VILL", "COMPOUND", "BLDG", "BUILDING", "UNIT", "FLR", "FLOOR",
}

DEFAULT_REFERENCE = Path(__file__).with_name("ph_zip_reference.csv")


# --------------------------------------------------------------------------
# reference table
# --------------------------------------------------------------------------

class Reference:
    """ZIP -> MUNICIPALITY / PROVINCE / REGION / ISLAND GROUP lookup."""

    def __init__(self, rows):
        self.by_zip: dict[str, dict] = {}
        self.by_muni: dict[str, dict] = {}
        self.by_prov: dict[str, dict] = {}

        for r in rows:
            z = str(r.get("ZIP CODE", "")).strip()
            z = re.sub(r"\D", "", z).zfill(4) if z else ""
            if not re.fullmatch(r"\d{4}", z):
                continue
            rec = {
                "ZIP CODE": z,
                "MUNICIPALITY": norm(r.get("MUNICIPALITY")),
                "PROVINCE": norm(r.get("PROVINCE")),
                "REGION": norm(r.get("REGION")),
                "ISLAND GROUP": norm(r.get("ISLAND GROUP")),
            }
            self.by_zip.setdefault(z, rec)
            self.by_muni.setdefault(rec["MUNICIPALITY"], rec)
            self.by_prov.setdefault(rec["PROVINCE"], rec)

        # longest names first so "SAN JOSE DEL MONTE CITY" wins over "SAN JOSE"
        self._muni_scan = sorted(
            (m for m in self.by_muni if len(m) >= 4 and m not in STOPWORDS),
            key=len, reverse=True,
        )
        self._prov_scan = sorted(
            (p for p in self.by_prov if len(p) >= 4 and p not in STOPWORDS),
            key=len, reverse=True,
        )

    # ---- constructors ----------------------------------------------------
    @classmethod
    def from_csv(cls, path_or_buffer):
        if hasattr(path_or_buffer, "read"):
            text = path_or_buffer.read()
            if isinstance(text, bytes):
                text = text.decode("utf-8-sig", errors="replace")
            return cls(csv.DictReader(text.splitlines()))
        with open(path_or_buffer, encoding="utf-8-sig", newline="") as f:
            return cls(list(csv.DictReader(f)))

    @classmethod
    def from_dataframe(cls, df):
        return cls(df.to_dict("records"))

    # ---- lookups ---------------------------------------------------------
    def by_zipcode(self, z):
        return self.by_zip.get(z)

    def scan_text(self, address_norm: str):
        """Find a municipality (then a province) named inside the address text."""
        padded = f" {address_norm} "
        for m in self._muni_scan:
            if f" {m} " in padded:
                return self.by_muni[m], "TEXT-MUNICIPALITY"
        for p in self._prov_scan:
            if f" {p} " in padded:
                return self.by_prov[p], "TEXT-PROVINCE"
        return None, None


# --------------------------------------------------------------------------
# ZIP extraction
# --------------------------------------------------------------------------

_TRAILER = re.compile(r"-\s*(\d{4})\s*$")
_PAIR = re.compile(r"^(?:\d{2,4})\s*-\s*(\d{4})$")
_ANY4 = re.compile(r"(?<!\d)(\d{4})(?!\d)")


def extract_zip(address: str) -> str | None:
    """
    Handles the two layouts present in the source file:

      A) '<street>,<brgy>,<ZIP> <CITY>,<NN-ZIP>,PHILIPPINES'
         '<street>,<ZIP> <CITY>-<ZIP>,PHILIPPINES'
         -> the ZIP is the number after the hyphen in the segment before
            'PHILIPPINES'.  The 'NN' prefix is a source/branch code, not
            geographic, so it is ignored.

      B) '<street> <CITY> <PROVINCE> <ZIP>' (no commas, ZIP sometimes doubled)
         -> the ZIP is the last standalone 4-digit token.
    """
    if not address:
        return None
    a = deaccent(str(address)).upper().strip()
    parts = [p.strip() for p in a.split(",")]

    if parts and parts[-1] in ("PHILIPPINES", "PHILIPINES", "PHIL", "PHILS"):
        body = parts[:-1]
        if body:
            m = _TRAILER.search(body[-1]) or _PAIR.match(body[-1])
            if m:
                return m.group(1)

    found = _ANY4.findall(a)
    return found[-1] if found else None


# --------------------------------------------------------------------------
# FINAL AREA modes
# --------------------------------------------------------------------------

FINAL_AREA_MODES = {
    "Island group (NCR / NORTH LUZON / SOUTH LUZON / VISAYAS / MINDANAO)":
        lambda rec: rec.get("ISLAND GROUP", ""),
    "NCR city, else province":
        lambda rec: rec["MUNICIPALITY"] if rec.get("ISLAND GROUP") == "NCR" else rec["PROVINCE"],
    "NCR / PROVINCIAL":
        lambda rec: "NCR" if rec.get("ISLAND GROUP") == "NCR" else "PROVINCIAL",
    "Administrative region (NCR, REGION III, REGION IV-A ...)":
        lambda rec: rec.get("REGION", ""),
    "Province (same as AREA)":
        lambda rec: rec.get("PROVINCE", ""),
}

AREA_MODES = {
    "Province": "PROVINCE",
    "Administrative region": "REGION",
    "Island group": "ISLAND GROUP",
}


# --------------------------------------------------------------------------
# row-level resolution
# --------------------------------------------------------------------------

BLANK = {"ZIP CODE": "", "MUNICIPALITY": "", "PROVINCE": "", "REGION": "", "ISLAND GROUP": ""}


def resolve_row(address, ref: Reference, use_text_fallback: bool = True):
    """Return (record, zip_found, match_source)."""
    if address is None or not str(address).strip():
        return BLANK, "", "NO ADDRESS"

    z = extract_zip(address)

    if z:
        rec = ref.by_zipcode(z)
        if rec:
            return rec, z, "ZIP"

    if use_text_fallback:
        rec, how = ref.scan_text(norm(address))
        if rec:
            out = dict(rec)
            out["ZIP CODE"] = z or rec["ZIP CODE"]
            return out, z or "", how

    if z:
        return dict(BLANK, **{"ZIP CODE": z}), z, "ZIP NOT IN REFERENCE"
    return BLANK, "", "NO ZIP FOUND"


def break_addresses(
    addresses,
    ref: Reference,
    area_mode: str = "Province",
    final_area_mode: str = "Island group (NCR / NORTH LUZON / SOUTH LUZON / VISAYAS / MINDANAO)",
    use_text_fallback: bool = True,
    keep_source_zip: bool = True,
):
    """Vectorised-enough loop with a cache; returns a list of dicts."""
    area_key = AREA_MODES.get(area_mode, "PROVINCE")
    final_fn = FINAL_AREA_MODES.get(
        final_area_mode, FINAL_AREA_MODES["Island group (NCR / NORTH LUZON / SOUTH LUZON / VISAYAS / MINDANAO)"]
    )

    cache: dict[str, dict] = {}
    out = []
    for addr in addresses:
        key = str(addr)
        hit = cache.get(key)
        if hit is None:
            rec, z, src = resolve_row(addr, ref, use_text_fallback)
            hit = {
                "AREA": rec.get(area_key, ""),
                "MUNICIPALITY": rec.get("MUNICIPALITY", ""),
                "FINAL AREA": final_fn(rec) if rec.get("PROVINCE") else "",
                "ZIP CODE": (z if keep_source_zip and z else rec.get("ZIP CODE", "")),
                "MATCH SOURCE": src,
            }
            cache[key] = hit
        out.append(hit)
    return out
