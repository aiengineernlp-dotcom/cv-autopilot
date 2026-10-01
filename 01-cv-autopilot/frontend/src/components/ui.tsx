import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-xl border border-border bg-panel p-5 shadow-[var(--shadow)] ${className}`}
    >
      {children}
    </div>
  );
}

export function Button({
  className = "",
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" }) {
  const base =
    "rounded-lg px-4 py-2 text-sm font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed";
  const styles =
    variant === "primary"
      ? "bg-accent text-white hover:bg-accent-strong"
      : "border border-border text-text hover:bg-panel-2";
  return <button className={`${base} ${styles} ${className}`} {...props} />;
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full rounded-lg border border-border bg-panel px-3 py-2 text-sm text-text outline-none focus:border-accent ${props.className ?? ""}`}
    />
  );
}

export function Label({ children }: { children: ReactNode }) {
  return (
    <label className="mb-1 block font-mono text-xs uppercase tracking-wide text-text-faint">
      {children}
    </label>
  );
}

export function ErrorText({ children }: { children: ReactNode }) {
  if (!children) return null;
  return <p className="rounded-lg bg-critical-soft px-3 py-2 text-sm text-critical">{children}</p>;
}

export function StatusPill({ tone, children }: { tone: "ok" | "warn" | "neutral"; children: ReactNode }) {
  const styles = {
    ok: "bg-success-soft text-success",
    warn: "bg-warning-soft text-warning",
    neutral: "bg-panel-2 text-text-faint border border-border",
  }[tone];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${styles}`}>
      {children}
    </span>
  );
}

export function SectionLabel({ index, title, description }: { index: string; title: string; description?: string }) {
  return (
    <div className="mb-6 flex items-baseline gap-3.5">
      <span className="flex-none rounded-full border border-accent px-3 py-0.5 font-mono text-[13px] text-accent">
        {index}
      </span>
      <div>
        <h2 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-text">{title}</h2>
        {description && <p className="mt-1 text-sm text-text-soft">{description}</p>}
      </div>
    </div>
  );
}
