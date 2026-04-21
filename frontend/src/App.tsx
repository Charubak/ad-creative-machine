import { useState } from "react";
import "./features/ad-machine/styles/ad-machine.css";
import { ProjectInput } from "./features/ad-machine/pages/ProjectInput";
import { WorkflowView } from "./features/ad-machine/pages/WorkflowView";
import { OutputGallery } from "./features/ad-machine/pages/OutputGallery";
import { PerformanceUpload } from "./features/ad-machine/pages/PerformanceUpload";

type AppView =
  | { page: "input" }
  | { page: "workflow"; jobId: string; projectId: string }
  | { page: "gallery"; packId: string; projectId: string }
  | { page: "performance"; packId: string; projectId: string };

export default function App() {
  const [view, setView] = useState<AppView>({ page: "input" });

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text)" }}>
      <link
        href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500&family=Playfair+Display:wght@400;600;700&display=swap"
        rel="stylesheet"
      />

      {/* Nav */}
      <nav style={{
        borderBottom: "1px solid var(--border)",
        padding: "0.9rem 2rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        position: "sticky",
        top: 0,
        background: "rgba(10,9,8,0.96)",
        backdropFilter: "blur(8px)",
        zIndex: 100,
      }}>
        <div
          style={{ cursor: "pointer", display: "flex", alignItems: "baseline", gap: "0.5rem" }}
          onClick={() => setView({ page: "input" })}
        >
          <span style={{ fontFamily: "var(--serif)", fontSize: "1.05rem", color: "var(--text-bright)", fontWeight: 700 }}>
            Ad Creative Machine
          </span>
          <span style={{ fontSize: "0.6rem", color: "var(--amber-dim)", letterSpacing: "0.1em" }}>
            by Charubak
          </span>
        </div>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <button
            className="am-btn am-btn-ghost"
            style={{ fontSize: "0.75rem" }}
            onClick={() => setView({ page: "input" })}
          >
            New Project
          </button>
          {(view.page === "gallery" || view.page === "performance") && (
            <button
              className="am-btn am-btn-ghost"
              style={{ fontSize: "0.75rem" }}
              onClick={() =>
                setView({
                  page: "performance",
                  packId: (view as any).packId,
                  projectId: (view as any).projectId,
                })
              }
            >
              Performance
            </button>
          )}
        </div>
      </nav>

      {/* Page routing */}
      {view.page === "input" && (
        <ProjectInput
          onJobStarted={(projectId, jobId) =>
            setView({ page: "workflow", jobId, projectId })
          }
        />
      )}

      {view.page === "workflow" && (
        <WorkflowView
          jobId={view.jobId}
          projectId={view.projectId}
          onPackReady={(packId) =>
            setView({ page: "gallery", packId, projectId: view.projectId })
          }
        />
      )}

      {view.page === "gallery" && (
        <OutputGallery
          packId={view.packId}
          onIterateReady={(projectId) =>
            setView({ page: "performance", packId: view.packId, projectId })
          }
        />
      )}

      {view.page === "performance" && (
        <PerformanceUpload
          packId={view.packId}
          projectId={view.projectId}
          onIterateStarted={(jobId) =>
            setView({ page: "workflow", jobId, projectId: view.projectId })
          }
        />
      )}
    </div>
  );
}
