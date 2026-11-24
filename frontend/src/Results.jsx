import { useMemo, useState } from "react";
import {
  FileDown,
  Sheet,
  Split,
  ListChecks,
  BarChart3,
  Table2,
  Search,
  RotateCcw,
  TriangleAlert,
  LoaderCircle,
  Inbox,
  ChevronDown,
  Gauge,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Card, CardHeader, Button, Badge, Select, Zip, cx, fmt } from "./ui.jsx";
import { sourceMeta, ISLAND_ORDER, SLOTS, SLOT_INK } from "./meta.js";

const share = (n, total) => (total ? n / total : 0);
const sharePct = (s) =>
  s === 0 ? "0%" : s < 0.001 ? "<0.1%" : s >= 0.1 ? `${Math.round(s * 100)}%` : `${(s * 100).toFixed(1)}%`;

/* ======================================================================== */
/* Headline                                                                  */
/* ======================================================================== */

function Hero({ result, stale, onRun, running, onExport, busy }) {
  const rateText =
    result.rate >= 1 ? "100%" : `${(Math.floor(result.rate * 10000) / 100).toFixed(2)}%`;
  const by = Object.fromEntries(result.sources.map((s) => [s.key, s.rows]));
  const nameMatched = (by["TEXT-MUNICIPALITY"] ?? 0) + (by["TEXT-PROVINCE"] ?? 0);

  const tiles = [
    ["ZIP match", fmt(by.ZIP ?? 0)],
    ["Name match", fmt(nameMatched)],
    ["Needs review", fmt(result.review)],
    ["Unresolved", result.unresolved ? fmt(result.unresolved) : "None"],
  ];

  return (
    <Card>
      <CardHeader
        icon={Gauge}
        title="Results"
        meta={`${fmt(result.rows)} rows · ${result.elapsed.toFixed(1)}s`}
        action={
          <>
            <Button size="sm" variant="primary" icon={FileDown} busy={busy.xlsx} onClick={() => onExport("xlsx")}>
              {busy.xlsx ? "Building…" : "Excel"}
            </Button>
            <Button size="sm" icon={Sheet} busy={busy.csv} onClick={() => onExport("csv")}>
              CSV
            </Button>
          </>
        }
      />
      {stale && (
        <div className="flex flex-col gap-3 border-b border-line bg-warn-soft px-4 py-3 sm:flex-row sm:items-center sm:px-6">
          <p className="flex items-center gap-2 text-sm text-warn">
            <TriangleAlert className="size-4 shrink-0" aria-hidden />
            Output rules changed since this run.
          </p>
          <Button size="sm" variant="secondary" icon={RotateCcw} busy={running} onClick={onRun} className="sm:ml-auto">
            Run again
          </Button>
        </div>
      )}
      <div className="flex flex-col gap-6 p-4 sm:p-6 lg:flex-row lg:items-end">
        <div className="lg:w-72">
          <p className="text-sm text-ink-2">Resolved to a province</p>
          <p className="mt-1 text-5xl font-semibold tracking-tight sm:text-6xl">{rateText}</p>
          <p className="tabular mt-1 text-sm text-ink-3">
            {fmt(result.resolved)} of {fmt(result.rows)} rows
          </p>
          <div
            className="mt-3 h-2 overflow-hidden rounded-full bg-bar-track"
            role="meter"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(result.rate * 100)}
            aria-label="Share of rows resolved"
          >
            <div className="h-full rounded-full bg-good" style={{ width: `${result.rate * 100}%` }} />
          </div>
        </div>

        <dl className="grid flex-1 grid-cols-2 gap-4 border-line sm:grid-cols-4 lg:border-l lg:pl-6">
          {tiles.map(([label, value]) => (
            <div key={label} className="rounded-lg bg-sunken px-3 py-2.5">
              <dt className="truncate text-xs text-ink-3">{label}</dt>
              <dd className="mt-0.5 text-xl font-semibold">{value}</dd>
            </div>
          ))}
        </dl>
      </div>
    </Card>
  );
}

