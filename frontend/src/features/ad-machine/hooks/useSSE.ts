import { useEffect, useState, useRef } from "react";
import type { SSEEvent } from "../types";

export function useSSE(url: string | null) {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!url) return;
    setEvents([]);
    setDone(false);
    setError(null);

    const es = new EventSource(url, { withCredentials: true });
    esRef.current = es;

    const push = (type: string) => (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setEvents((prev) => [...prev, { type, ...data }]);
    };

    es.addEventListener("stage_started", push("stage_started") as EventListener);
    es.addEventListener("stage_completed", push("stage_completed") as EventListener);
    es.addEventListener("substage_progress", push("substage_progress") as EventListener);
    es.addEventListener("pack_ready", (e: MessageEvent) => {
      setEvents((prev) => [...prev, { type: "pack_ready", ...JSON.parse(e.data) }]);
      setDone(true);
      es.close();
    });
    es.addEventListener("job_failed", (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setError(data.error ?? "Pipeline failed");
      setDone(true);
      es.close();
    });

    es.onerror = () => {
      setError("Connection lost. Reload to retry.");
      setDone(true);
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [url]);

  return { events, done, error };
}
