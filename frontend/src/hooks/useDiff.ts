import { useState, useCallback } from "react";
import { apiFetch } from "../utils/api";
import { CodeDiff } from "../types/task";

export interface UseDiffOptions {
  taskId: string;
  includeLines?: boolean;
  onError?: (error: Error) => void;
}

export interface UseDiffResult {
  diff: CodeDiff | null;
  isLoading: boolean;
  error: Error | null;
  fetchDiff: () => Promise<void>;
  reset: () => void;
}

export function useDiff({
  taskId,
  includeLines = true,
  onError,
}: UseDiffOptions): UseDiffResult {
  const [diff, setDiff] = useState<CodeDiff | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchDiff = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (includeLines) {
        params.set("include_lines", "true");
      }
      const queryString = params.toString();
      const url = `/tasks/${taskId}/diff${queryString ? `?${queryString}` : ""}`;

      const data = await apiFetch<CodeDiff>(url);
      setDiff(data);
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      onError?.(error);
    } finally {
      setIsLoading(false);
    }
  }, [taskId, includeLines, onError]);

  const reset = useCallback(() => {
    setDiff(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return {
    diff,
    isLoading,
    error,
    fetchDiff,
    reset,
  };
}
