import { useEffect, useRef, useState } from "react";
import { Split, CircleAlert, X, Database, LoaderCircle, Rows3 } from "lucide-react";
import { useStreamlitState, useFrameHeight, sendEvent } from "./streamlit.js";
import { Card, fmt } from "./ui.jsx";
import Source from "./Source.jsx";
import Rules from "./Rules.jsx";
import Results from "./Results.jsx";

const MAX_MB = 180;
const EMPTY_QUERY = { view: "all", q: "", final: "", source: "", page: 0 };

function readBase64(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result).split(",")[1] ?? "");
    r.onerror = () => reject(r.error);
    r.readAsDataURL(file);
  });
}

function saveDownload(d) {
  const bin = atob(d.b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  const url = URL.createObjectURL(new Blob([bytes], { type: d.mime }));
  const a = document.createElement("a");
  a.href = url;
  a.download = d.name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}

function Header({ reference }) {
  return (
    <header className="flex items-center gap-3">
      <div className="grid size-10 shrink-0 place-items-center rounded-lg bg-primary text-on-primary">
        <Split className="size-5" aria-hidden />
      </div>
      <div className="min-w-0">
        <h1 className="font-display text-xl leading-tight font-extrabold tracking-tight [font-stretch:125%] sm:text-2xl">
          Area Break
        </h1>
        <p className="truncate text-xs text-ink-3 sm:text-sm">
          Address column → AREA, MUNICIPALITY, FINAL AREA and ZIP CODE
        </p>
      </div>
      {reference && (
        <span className="ml-auto hidden items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1 text-xs text-ink-2 md:inline-flex">
          <Database className="size-3.5" aria-hidden />
          <span className="tabular">{fmt(reference.zips)} ZIPs</span>
          <span className="text-ink-3">· {reference.custom ? "custom" : "bundled"}</span>
        </span>
      )}
    </header>
  );
}

export default function App() {
  const state = useStreamlitState();
  useFrameHeight();

  const [rules, setRules] = useState(null);
  const [pending, setPending] = useState({});
  const [localError, setLocalError] = useState(null);
  const [dismissed, setDismissed] = useState(null);
  const [query, setQueryState] = useState(EMPTY_QUERY);
  const downloaded = useRef(new Set());
  const lastResult = useRef(null);
  const typing = useRef(null);

  const ack = state?.ack ?? 0;
  const isBusy = (k) => Boolean(pending[k]) && ack < pending[k];

  const fire = (key, type, payload) => {
    const nonce = sendEvent(type, payload);
    setPending((p) => ({ ...p, [key]: nonce }));
    return nonce;
  };

  // rules start from Python's defaults
  useEffect(() => {
    if (state?.rules && rules === null) setRules(state.rules);
  }, [state, rules]);

  // new run -> table query resets to what Python reset it to
  useEffect(() => {
    const id = state?.result?.id ?? null;
    if (id !== lastResult.current) {
      lastResult.current = id;
      setQueryState(state?.table?.query ?? EMPTY_QUERY);
    }
  }, [state]);

  // one-shot downloads handed back by Python
  useEffect(() => {
    const d = state?.download;
    if (d && !downloaded.current.has(d.nonce)) {
      downloaded.current.add(d.nonce);
      saveDownload(d);
    }
  }, [state]);

  const setQuery = (q) => {
    setQueryState(q);
    clearTimeout(typing.current);
    const delay = q.q !== query.q ? 320 : 0; // debounce typing only
    typing.current = setTimeout(() => fire("table", "table", { query: q }), delay);
  };

  if (!state || !rules) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-sm text-ink-3">
        <LoaderCircle className="size-4 animate-spin" aria-hidden /> Loading…
      </div>
    );
  }

  const file = state.file;
  const result = state.result;
  const stale = Boolean(result) && JSON.stringify(result.settings) !== JSON.stringify(rules);

  const onFile = async (f) => {
    setLocalError(null);
    if (f.size > MAX_MB * 1024 * 1024) {
      setLocalError(`${f.name} is ${(f.size / 1048576).toFixed(0)} MB. The limit is ${MAX_MB} MB — split the file and run each part.`);
      return;
    }
    setPending((p) => ({ ...p, upload: Number.MAX_SAFE_INTEGER })); // spinner while the browser reads
    try {
      const b64 = await readBase64(f);
      fire("upload", "upload", { name: f.name, b64 });
    } catch {
      setPending((p) => ({ ...p, upload: 0 }));
      setLocalError(`Could not read ${f.name}.`);
    }
  };

  const onRefUpload = async (f) => {
    const b64 = await readBase64(f);
    fire("reference", "reference", { name: f.name, b64 });
  };

  const error = localError ?? (state.error && state.error.nonce !== dismissed ? state.error.message : null);

  return (
    <div className="mx-auto max-w-[1440px] px-3 py-4 sm:px-6 sm:py-6">
      <Header reference={state.reference} />

      {error && (
        <div role="alert" className="mt-4 flex items-start gap-3 rounded-lg border border-bad/30 bg-bad-soft px-4 py-3 text-sm text-bad">
          <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
          <p className="flex-1">{error}</p>
          <button
            type="button"
            aria-label="Dismiss"
            className="rounded p-0.5 hover:bg-bad/10"
            onClick={() => {
              setLocalError(null);
              setDismissed(state.error?.nonce ?? null);
            }}
          >
            <X className="size-4" aria-hidden />
          </button>
        </div>
      )}

      <div className="mt-5 grid grid-cols-[minmax(0,1fr)] gap-5 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start">
        <div className="min-w-0 lg:col-start-1 lg:row-start-1">
          <Source
            file={file}
            onFile={onFile}
            onSelect={(patch) => fire("select", "select", patch)}
            onClear={() => fire("clear", "clear")}
            onRun={() => fire("run", "run", { rules })}
            uploading={isBusy("upload")}
            running={isBusy("run")}
            hasResult={Boolean(result)}
            stale={stale}
          />
        </div>

        <div className="min-w-0 lg:col-start-2 lg:row-span-2 lg:row-start-1">
          <Rules
            rules={rules}
            setRules={setRules}
            options={state.options}
            reference={state.reference}
            onRefUpload={onRefUpload}
            onRefReset={() => fire("reference", "reference", { reset: true })}
            onRefDownload={() => fire("refDownload", "export", { fmt: "reference" })}
            busy={{ reference: isBusy("reference"), refDownload: isBusy("refDownload") }}
          />
        </div>

        <div className="min-w-0 lg:col-start-1 lg:row-start-2">
          {result ? (
            <Results
              result={result}
              table={state.table}
              query={query}
              setQuery={setQuery}
              tableLoading={isBusy("table")}
              stale={stale}
              onRun={() => fire("run", "run", { rules })}
              running={isBusy("run")}
              onExport={(f) => fire(`export_${f}`, "export", { fmt: f })}
              busy={{ xlsx: isBusy("export_xlsx"), csv: isBusy("export_csv") }}
            />
          ) : (
            file && (
              <Card className="flex flex-col items-center px-5 py-12 text-center">
                <Rows3 className="size-8 text-ink-3" aria-hidden />
                <p className="mt-3 text-sm font-medium">Results appear here</p>
                <p className="mt-1 max-w-sm text-xs text-ink-3">
                  Check the address column above, then run. Every row is tagged with how it was matched.
                </p>
              </Card>
            )
          )}
        </div>
      </div>
    </div>
  );
}
