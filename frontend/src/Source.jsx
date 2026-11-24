import { useRef, useState } from "react";
import {
  CloudUpload,
  FileSpreadsheet,
  FileUp,
  X,
  Play,
  RotateCcw,
  LoaderCircle,
  ArrowDown,
  Info,
} from "lucide-react";
import { Card, CardHeader, Button, Label, Select, cx, fmt } from "./ui.jsx";

const ACCEPT = ".xlsx,.xlsm,.xls,.csv";

/* ------------------------------------------------------------------------ */
/* Empty state: the drop zone, beside a worked example of one address.       */
/* ------------------------------------------------------------------------ */

function Example() {
  const out = [
    ["AREA", "ISABELA"],
    ["MUNICIPALITY", "CABATUAN"],
    ["FINAL AREA", "NORTH LUZON"],
    ["ZIP CODE", "3315"],
  ];
  return (
    <div className="flex flex-col justify-center rounded-lg bg-sunken p-4 sm:p-5">
      <p className="text-xs font-semibold tracking-wide text-ink-2 uppercase">One address, broken</p>
      <p className="mt-3 font-mono text-[12.5px] leading-relaxed break-all text-ink-2">
        PUROK 2,BARANGAY CANAN,3315 <span className="mark text-ink">CABATUAN</span>{" "}
        <span className="mark text-ink">ISABELA</span>,09-<span className="mark text-ink">3315</span>,PHILIPPINES
      </p>
      <ArrowDown className="my-3 size-4 text-ink-3" aria-hidden />
      <dl className="grid grid-cols-2 gap-2">
        {out.map(([k, v]) => (
          <div key={k} className="rounded-md bg-surface px-3 py-2 ring-1 ring-line">
            <dt className="text-[10.5px] font-semibold tracking-wide text-ink-3 uppercase">{k}</dt>
            <dd className={cx("mt-0.5 truncate text-sm font-medium", k === "ZIP CODE" && "font-mono")}>{v}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 flex gap-1.5 text-xs text-ink-3">
        <Info className="mt-px size-3.5 shrink-0" aria-hidden />
        The 09- before the ZIP is a branch code, not part of the location, so it is ignored.
      </p>
    </div>
  );
}

function DropZone({ onFile, busy }) {
  const input = useRef(null);
  const [over, setOver] = useState(false);

  const take = (files) => {
    const f = files?.[0];
    if (f) onFile(f);
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        take(e.dataTransfer.files);
      }}
      className={cx(
        "flex min-h-64 flex-col items-center justify-center rounded-lg border-2 border-dashed px-5 py-8 text-center transition-colors",
        over ? "border-focus bg-info-soft" : "border-line-strong",
      )}
    >
      {busy ? (
        <>
          <LoaderCircle className="size-9 animate-spin text-ink-3" aria-hidden />
          <p className="mt-4 text-sm font-medium">Reading file…</p>
          <p className="mt-1 text-xs text-ink-3">Large workbooks take a few seconds.</p>
        </>
      ) : (
        <>
          <div className="grid size-12 place-items-center rounded-full bg-sunken">
            <CloudUpload className="size-6 text-ink-2" aria-hidden />
          </div>
          <p className="mt-4 text-base font-semibold">Drop the portfolio file here</p>
          <p className="mt-1 text-sm text-ink-3">XLSX, XLS or CSV · the address column is picked up automatically</p>
          <Button variant="primary" icon={FileUp} className="mt-5" onClick={() => input.current?.click()}>
            Choose file
          </Button>
        </>
      )}
      <input
        ref={input}
        type="file"
        accept={ACCEPT}
        className="hidden"
        onChange={(e) => {
          take(e.target.files);
          e.target.value = "";
        }}
      />
    </div>
  );
}

/* ------------------------------------------------------------------------ */
/* Loaded state: file summary, column mapping, run.                         */
/* ------------------------------------------------------------------------ */

export default function Source({ file, onFile, onSelect, onClear, onRun, uploading, running, hasResult, stale }) {
  const replace = useRef(null);

  if (!file) {
    return (
      <Card>
        <CardHeader icon={FileSpreadsheet} title="Source file" />
        <div className="grid gap-4 p-4 sm:p-5 md:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
          <DropZone onFile={onFile} busy={uploading} />
          <Example />
        </div>
      </Card>
    );
  }

  const runLabel = hasResult && stale ? "Run again" : `Break ${fmt(file.rows)} addresses`;

  return (
    <Card>
      <CardHeader icon={FileSpreadsheet} title="Source file" />
      <div className="space-y-5 p-4 sm:p-5">
        {/* file row */}
        <div className="flex items-center gap-3 rounded-lg bg-sunken p-3">
          <div className="grid size-10 shrink-0 place-items-center rounded-lg bg-surface ring-1 ring-line">
            {uploading ? (
              <LoaderCircle className="size-5 animate-spin text-ink-3" aria-hidden />
            ) : (
              <FileSpreadsheet className="size-5 text-good" aria-hidden />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold" title={file.name}>
              {file.name}
            </p>
            <p className="tabular text-xs text-ink-3">
              {fmt(file.rows)} rows · {file.columns.length} columns
              {file.sheet ? ` · ${file.sheet}` : ""}
            </p>
          </div>
          <Button size="sm" variant="secondary" icon={FileUp} onClick={() => replace.current?.click()} disabled={uploading} aria-label="Replace file">
            <span className="hidden sm:inline">Replace</span>
          </Button>
          <Button size="sm" variant="ghost" icon={X} onClick={onClear} aria-label="Remove file" disabled={uploading} />
          <input
            ref={replace}
            type="file"
            accept={ACCEPT}
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onFile(f);
              e.target.value = "";
            }}
          />
        </div>

        {/* mapping */}
        <div className={cx("grid gap-4", file.sheets.length > 1 && "sm:grid-cols-2")}>
          {file.sheets.length > 1 && (
            <div>
              <Label htmlFor="sheet">Sheet</Label>
              <Select id="sheet" value={file.sheet} options={file.sheets} onChange={(v) => onSelect({ sheet: v })} />
            </div>
          )}
          <div>
            <Label htmlFor="addr">Address column</Label>
            <Select
              id="addr"
              value={file.addrCol}
              options={file.columns}
              onChange={(v) => onSelect({ addrCol: v })}
            />
          </div>
        </div>

        {/* samples, so a wrong column choice is obvious before running */}
        <div>
          <p className="mb-1.5 text-xs font-semibold tracking-wide text-ink-2 uppercase">
            First addresses in this column
          </p>
          <ul className="divide-y divide-line overflow-hidden rounded-lg ring-1 ring-line">
            {file.samples.length === 0 && <li className="px-3 py-2 text-sm text-ink-3">Column is empty.</li>}
            {file.samples.map((s, i) => (
              <li key={i} className="truncate px-3 py-2 font-mono text-[12.5px] text-ink-2" title={s}>
                {s}
              </li>
            ))}
          </ul>
        </div>

        <div className="flex flex-col-reverse gap-3 border-t border-line pt-4 sm:flex-row sm:items-center">
          <p className="text-xs text-ink-3">
            {file.blanks > 0 ? `${fmt(file.blanks)} blank addresses will be flagged.` : "No blank addresses."}
          </p>
          <Button
            variant="primary"
            icon={hasResult && stale ? RotateCcw : Play}
            busy={running}
            onClick={onRun}
            disabled={uploading}
            className="w-full sm:ml-auto sm:w-auto"
          >
            {running ? "Breaking addresses…" : runLabel}
          </Button>
        </div>
      </div>
    </Card>
  );
}
