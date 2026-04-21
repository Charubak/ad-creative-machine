import { useEffect } from "react";
import { useSSE } from "../hooks/useSSE";
import { PipelineStage } from "../components/PipelineStage";
import { adMachineApi } from "../api/adMachineClient";
import type { SSEEvent } from "../types";

const ORDERED_STAGES = ["opus_planning", "copy_generation", "image_generation", "assembly"];

interface Props {
  jobId: string;
  projectId: string;
  onPackReady: (packId: string) => void;
}

type StageState = "pending" | "active" | "done" | "failed";

function deriveStageStates(events: SSEEvent[]): Record<string, StageState> {
  const states: Record<string, StageState> = {};
  ORDERED_STAGES.forEach((s) => (states[s] = "pending"));

  for (const ev of events) {
    if (ev.type === "stage_started" && ev.stage) {
      states[ev.stage] = "active";
    } else if (ev.type === "stage_completed" && ev.stage) {
      states[ev.stage] = "done";
    } else if (ev.type === "job_failed" && ev.stage) {
      states[ev.stage] = "failed";
    }
  }
  return states;
}

function summaryForStage(stage: string, events: SSEEvent[]): string | undefined {
  const completed = events.find(
    (e) => e.type === "stage_completed" && e.stage === stage
  );
  return completed?.output_summary;
}

function subeventsForStage(stage: string, events: SSEEvent[]): SSEEvent[] {
  return events.filter((e) => e.type === "substage_progress" && e.stage === stage);
}

export function WorkflowView({ jobId, projectId, onPackReady }: Props) {
  const url = adMachineApi.streamJobUrl(jobId);
  const { events, done, error } = useSSE(url);

  useEffect(() => {
    const packEvent = events.find((e) => e.type === "pack_ready");
    if (packEvent?.creative_pack_id) {
      onPackReady(packEvent.creative_pack_id);
    }
  }, [events, onPackReady]);

  const stageStates = deriveStageStates(events);
  const isRunning = !done && !error;

  return (
    <div className="am-page">
      <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "2rem" }}>
        <h1 className="am-heading" style={{ fontSize: "1.3rem" }}>Generating Creative Package</h1>
        {isRunning && <span className="am-spinner" />}
        {error && <span style={{ color: "var(--red)", fontSize: "0.82rem" }}>Failed: {error}</span>}
        {done && !error && <span style={{ color: "var(--green)", fontSize: "0.82rem" }}>Complete</span>}
      </div>

      <div className="am-pipeline">
        {ORDERED_STAGES.map((stage) => (
          <PipelineStage
            key={stage}
            stage={stage}
            status={stageStates[stage]}
            summary={summaryForStage(stage, events)}
            substages={subeventsForStage(stage, events)}
          />
        ))}
      </div>

      {error && (
        <div style={{ marginTop: "1.5rem" }}>
          <div style={{ color: "var(--red)", marginBottom: "1rem", padding: "0.75rem", background: "rgba(224,82,82,0.1)", borderRadius: "4px" }}>
            {error}
          </div>
          <button
            className="am-btn am-btn-ghost"
            onClick={() => window.location.reload()}
          >
            ← Start over
          </button>
        </div>
      )}

      {isRunning && (
        <p style={{ color: "var(--text-dim)", fontSize: "0.75rem", marginTop: "1.5rem" }}>
          Estimated time: 3–5 minutes for a full pack. Grab a coffee.
        </p>
      )}
    </div>
  );
}
