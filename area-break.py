"""
Philippine Address Parser - Streamlit App
-------------------------------------------
Parses freeform Philippine addresses into structured columns:
[Block and Lot Number] [House Number] [Street Name] [Subdivision Name]
[Barangay Name] [City or Municipality] [Province] [Zip Code]

Run with:
    pip install -r requirements.txt
    streamlit run address_parser_app.py
"""

import re
import io
import html as _html
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# --------------------------------------------------------------------------
# REFERENCE LISTS
# Extend these lists any time to improve matching accuracy for your dataset.
# --------------------------------------------------------------------------

PROVINCES = [
    "ABRA", "AGUSAN DEL NORTE", "AGUSAN DEL SUR", "AKLAN", "ALBAY",
    "ANTIQUE", "APAYAO", "AURORA", "BASILAN", "BATAAN", "BATANES",
    "BATANGAS", "BENGUET", "BILIRAN", "BOHOL", "BUKIDNON", "BULACAN",
    "CAGAYAN", "CAMARINES NORTE", "CAMARINES SUR", "CAMIGUIN", "CAPIZ",
    "CATANDUANES", "CAVITE", "CEBU", "COTABATO", "DAVAO DE ORO",
    "DAVAO DEL NORTE", "DAVAO DEL SUR", "DAVAO OCCIDENTAL",
    "DAVAO ORIENTAL", "DINAGAT ISLANDS", "EASTERN SAMAR", "GUIMARAS",
    "IFUGAO", "ILOCOS NORTE", "ILOCOS SUR", "ILOILO", "ISABELA",
    "KALINGA", "LA UNION", "LAGUNA", "LANAO DEL NORTE", "LANAO DEL SUR",
    "LEYTE", "MAGUINDANAO DEL NORTE", "MAGUINDANAO DEL SUR", "MARINDUQUE",
    "MASBATE", "MISAMIS OCCIDENTAL", "MISAMIS ORIENTAL", "MOUNTAIN PROVINCE",
    "NEGROS OCCIDENTAL", "NEGROS ORIENTAL", "NORTHERN SAMAR",
    "NUEVA ECIJA", "NUEVA VIZCAYA", "OCCIDENTAL MINDORO",
    "ORIENTAL MINDORO", "PALAWAN", "PAMPANGA", "PANGASINAN", "QUEZON",
    "QUIRINO", "RIZAL", "ROMBLON", "SAMAR", "SARANGANI", "SIQUIJOR",
    "SORSOGON", "SOUTH COTABATO", "SOUTHERN LEYTE", "SULTAN KUDARAT",
    "SULU", "SURIGAO DEL NORTE", "SURIGAO DEL SUR", "TARLAC",
    "TAWI-TAWI", "ZAMBALES", "ZAMBOANGA DEL NORTE", "ZAMBOANGA DEL SUR",
    "ZAMBOANGA SIBUGAY", "METRO MANILA", "NCR",
]
# Sort longest-first so multi-word provinces match before shorter substrings
PROVINCES = sorted(set(PROVINCES), key=len, reverse=True)

CITIES = [
    # Metro Manila
    "MANILA", "QUEZON CITY", "CALOOCAN", "LAS PINAS", "LAS PIÑAS",
    "MAKATI", "MALABON", "MANDALUYONG", "MARIKINA", "MUNTINLUPA",
    "NAVOTAS", "PARANAQUE", "PARAÑAQUE", "PASAY", "PASIG", "PATEROS",
    "SAN JUAN", "TAGUIG", "VALENZUELA",
    # Rizal towns
    "ANTIPOLO", "ANGONO", "BARAS", "BINANGONAN", "CAINTA", "CARDONA",
    "JALA-JALA", "MORONG", "PILILLA", "RODRIGUEZ", "SAN MATEO",
    "TAYTAY", "TERESA", "MONTALBAN",
    # Other common cities
    "CEBU CITY", "DAVAO CITY", "BACOLOD", "ILOILO CITY", "CAGAYAN DE ORO",
    "ZAMBOANGA CITY", "BAGUIO", "ANGELES CITY", "OLONGAPO", "LIPA",
    "BATANGAS CITY", "LUCENA", "NAGA", "LEGAZPI", "TACLOBAN",
    "GENERAL SANTOS", "BUTUAN", "DAGUPAN", "SANTA ROSA", "BINAN", "BIÑAN",
    "SAN JOSE", "SAN FERNANDO", "SAN PABLO", "SAN CARLOS", "TARLAC",
    "COTABATO", "GENERAL TRIAS", "MEYCAUAYAN", "MALOLOS", "IMUS", "BACOOR",
    "DASMARINAS", "DASMARIÑAS", "CABANATUAN", "TUGUEGARAO", "PUERTO PRINCESA",
]
CITIES = sorted(set(CITIES), key=len, reverse=True)

