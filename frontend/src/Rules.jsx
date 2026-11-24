import { useRef, useState } from "react";
import { SlidersHorizontal, ChevronDown, Database, Upload, Download, RotateCcw } from "lucide-react";
import { Card, Label, Segmented, Switch, Button, cx, fmt } from "./ui.jsx";

/**
 * Output rules. A side rail on large screens; a collapsed panel on phones so
 * the upload stays the first thing on screen.
 */
export default function Rules({ rules, setRules, options, reference, onRefUpload, onRefReset, onRefDownload, busy }) {
  const [open, setOpen] = useState(false);
  const refInput = useRef(null);
  const final = options.finalModes.find((m) => m.value === rules.finalMode);
  const area = options.areaModes.find((m) => m.value === rules.areaMode);

  return (
    <Card className="lg:sticky lg:top-4">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center gap-3 px-4 py-3 text-left sm:px-5 lg:pointer-events-none lg:border-b lg:border-line"
      >
        <SlidersHorizontal className="size-4 shrink-0 text-ink-3" aria-hidden />
        <span className="text-sm font-semibold">Output rules</span>
        <span className="ml-auto truncate text-xs text-ink-3 lg:hidden">
          {area?.label} · {final?.label}
        </span>
        <ChevronDown
          className={cx("size-4 shrink-0 text-ink-3 transition-transform lg:hidden", open && "rotate-180")}
          aria-hidden
        />
      </button>

      <div className={cx(open ? "block" : "hidden", "border-t border-line lg:block lg:border-t-0")}>
        <div className="space-y-6 p-4 sm:p-5">
          <div>
            <Label hint="What the AREA column holds">AREA</Label>
            <Segmented
              label="AREA column"
              value={rules.areaMode}
              onChange={(v) => setRules({ ...rules, areaMode: v })}
              options={options.areaModes}
            />
          </div>

          <div>
            <Label hint="How FINAL AREA rolls the location up">Final area</Label>
            <div role="radiogroup" aria-label="FINAL AREA column" className="space-y-1.5">
              {options.finalModes.map((m) => {
                const active = m.value === rules.finalMode;
                return (
                  <button
                    key={m.value}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => setRules({ ...rules, finalMode: m.value })}
                    className={cx(
                      "flex w-full items-start gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors",
                      active ? "border-primary bg-sunken" : "border-line hover:border-line-strong",
                    )}
                  >
                    <span
                      className={cx(
                        "mt-0.5 grid size-4 shrink-0 place-items-center rounded-full border-2",
                        active ? "border-primary" : "border-line-strong",
                      )}
                    >
                      {active && <span className="size-1.5 rounded-full bg-primary" />}
                    </span>
                    <span className="min-w-0">
                      <span className="block text-sm font-medium">{m.label}</span>
                      <span className="block truncate font-mono text-[11px] text-ink-3">{m.example}</span>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <Label>Matching</Label>
            <Switch
              id="fallback"
              checked={rules.fallback}
              onChange={(v) => setRules({ ...rules, fallback: v })}
              label="Read place names when the ZIP fails"
              hint="Looks for a municipality, then a province, in the address text."
            />
          </div>

          <div>
            <Label>Reference table</Label>
            <div className="rounded-lg bg-sunken p-3">
              <div className="flex items-center gap-2.5">
                <Database className="size-4 shrink-0 text-ink-3" aria-hidden />
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{reference.custom ? reference.name : "Bundled table"}</p>
                  <p className="tabular text-xs text-ink-3">
                    {fmt(reference.zips)} ZIPs · {reference.provinces} provinces
                  </p>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button size="sm" icon={Upload} onClick={() => refInput.current?.click()} busy={busy.reference}>
                  Use my CSV
                </Button>
                {reference.custom ? (
                  <Button size="sm" variant="ghost" icon={RotateCcw} onClick={onRefReset}>
                    Back to bundled
                  </Button>
                ) : (
                  <Button size="sm" variant="ghost" icon={Download} onClick={onRefDownload} busy={busy.refDownload}>
                    Download
                  </Button>
                )}
              </div>
              <input
                ref={refInput}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) onRefUpload(f);
                  e.target.value = "";
                }}
              />
            </div>
            <p className="mt-2 text-xs text-ink-3">
              Columns: ZIP CODE, MUNICIPALITY, PROVINCE, REGION, ISLAND GROUP.
            </p>
          </div>
        </div>
      </div>
    </Card>
  );
}
