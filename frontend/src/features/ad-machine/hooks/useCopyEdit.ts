import { useRef, useCallback } from "react";
import { adMachineApi } from "../api/adMachineClient";

export function useCopyEdit() {
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  const debouncedEdit = useCallback(
    (variationId: string, payload: Record<string, unknown>, delay = 500) => {
      if (timers.current[variationId]) {
        clearTimeout(timers.current[variationId]);
      }
      timers.current[variationId] = setTimeout(() => {
        adMachineApi.editCopyVariation(variationId, payload).catch(console.error);
      }, delay);
    },
    []
  );

  return { debouncedEdit };
}
