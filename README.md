# Area Break

Turns a free-text `ADDRESS` column into **AREA / MUNICIPALITY / FINAL AREA / ZIP CODE**.

The interface is React + Tailwind CSS with Lucide icons, running inside Streamlit as a
custom component. It ships **pre-built** in `frontend/dist`, so you only need Python
to run it. Fonts and icons are bundled too — nothing is fetched from the internet, so it
works on an office network with outside sites blocked.

## Run

```bash
pip install -r requirements.txt
streamlit run area_break_app.py
```

Keep the folder together: the app needs `area_engine.py`, `ph_zip_reference.csv`,
`favicon.png`, `.streamlit/config.toml` and `frontend/dist/` beside it.
(`.streamlit` starts with a dot, so Windows Explorer may hide it — it raises the
upload size limit and should stay.)

## Folder

| Path | What it is |
|---|---|
| `area_break_app.py` | Streamlit back end — receives events from the page, runs the engine, sends results back |
| `area_engine.py` | Address parsing and ZIP lookup (usable on its own in batch scripts) |
| `ph_zip_reference.csv` | ZIP → municipality / province / region / island group, 2,055 ZIPs |
| `frontend/src/` | React source (`App.jsx`, `Source.jsx`, `Rules.jsx`, `Results.jsx`, `ui.jsx`) |
| `frontend/dist/` | The built page Streamlit serves — this is what runs |

## Using it

1. Drop the file (XLSX, XLS or CSV). The address column is picked automatically —
   check the three sample addresses shown, and change the column if they look wrong.
2. Set **Output rules** (right rail on desktop, collapsed panel on a phone).
3. **Break addresses.** You get the resolution rate, the FINAL AREA split, how every
   row was matched, AREA counts, and a searchable, paged row view.
4. **Excel** or **CSV** downloads every row. The Excel file has a second sheet,
   `NEEDS REVIEW`, with every row not matched by ZIP.

Changing a rule after a run shows a banner — results only change when you run again.
Uploading a custom reference CSV re-runs automatically.

### How a row is resolved

1. **ZIP is pulled from the address.** `...,3315 CABATUAN ISABELA,09-3315,PHILIPPINES`
   → the number after the hyphen (the `09` is a branch code, not geographic).
   No-comma addresses → the last standalone 4-digit number.
2. **ZIP lookup** in `ph_zip_reference.csv`.
3. **Fallback** (switchable): if the ZIP is missing or unknown, look for a municipality
   name in the text, then a province name.

Every row gets a `MATCH SOURCE`:

| Value | Meaning |
|---|---|
| `ZIP` | ZIP found and matched |
| `TEXT-MUNICIPALITY` | no usable ZIP; a municipality name was found |
| `TEXT-PROVINCE` | only a province was found — MUNICIPALITY is left blank |
| `ZIP NOT IN REFERENCE` | add the ZIP to the CSV and run again |
| `NO ZIP FOUND` | no ZIP and no place name |
| `NO ADDRESS` | blank cell |

## Changing the interface

Only needed if you edit the React code. Requires Node 18+.

```bash
cd frontend
npm install
npm run build          # rebuilds frontend/dist — then just restart Streamlit
```

For live reload while editing:

```bash
cd frontend && npm run dev                       # serves on :5173
# in a second terminal (Windows):
set AREA_BREAK_DEV=http://localhost:5173
streamlit run area_break_app.py
```

Theme colours live as CSS variables at the top of `frontend/src/index.css`; light and
dark mode follow the Windows/OS setting.

## Reference table

Plain CSV: `ZIP CODE, MUNICIPALITY, PROVINCE, REGION, ISLAND GROUP`. Add a row and
re-run, or upload a replacement from the Output rules panel.

Built from the open `nadarei/philippines` ZIP dataset (MIT), with four upstream
defects repaired where a missing province key had merged one province's towns into
another (Bulacan → Bukidnon, Albay → Aklan, Marinduque → Maguindanao, Parañaque →
Navotas). Zamboanga del Sur, Surigao del Sur and Davao Occidental carry their major
cities only.