STREET_KEYWORDS = r"(ST\.?|STREET|AVE\.?|AVENUE|RD\.?|ROAD|BLVD\.?|BOULEVARD|DRIVE|DR\.?|EXTENSION|EXT\.?)"


def _strip(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip(" ,.-")


def parse_address(address: str) -> dict:
    """Heuristically parse a single Area Break string into fields."""
    result = {
        "Block and Lot Number": "",
        "House Number": "",
        "Street Name": "",
        "Subdivision Name": "",
        "Barangay Name": "",
        "City or Municipality": "",
        "Province": "",
        "Zip Code": "",
    }

    if not isinstance(address, str) or not address.strip():
        return result

    addr = " " + address.upper().replace(",", " , ") + " "
    addr = re.sub(r"\s+", " ", addr)

    # 1. ZIP CODE - take the LAST standalone 4-digit number, then remove
    #    every standalone 4-digit number so duplicates don't leak elsewhere.
    zip_matches = re.findall(r"\b\d{4}\b", addr)
    if zip_matches:
        result["Zip Code"] = zip_matches[-1]
        for z in set(zip_matches):
            addr = re.sub(r"\b" + re.escape(z) + r"\b", " ", addr)

    # 2. BLOCK AND LOT NUMBER
    blk_lot_pattern = (
        r"\b(BLK\.?|BLOCK)\s*\.?\s*[\w-]+\s*,?\s*(LOT|LT)\.?\s*[\w-]+"
        r"|\b(LOT|LT)\.?\s*[\w-]+\s*,?\s*(BLK\.?|BLOCK)\s*[\w-]+"
    )
    m = re.search(blk_lot_pattern, addr)
    if m:
        result["Block and Lot Number"] = _strip(m.group(0)).title().replace("Blk", "BLK").replace("Lot", "LOT").replace("Lt", "LOT").replace("Block","BLK")
        addr = addr.replace(m.group(0), " ")

    # 3. CITY / MUNICIPALITY - check known list first (allowing an optional
    #    trailing "CITY" word, e.g. "Lipa" + "City", "Valenzuela" + "City").
    #    Doing this BEFORE province matching means a province-like word
    #    (e.g. "Quezon") isn't wrongly grabbed as the province when it's
    #    really part of a city name like "Quezon City".
    for city in CITIES:
        pattern = r"\b" + re.escape(city) + r"\b(?:\s+CITY\b)?"
        m = re.search(pattern, addr)
        if m:
            result["City or Municipality"] = _strip(m.group(0)).title()
            addr = addr.replace(m.group(0), " ")
            break

    # 3b. Fallback: a single unlisted word directly followed by "CITY"
    #     (e.g. "Meycauayan City" if not already in the list above).
    if not result["City or Municipality"]:
        m = re.search(r"\b([A-Z]+)\s+CITY\b", addr)
        if m:
            result["City or Municipality"] = _strip(m.group(0)).title()
            addr = addr.replace(m.group(0), " ")

    # 4. PROVINCE (match longest known province first) - do this before
    #    Barangay so a greedy barangay match can't swallow city/province.
    for prov in PROVINCES:
        pattern = r"\b" + re.escape(prov) + r"\b"
        if re.search(pattern, addr):
            result["Province"] = prov.title()
            addr = re.sub(pattern, " ", addr)
            break

    # 5. BARANGAY - capture up to 4 words after the BRGY/BARANGAY keyword
    #    (bounded, not greedy to end-of-string) so it doesn't eat later fields.
    brgy_pattern = r"\b(BRGY\.?|BARANGAY)\s+((?:[A-Z0-9ÑÁÉÍÓÚ.-]+\s*){1,4}?)(?=,|$|\d{4}\b)"
    m = re.search(brgy_pattern, addr)
    if m:
        result["Barangay Name"] = _strip(m.group(2)).title()
        addr = addr.replace(m.group(0), " ")

    # 7. STREET NAME - phrase ending in a street-type keyword
    street_pattern = r"([A-Z0-9ÑÁÉÍÓÚ.\s]{0,30}\b" + STREET_KEYWORDS + r"\b)"
    m = re.search(street_pattern, addr)
    if m:
        result["Street Name"] = _strip(m.group(0)).title()
        addr = addr.replace(m.group(0), " ")

    # 8. Clean leftovers -> split into House Number (if any) + Subdivision Name
    addr = _strip(addr.replace(",", " "))
    if addr:
        hn_match = re.match(r"^#?\s*(\d+[A-Z]?)\s+(.*)$", addr)
        if hn_match:
            result["House Number"] = hn_match.group(1)
            addr = hn_match.group(2)
        result["Subdivision Name"] = _strip(addr).title()

    return result


# --------------------------------------------------------------------------
# STREAMLIT UI  —  dark-mode theme, custom CSS + a small JS-animated header
# --------------------------------------------------------------------------

st.set_page_config(page_title="DIY Area Break", page_icon="🏠", layout="wide")

# ---- Global dark-mode CSS (not pure black — soft charcoal, like real dark mode) ----
st.markdown(
    """
    <style>
    :root{
        --bg:            #121214;
        --bg-elevated:   #1B1B1F;
        --bg-card:       #1E1E23;
        --border:        #2B2B31;
        --text:          #E9E9EC;
        --text-dim:      #9A9AA4;
        --accent:        #7C5CFF;
        --accent-soft:   rgba(124, 92, 255, 0.15);
        --success:       #38D39F;
    }

    .stApp{
        background: radial-gradient(circle at 20% -10%, #1a1a2e 0%, var(--bg) 45%) fixed;
        color: var(--text);
    }

    /* Hide default Streamlit chrome for a cleaner app feel */
    #MainMenu, footer, header{ visibility: hidden; }

    /* Minimalist centered width instead of full-bleed wide layout */
    div[data-testid="stAppViewContainer"] .main .block-container{
        max-width: 880px;
        margin: 0 auto;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* Cards / containers */
    div[data-testid="stExpander"]{
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 14px;
    }
    div[data-testid="stFileUploader"]{
        background: var(--bg-card);
        border: 1px dashed var(--border);
        border-radius: 14px;
        padding: 0.6rem;
    }
    div[data-testid="stFileUploader"] section{
        background: transparent;
    }
    /* The little uploaded-file chip Streamlit renders (was showing white/light) */
    div[data-testid="stFileUploaderFile"],
    div[data-testid="stFileUploader"] li,
    div[data-testid="stFileUploader"] div[class*="uploadedFile"]{
        background: var(--bg-elevated) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        color: var(--text) !important;
    }
    div[data-testid="stFileUploader"] span,
    div[data-testid="stFileUploader"] small,
    div[data-testid="stFileUploaderFile"] *{
        color: var(--text) !important;
    }
    div[data-testid="stFileUploader"] button{
        background: transparent !important;
        border: 1px solid var(--border) !important;
        color: var(--text-dim) !important;
    }

    /* Tabs -> pill style */
    div[data-testid="stTabs"] button{
        border-radius: 999px !important;
        margin-right: 6px;
        color: var(--text-dim);
        background: var(--bg-elevated);
        border: 1px solid var(--border) !important;
        padding: 6px 18px;
        transition: all 0.2s ease;
    }
    div[data-testid="stTabs"] button[aria-selected="true"]{
        background: var(--accent-soft);
        color: var(--accent) !important;
        border-color: var(--accent) !important;
    }
    div[data-testid="stTabs"] div[data-baseweb="tab-highlight"]{
        display:none;
    }

    /* Buttons */
    .stButton button, .stDownloadButton button{
        border-radius: 10px;
        border: 1px solid var(--border);
        background: linear-gradient(135deg, #7C5CFF, #5A3FD6);
        color: white;
        font-weight: 600;
        padding: 0.5rem 1.1rem;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
        box-shadow: 0 0 0 rgba(124,92,255,0);
    }
    .stButton button:hover, .stDownloadButton button:hover{
        transform: translateY(-1px);
        box-shadow: 0 6px 18px rgba(124,92,255,0.35);
    }

    /* Metric cards */
    div[data-testid="stMetric"]{
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 12px 14px;
    }
    div[data-testid="stMetricLabel"]{ color: var(--text-dim); }
    div[data-testid="stMetricValue"]{ color: var(--accent); }

    /* Native st.dataframe / st.data_editor (kept for the optional edit view) */
    div[data-testid="stDataFrame"], div[data-testid="stDataEditor"]{
        border: 1px solid var(--border);
        border-radius: 12px;
        overflow: hidden;
    }

    /* Custom dark HTML table (used for previews/results so colors never break) */
    .dark-table-wrap{
        border: 1px solid var(--border);
        border-radius: 12px;
        overflow: auto;
        max-height: 480px;
    }
    table.dark-table{
        width: 100%;
        border-collapse: collapse;
        font-size: 13.5px;
    }
    table.dark-table thead th{
        position: sticky; top: 0;
        background: var(--bg-elevated);
        color: var(--text-dim);
        text-align: left;
        padding: 10px 12px;
        font-weight: 600;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        border-bottom: 1px solid var(--border);
        white-space: nowrap;
    }
    table.dark-table tbody td{
        padding: 9px 12px;
        border-bottom: 1px solid var(--border);
        color: var(--text);
        white-space: nowrap;
    }
    table.dark-table tbody tr:hover{ background: var(--bg-elevated); }
    table.dark-table tbody tr:last-child td{ border-bottom: none; }

    /* Progress bar */
    div[data-testid="stProgress"] > div > div{
        background-color: var(--accent) !important;
    }
    div[data-testid="stProgress"] > div{
        background-color: var(--bg-elevated) !important;
    }

    /* Text areas / inputs */
    textarea, input, div[data-baseweb="select"] > div{
        background: var(--bg-elevated) !important;
        color: var(--text) !important;
        border-radius: 10px !important;
        border: 1px solid var(--border) !important;
    }

    /* Success / info boxes */
    div[data-testid="stAlert"]{
        border-radius: 12px;
        border: 1px solid var(--border);
    }

    .app-caption{
        color: var(--text-dim);
        font-size: 0.95rem;
        margin-top: -6px;
        margin-bottom: 1.2rem;
    }
    </style>

    """,
    unsafe_allow_html=True,
)

# ---- JS-animated hero header (canvas particles + gradient title) ----
components.html(
    """
    <div id="hero" style="
        position: relative;
        border-radius: 16px;
        overflow: hidden;
        padding: 26px 28px;
        background: linear-gradient(135deg, #1a1a2e 0%, #16161a 100%);
        border: 1px solid #2B2B31;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    ">
        <canvas id="particles" style="position:absolute; inset:0; width:100%; height:100%;"></canvas>
        <div style="position:relative; z-index:2;">
            <h1 style="
                margin:0; font-size: 30px; font-weight: 800;
                background: linear-gradient(90deg, #B9A6FF, #7C5CFF 55%, #38D39F);
                -webkit-background-clip: text; background-clip: text; color: transparent;
            ">🏠 DIY Area Break</h1>
            <p style="margin: 6px 0 0 0; color:#9A9AA4; font-size: 14px;">
                Splits a full address into Block/Lot, House Number, Street Name,
                Subdivision Name, Barangay, City/Municipality, Province, and Zip Code.
            </p>
        </div>
    </div>
    <script>
        const canvas = document.getElementById('particles');
        const ctx = canvas.getContext('2d');
        const hero = document.getElementById('hero');

        function resize() {
            canvas.width = hero.offsetWidth;
            canvas.height = hero.offsetHeight;
        }
        resize();
        window.addEventListener('resize', resize);

        const N = 36;
        const dots = Array.from({length: N}, () => ({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            vx: (Math.random() - 0.5) * 0.3,
            vy: (Math.random() - 0.5) * 0.3,
            r: Math.random() * 1.6 + 0.6,
        }));

        function tick() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            for (const d of dots) {
                d.x += d.vx; d.y += d.vy;
                if (d.x < 0 || d.x > canvas.width) d.vx *= -1;
                if (d.y < 0 || d.y > canvas.height) d.vy *= -1;
                ctx.beginPath();
                ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(124, 92, 255, 0.55)';
                ctx.fill();
            }
            // faint connecting lines
            for (let i = 0; i < N; i++) {
                for (let j = i + 1; j < N; j++) {
                    const a = dots[i], b = dots[j];
                    const dist = Math.hypot(a.x - b.x, a.y - b.y);
                    if (dist < 90) {
                        ctx.beginPath();
                        ctx.moveTo(a.x, a.y);
                        ctx.lineTo(b.x, b.y);
                        ctx.strokeStyle = 'rgba(124, 92, 255, ' + (0.12 * (1 - dist / 90)) + ')';
                        ctx.stroke();
                    }
                }
            }
            requestAnimationFrame(tick);
        }
        tick();
    </script>
    """,
    height=120,
)

with st.expander("ℹ️ How this works / limitations", expanded=False):
    st.markdown(
        """
        - Parsing is **rule-based** (regex + known province/city lists), not AI-based,
          so it works instantly and offline — but unusual formats may need manual fixes.
        - You can edit any result directly in the table before downloading.
        - Want better accuracy for your own dataset? Add your common city/subdivision
          names to the `PROVINCES` / `CITIES` lists at the top of this script.
        """
    )

def render_dark_table(df: pd.DataFrame, max_rows: int = 300):
    """Render a DataFrame as a custom dark-themed HTML table so styling
    never depends on Streamlit's own (sometimes light) component theming."""
    display_df = df.head(max_rows)
    header_html = "".join(f"<th>{_html.escape(str(c))}</th>" for c in display_df.columns)
    body_rows = []
    for _, row in display_df.iterrows():
        cells = "".join(
            f"<td>{'' if pd.isna(v) else _html.escape(str(v))}</td>" for v in row
        )
        body_rows.append(f"<tr>{cells}</tr>")
    table_html = f"""
    <div class="dark-table-wrap">
      <table class="dark-table">
        <thead><tr>{header_html}</tr></thead>
        <tbody>{''.join(body_rows)}</tbody>
      </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)
    if len(df) > max_rows:
        st.caption(f"Showing first {max_rows} of {len(df)} rows.")


tab1, tab2 = st.tabs(["🔤 Single Address", "📄 Bulk Upload (CSV/Excel)"])

# ---------------- TAB 1: Single address tester ----------------
with tab1:
    default_example = "Enter Address"
    address_input = st.text_area("Paste an address:", value=default_example, height=80)

    if st.button("✨ Parse Address", type="primary"):
        parsed = parse_address(address_input)
        render_dark_table(pd.DataFrame([parsed]))

        cols = st.columns(4)
        labels = list(parsed.keys())
        for i, label in enumerate(labels):
            with cols[i % 4]:
                st.metric(label, parsed[label] if parsed[label] else "—")

# ---------------- TAB 2: Bulk upload ----------------
with tab2:
    uploaded_file = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx", "xls"])

    if uploaded_file is not None:
        try:
            if uploaded_file.name.lower().endswith(".csv"):
                raw_df = pd.read_csv(uploaded_file)
            else:
                raw_df = pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"Could not read file: {e}")
            raw_df = None

        if raw_df is not None:
            st.write("Preview of uploaded data:")
            render_dark_table(raw_df.head())

            address_col = st.selectbox(
                "Which column contains the full address?", raw_df.columns.tolist()
            )

            if st.button("⚡ Parse All Addresses", type="primary"):
                total = len(raw_df)
                progress_bar = st.progress(0, text="Starting…")
                parsed_list = []
                addresses = raw_df[address_col].tolist()
                for i, addr in enumerate(addresses):
                    parsed_list.append(parse_address(addr))
                    pct = int(((i + 1) / total) * 100)
                    progress_bar.progress(
                        pct, text=f"Parsing address {i + 1} of {total}…"
                    )
                progress_bar.progress(100, text="Done!")
                progress_bar.empty()

                parsed_rows = pd.DataFrame(parsed_list)
                result_df = pd.concat(
                    [raw_df.reset_index(drop=True), parsed_rows], axis=1
                )

                st.success(f"Parsed {len(result_df)} address(es).")
                render_dark_table(result_df)

                with st.expander("✏️ Edit results (optional)", expanded=False):
                    edited_df = st.data_editor(
                        result_df, use_container_width=True, num_rows="dynamic"
                    )

                csv_buffer = io.StringIO()
                edited_df.to_csv(csv_buffer, index=False)
                st.download_button(
                    "⬇️ Download Results as CSV",
                    data=csv_buffer.getvalue(),
                    file_name="parsed_addresses.csv",
                    mime="text/csv",
                )

                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                    edited_df.to_excel(writer, index=False, sheet_name="Parsed Addresses")
                st.download_button(
                    "⬇️ Download Results as Excel",
                    data=excel_buffer.getvalue(),
                    file_name="parsed_addresses.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )