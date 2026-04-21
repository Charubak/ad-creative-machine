import { useState } from "react";

interface Props {
  brief: Record<string, unknown>;
}

export function BriefCard({ brief }: Props) {
  const [open, setOpen] = useState(false);

  const angles = (brief.angles as any[]) ?? [];
  const summary = brief.brief_summary_for_copy_agent as string;
  const extra = (brief.recommended_extra_platforms as any[]) ?? [];
  const compliance = (brief.compliance_constraints as string[]) ?? [];

  return (
    <div className="am-card am-brief-section">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
        <h3 className="am-heading" style={{ fontSize: "0.95rem" }}>Strategic Brief</h3>
        <button className="am-btn am-btn-ghost" style={{ padding: "0.2rem 0.6rem", fontSize: "0.7rem" }} onClick={() => setOpen(!open)}>
          {open ? "collapse" : "expand"}
        </button>
      </div>

      <div style={{ color: "var(--text-dim)", fontSize: "0.82rem", marginBottom: "1rem" }}>
        {summary}
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", marginBottom: "0.75rem" }}>
        {angles.map((a: any) => (
          <span key={a.name} className="am-angle-pill">
            <span className="am-angle-rank">#{a.rank}</span>
            {a.name}
            <span style={{ color: "var(--text-dim)", fontSize: "0.65rem" }}>{a.primary_emotion}</span>
          </span>
        ))}
      </div>

      {open && (
        <div>
          {angles.map((a: any) => (
            <div key={a.name} style={{ marginBottom: "1rem", padding: "0.75rem", background: "var(--surface2)", borderRadius: "4px" }}>
              <div style={{ color: "var(--amber)", marginBottom: "0.25rem", fontSize: "0.82rem", fontWeight: 500 }}>
                {a.rank}. {a.name}
              </div>
              <div style={{ color: "var(--text)", fontSize: "0.8rem" }}>{a.thesis}</div>
              {a.evidence_to_use?.length > 0 && (
                <div style={{ marginTop: "0.35rem", fontSize: "0.75rem", color: "var(--text-dim)" }}>
                  Evidence: {a.evidence_to_use.join(" · ")}
                </div>
              )}
            </div>
          ))}

          {compliance.length > 0 && (
            <div style={{ marginTop: "0.75rem" }}>
              <div className="am-subheading" style={{ marginBottom: "0.5rem" }}>Compliance Constraints</div>
              {compliance.map((c, i) => (
                <div key={i} className="am-flag warn">
                  <span>⚠</span>
                  <span style={{ fontSize: "0.75rem" }}>{c}</span>
                </div>
              ))}
            </div>
          )}

          {extra.filter((p: any) => p.recommend).length > 0 && (
            <div style={{ marginTop: "0.75rem" }}>
              <div className="am-subheading" style={{ marginBottom: "0.5rem" }}>Extra Platform Recommendations</div>
              {extra.filter((p: any) => p.recommend).map((p: any) => (
                <div key={p.platform} style={{ marginBottom: "0.5rem", fontSize: "0.8rem" }}>
                  <span className="am-tag">{p.platform}</span>
                  <span style={{ marginLeft: "0.5rem", color: "var(--text-dim)" }}>{p.rationale}</span>
                  <span style={{ marginLeft: "0.5rem", color: "var(--amber-dim)", fontSize: "0.7rem" }}>{p.suggested_budget_split_pct}% budget</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
