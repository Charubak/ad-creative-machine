import type { ComplianceFlag } from "../types";

interface Props {
  flags: ComplianceFlag[];
}

export function ComplianceFlagBanner({ flags }: Props) {
  if (!flags.length) return null;

  const blocks = flags.filter((f) => f.severity === "block");
  const warns = flags.filter((f) => f.severity === "warn");

  return (
    <div style={{ marginBottom: "1rem" }}>
      {blocks.length > 0 && (
        <div style={{ marginBottom: "0.5rem" }}>
          <div style={{ fontSize: "0.7rem", color: "var(--red)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "0.25rem" }}>
            {blocks.length} blocked phrase{blocks.length !== 1 ? "s" : ""} — must fix before launch
          </div>
          {blocks.map((f, i) => (
            <div key={i} className="am-flag block">
              <span>⛔</span>
              <span>
                <strong>{f.matched_text}</strong> — {f.rule}
                {f.suggestion && <span style={{ color: "var(--text-dim)" }}> · {f.suggestion}</span>}
              </span>
            </div>
          ))}
        </div>
      )}
      {warns.length > 0 && (
        <div>
          <div style={{ fontSize: "0.7rem", color: "var(--yellow)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "0.25rem" }}>
            {warns.length} warning{warns.length !== 1 ? "s" : ""} — review before launch
          </div>
          {warns.map((f, i) => (
            <div key={i} className="am-flag warn">
              <span>⚠</span>
              <span>
                <strong>{f.matched_text}</strong> — {f.rule}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