/* ======================================================================== */
/* FINAL AREA - one whole split into parts (tall segmented bar + legend)     */
/* ======================================================================== */

function buildSegments(result) {
  const total = result.rows;
  const named = result.final.filter((f) => f.label);
  const none = result.final.find((f) => !f.label);
  let segs;

  if (result.islandMode) {
    segs = ISLAND_ORDER.map((label, i) => ({
      label,
      rows: named.find((f) => f.label === label)?.rows ?? 0,
      color: SLOTS[i],
      ink: SLOT_INK[i],
    }));
  } else {
    const sorted = [...named].sort((a, b) => b.rows - a.rows);
    segs = sorted.slice(0, 5).map((f, i) => ({ ...f, color: SLOTS[i], ink: SLOT_INK[i] }));
    const rest = sorted.slice(5);
    if (rest.length) {
      segs.push({
        label: `Other (${rest.length})`,
        rows: rest.reduce((a, f) => a + f.rows, 0),
        color: "var(--s-other)",
        ink: "#0f1b2d",
      });
    }
  }
  if (none?.rows) segs.push({ label: "Unresolved", rows: none.rows, color: "var(--s-none)", ink: "var(--ink)" });
  return segs.filter((s) => s.rows > 0).map((s) => ({ ...s, share: share(s.rows, total) }));
}

function FinalArea({ result }) {
  const segs = useMemo(() => buildSegments(result), [result]);
  const [hover, setHover] = useState(null);

  // centre of each block, for tooltip placement
  let acc = 0;
  const centres = segs.map((s) => {
    const c = acc + s.share / 2;
    acc += s.share;
    return c;
  });

  return (
    <Card>
      <CardHeader icon={Split} title="Final area" meta={result.finalModeLabel} />
      <div className="p-4 sm:p-5">
        <div className="relative">
          <div
            className="flex h-7 gap-0.5"
            role="img"
            aria-label={segs.map((s) => `${s.label} ${fmt(s.rows)} rows, ${sharePct(s.share)}`).join("; ")}
          >
            {segs.map((s, i) => (
              <div
                key={s.label}
                tabIndex={0}
                onMouseEnter={() => setHover(i)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(i)}
                onBlur={() => setHover(null)}
                className={cx(
                  "flex min-w-[3px] items-center overflow-hidden rounded text-xs font-semibold transition-opacity outline-offset-1",
                  s.share >= 0.07 && "px-2",
                  hover !== null && hover !== i && "opacity-60",
                )}
                style={{ flexGrow: s.rows, flexBasis: 0, background: s.color, color: s.ink }}
              >
                {s.share >= 0.07 && <span className="tabular truncate">{sharePct(s.share)}</span>}
              </div>
            ))}
          </div>
          {hover !== null && (
            <div
              className="pointer-events-none absolute bottom-full z-10 mb-2 -translate-x-1/2 rounded-lg bg-primary px-3 py-2 text-xs whitespace-nowrap text-on-primary shadow-lg"
              style={{ left: `clamp(70px, ${centres[hover] * 100}%, calc(100% - 70px))` }}
            >
              <p className="font-semibold">{segs[hover].label}</p>
              <p className="tabular opacity-80">
                {fmt(segs[hover].rows)} rows · {sharePct(segs[hover].share)}
              </p>
            </div>
          )}
        </div>

        <ul className="mt-4">
          {segs.map((s, i) => (
            <li
              key={s.label}
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
              className="flex items-center gap-2.5 border-b border-line py-2 text-sm last:border-b-0"
            >
              <span className="size-2.5 shrink-0 rounded-sm" style={{ background: s.color }} aria-hidden />
              <span className="min-w-0 flex-1 truncate">{s.label}</span>
              <span className="tabular text-ink-2">{fmt(s.rows)}</span>
              <span className="tabular w-12 text-right text-ink-3">{sharePct(s.share)}</span>
            </li>
          ))}
        </ul>
      </div>
    </Card>
  );
}

/* ======================================================================== */
/* How rows were matched                                                     */
/* ======================================================================== */

const TONE_ICON = {
  good: "bg-good-soft text-good",
  info: "bg-info-soft text-info",
  warn: "bg-warn-soft text-warn",
  bad: "bg-bad-soft text-bad",
  neutral: "bg-sunken text-ink-2",
};

function Sources({ result, onPick }) {
  const rows = [...result.sources].sort((a, b) => b.rows - a.rows);
  return (
    <Card>
      <CardHeader icon={ListChecks} title="How rows were matched" />
      <ul className="divide-y divide-line">
        {rows.map((s) => {
          const m = sourceMeta(s.key);
          const Icon = m.icon;
          const clickable = s.key !== "ZIP";
          const body = (
            <>
              <span className={cx("grid size-8 shrink-0 place-items-center rounded-full", TONE_ICON[m.tone])}>
                <Icon className="size-4" aria-hidden />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-medium">{m.label}</span>
                <span className="block text-xs text-ink-3">{m.hint}</span>
              </span>
              <span className="tabular text-sm font-semibold">{fmt(s.rows)}</span>
            </>
          );
          return (
            <li key={s.key}>
              {clickable ? (
                <button
                  type="button"
                  onClick={() => onPick(s.key)}
                  className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-sunken sm:px-5"
                  title="Show these rows"
                >
                  {body}
                </button>
              ) : (
                <div className="flex items-center gap-3 px-4 py-3 sm:px-5">{body}</div>
              )}
            </li>
          );
        })}
      </ul>
      {result.missingZips.length > 0 && (
        <div className="border-t border-line px-4 py-3 sm:px-5">
          <p className="text-xs font-semibold tracking-wide text-ink-2 uppercase">ZIPs to add to the reference</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {result.missingZips.map((z) => (
              <span key={z.zip} className="rounded-md bg-sunken px-2 py-1 text-xs">
                <Zip>{z.zip}</Zip>
                <span className="tabular ml-1.5 text-ink-3">×{fmt(z.rows)}</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

/* ======================================================================== */
/* AREA - ranked bars, one series                                            */
/* ======================================================================== */

function AreaBars({ result }) {
  const [all, setAll] = useState(false);
  const items = result.area.filter((a) => a.label).sort((a, b) => b.rows - a.rows);
  const shown = all ? items : items.slice(0, 10);
  const max = items[0]?.rows || 1;

  return (
    <Card>
      <CardHeader icon={BarChart3} title="Area" meta={`${result.areaModeLabel} · ${items.length}`} />
      <ul className="px-4 py-3 sm:px-5">
        {shown.map((a) => (
          <li key={a.label} className="group grid grid-cols-[minmax(0,8.5rem)_1fr_auto] items-center gap-3 py-1.5 sm:grid-cols-[minmax(0,11rem)_1fr_auto]">
            <span className="truncate text-sm" title={a.label}>
              {a.label}
            </span>
            <span className="h-2.5 overflow-hidden rounded-r bg-bar-track">
              <span
                className="block h-full rounded-r transition-opacity group-hover:opacity-80"
                style={{ width: `${Math.max(0.6, (a.rows / max) * 100)}%`, background: "var(--bar)" }}
              />
            </span>
            <span className="tabular min-w-14 text-right text-sm text-ink-2">
              <span className="group-hover:hidden">{fmt(a.rows)}</span>
              <span className="hidden text-ink group-hover:inline">{sharePct(share(a.rows, result.rows))}</span>
            </span>
          </li>
        ))}
      </ul>
      {items.length > 10 && (
        <div className="border-t border-line px-4 py-2 sm:px-5">
          <Button size="sm" variant="ghost" icon={ChevronDown} onClick={() => setAll((v) => !v)}>
            {all ? "Show top 10" : `Show all ${items.length}`}
          </Button>
        </div>
      )}
    </Card>
  );
}

/* ======================================================================== */
/* Rows                                                                      */
/* ======================================================================== */

function Cell({ col, value, table }) {
  if (col === "ZIP CODE") return <Zip>{value}</Zip>;
  if (col === "MATCH SOURCE") {
    const m = sourceMeta(value);
    return (
      <Badge tone={m.tone} icon={m.icon}>
        {m.label}
      </Badge>
    );
  }
  if (col === table.addrCol)
    return (
      <span className="line-clamp-2 font-mono text-[12px] leading-snug text-ink-2" title={value}>
        {value || "—"}
      </span>
    );
  if (col === table.idCol) return <span className="font-mono text-[12px] whitespace-nowrap">{value}</span>;
  return value ? <span className="whitespace-nowrap">{value}</span> : <span className="text-ink-3">—</span>;
}

function Rows({ result, table, query, setQuery, loading }) {
  const cols = table.columns;
  const outputCols = cols.filter((c) => c !== table.idCol && c !== table.addrCol && c !== "MATCH SOURCE");
  const finals = result.final.filter((f) => f.label).map((f) => f.label);
  const tabs = [
    { value: "all", label: "All rows", count: result.rows },
    { value: "review", label: "Needs review", count: result.review },
  ];

  return (
    <Card id="rows">
      <CardHeader icon={Table2} title="Rows" />
      <div className="space-y-3 border-b border-line p-4 sm:px-5">
        <div role="tablist" aria-label="Row set" className="flex gap-1 rounded-lg bg-sunken p-1 sm:inline-flex">
          {tabs.map((t) => (
            <button
              key={t.value}
              role="tab"
              type="button"
              aria-selected={query.view === t.value}
              onClick={() => setQuery({ ...query, view: t.value, source: "", page: 0 })}
              className={cx(
                "flex flex-1 items-center justify-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors sm:flex-none",
                query.view === t.value ? "bg-surface text-ink shadow-sm ring-1 ring-line" : "text-ink-2 hover:text-ink",
              )}
            >
              {t.label}
              <span className="tabular rounded bg-sunken px-1.5 text-xs text-ink-3">{fmt(t.count)}</span>
            </button>
          ))}
        </div>
        <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_12rem_12rem]">
          <div className="relative">
            <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-ink-3" aria-hidden />
            <input
              type="search"
              value={query.q}
              onChange={(e) => setQuery({ ...query, q: e.target.value, page: 0 })}
              placeholder="Search address, account, municipality…"
              aria-label="Search rows"
              className="h-10 w-full rounded-lg border border-line-strong bg-surface pr-9 pl-9 text-sm placeholder:text-ink-3"
            />
            {loading && (
              <LoaderCircle className="absolute top-1/2 right-3 size-4 -translate-y-1/2 animate-spin text-ink-3" aria-hidden />
            )}
          </div>
          <Select
            value={query.final}
            onChange={(v) => setQuery({ ...query, final: v, page: 0 })}
            options={[{ value: "", label: "All final areas" }, ...finals.map((f) => ({ value: f, label: f }))]}
          />
          <Select
            value={query.source}
            onChange={(v) => setQuery({ ...query, source: v, page: 0 })}
            options={[
              { value: "", label: "All match sources" },
              ...result.sources
                .filter((s) => query.view === "all" || s.key !== "ZIP")
                .map((s) => ({ value: s.key, label: sourceMeta(s.key).label })),
            ]}
          />
        </div>
      </div>

      {table.rows.length === 0 ? (
        <div className="flex flex-col items-center px-5 py-12 text-center">
          <Inbox className="size-8 text-ink-3" aria-hidden />
          <p className="mt-3 text-sm font-medium">No rows match</p>
          <p className="mt-1 text-xs text-ink-3">Clear the search or a filter to see more.</p>
        </div>
      ) : (
        <>
          {/* table on wider screens */}
          <div className={cx("hidden overflow-x-auto md:block", loading && "opacity-60")}>
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-line bg-sunken">
                  {cols.map((c) => (
                    <th key={c} scope="col" className="px-4 py-2.5 text-[11px] font-semibold tracking-wide whitespace-nowrap text-ink-2 uppercase">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {table.rows.map((r, i) => (
                  <tr key={i} className="align-top hover:bg-sunken/60">
                    {cols.map((c) => (
                      <td key={c} className={cx("px-4 py-2.5", c === table.addrCol && "min-w-72 max-w-md")}>
                        <Cell col={c} value={r[c]} table={table} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* cards on phones */}
          <ul className={cx("divide-y divide-line md:hidden", loading && "opacity-60")}>
            {table.rows.map((r, i) => {
              const m = sourceMeta(r["MATCH SOURCE"]);
              return (
                <li key={i} className="space-y-2 px-4 py-3">
                  <div className="flex items-center gap-2">
                    {table.idCol && <span className="truncate font-mono text-xs text-ink-3">{r[table.idCol]}</span>}
                    <Badge tone={m.tone} icon={m.icon} className="ml-auto">
                      {m.label}
                    </Badge>
                  </div>
                  <p className="font-mono text-[12px] leading-snug break-words text-ink-2">{r[table.addrCol] || "—"}</p>
                  <dl className="grid grid-cols-2 gap-x-3 gap-y-1.5">
                    {outputCols.map((c) => (
                      <div key={c} className="min-w-0">
                        <dt className="text-[10.5px] font-semibold tracking-wide text-ink-3 uppercase">{c}</dt>
                        <dd className="truncate text-sm">
                          <Cell col={c} value={r[c]} table={table} />
                        </dd>
                      </div>
                    ))}
                  </dl>
                </li>
              );
            })}
          </ul>
        </>
      )}

      <footer className="flex items-center gap-3 border-t border-line px-4 py-2.5 sm:px-5">
        <p className="tabular text-xs text-ink-3">
          {table.total === 0
            ? "0 rows"
            : `${fmt(table.offset + 1)}–${fmt(table.offset + table.rows.length)} of ${fmt(table.total)} rows`}
        </p>
        {table.pages > 1 && (
          <div className="ml-auto flex items-center gap-1">
            <Button
              size="sm"
              variant="ghost"
              icon={ChevronLeft}
              aria-label="Previous page"
              disabled={loading || query.page === 0}
              onClick={() => setQuery({ ...query, page: query.page - 1 })}
            />
            <span className="tabular px-1 text-xs text-ink-2">
              {fmt(query.page + 1)} / {fmt(table.pages)}
            </span>
            <Button
              size="sm"
              variant="ghost"
              icon={ChevronRight}
              aria-label="Next page"
              disabled={loading || query.page >= table.pages - 1}
              onClick={() => setQuery({ ...query, page: query.page + 1 })}
            />
          </div>
        )}
      </footer>
    </Card>
  );
}

/* ======================================================================== */

export default function Results({ result, table, query, setQuery, tableLoading, stale, onRun, running, onExport, busy }) {
  const pick = (key) => {
    setQuery({ view: "review", q: "", final: "", source: key, page: 0 });
    document.getElementById("rows")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="space-y-5">
      <Hero result={result} stale={stale} onRun={onRun} running={running} onExport={onExport} busy={busy} />
      <div className="grid gap-5 xl:grid-cols-2">
        <FinalArea result={result} />
        <Sources result={result} onPick={pick} />
      </div>
      <AreaBars result={result} />
      {table && <Rows result={result} table={table} query={query} setQuery={setQuery} loading={tableLoading} />}
    </div>
  );
}
