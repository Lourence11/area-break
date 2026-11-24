import { LoaderCircle, ChevronDown } from "lucide-react";

export const fmt = (n) => (n ?? 0).toLocaleString("en-US");
export const pct = (n, d = 1) => `${(n * 100).toFixed(d)}%`;

export function cx(...parts) {
  return parts.filter(Boolean).join(" ");
}

export function Card({ className, children, ...rest }) {
  return (
    <section
      className={cx(
        "rounded-xl border border-line bg-surface shadow-[0_1px_2px_rgba(15,27,45,0.04)]",
        className,
      )}
      {...rest}
    >
      {children}
    </section>
  );
}

export function CardHeader({ icon: Icon, title, meta, action }) {
  return (
    <header className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-line px-4 py-3 sm:px-5">
      {Icon && <Icon className="size-4 shrink-0 text-ink-3" aria-hidden />}
      <h2 className="text-sm font-semibold text-ink">{title}</h2>
      {meta && <span className="text-xs text-ink-3">{meta}</span>}
      {action && <div className="ml-auto flex items-center gap-2">{action}</div>}
    </header>
  );
}

export function Label({ children, htmlFor, hint }) {
  return (
    <div className="mb-1.5">
      <label htmlFor={htmlFor} className="block text-xs font-semibold tracking-wide text-ink-2 uppercase">
        {children}
      </label>
      {hint && <p className="mt-0.5 text-xs text-ink-3">{hint}</p>}
    </div>
  );
}

const BUTTON = {
  primary: "bg-primary text-on-primary hover:bg-primary-hover",
  secondary: "border border-line-strong bg-surface text-ink hover:bg-sunken",
  ghost: "text-ink-2 hover:bg-sunken hover:text-ink",
};

export function Button({ variant = "secondary", size = "md", icon: Icon, busy, children, className, ...rest }) {
  const sizes = size === "sm" ? "h-8 px-2.5 text-xs gap-1.5" : "h-10 px-4 text-sm gap-2";
  return (
    <button
      type="button"
      className={cx(
        "inline-flex shrink-0 items-center justify-center rounded-lg font-medium transition-colors",
        "disabled:cursor-not-allowed disabled:opacity-55",
        sizes,
        BUTTON[variant],
        className,
      )}
      disabled={busy || rest.disabled}
      aria-busy={busy || undefined}
      {...rest}
    >
      {busy ? (
        <LoaderCircle className={cx(size === "sm" ? "size-3.5" : "size-4", "animate-spin")} aria-hidden />
      ) : (
        Icon && <Icon className={size === "sm" ? "size-3.5" : "size-4"} aria-hidden />
      )}
      {children}
    </button>
  );
}

export function Select({ id, value, onChange, options, disabled }) {
  return (
    <div className="relative">
      <select
        id={id}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className={cx(
          "h-10 w-full appearance-none rounded-lg border border-line-strong bg-surface pr-9 pl-3 text-sm text-ink",
          "disabled:opacity-55",
        )}
      >
        {options.map((o) => {
          const v = typeof o === "string" ? o : o.value;
          const l = typeof o === "string" ? o : o.label;
          return (
            <option key={v} value={v}>
              {l}
            </option>
          );
        })}
      </select>
      <ChevronDown className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-ink-3" aria-hidden />
    </div>
  );
}

/** Segmented control - a short set of mutually exclusive choices. */
export function Segmented({ value, onChange, options, label }) {
  return (
    <div role="radiogroup" aria-label={label} className="grid auto-cols-fr grid-flow-col gap-1 rounded-lg bg-sunken p-1">
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(o.value)}
            className={cx(
              "min-h-8 rounded-md px-2 text-xs font-medium transition-colors",
              active ? "bg-surface text-ink shadow-sm ring-1 ring-line" : "text-ink-2 hover:text-ink",
            )}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

export function Switch({ checked, onChange, label, hint, id }) {
  return (
    <div className="flex items-start gap-3">
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={cx(
          "relative mt-0.5 h-5 w-9 shrink-0 rounded-full transition-colors",
          checked ? "bg-primary" : "bg-line-strong",
        )}
      >
        <span
          className={cx(
            "absolute top-0.5 left-0.5 size-4 rounded-full bg-surface shadow transition-transform",
            checked && "translate-x-4",
          )}
        />
        <span className="sr-only">{label}</span>
      </button>
      <label htmlFor={id} className="cursor-pointer text-sm">
        <span className="block font-medium text-ink">{label}</span>
        {hint && <span className="mt-0.5 block text-xs text-ink-3">{hint}</span>}
      </label>
    </div>
  );
}

const TONE = {
  good: "bg-good-soft text-good",
  warn: "bg-warn-soft text-warn",
  bad: "bg-bad-soft text-bad",
  info: "bg-info-soft text-info",
  neutral: "bg-sunken text-ink-2",
};

export function Badge({ tone = "neutral", icon: Icon, children, className }) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-medium whitespace-nowrap",
        TONE[tone],
        className,
      )}
    >
      {Icon && <Icon className="size-3" aria-hidden />}
      {children}
    </span>
  );
}

export function Zip({ children }) {
  if (!children) return <span className="text-ink-3">—</span>;
  return <span className="mark font-mono text-[13px] text-ink">{children}</span>;
}
