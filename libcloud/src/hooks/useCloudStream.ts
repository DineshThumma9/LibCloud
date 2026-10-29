import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { startLibCloudStream } from "../api";
import { useCloudStore } from "../state";

type UseCloudStreamArgs = {
  username: string;
  token: string;
};

export function useCloudStream({ username, token }: UseCloudStreamArgs) {
  const [isLoading, setIsLoading] = useState(false);
  const [statusText, setStatusText] = useState("");
  const abortControllerRef = useRef<AbortController | null>(null);
  const resetStore = useCloudStore((s) => s.reset);

  const abortStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
  }, []);

  const streamResponse = useCallback(async () => {
    abortStream();
    resetStore();

    abortControllerRef.current = new AbortController();
    setIsLoading(true);
    setStatusText("Connecting to server...");

    try {
      await startLibCloudStream(
        {
          username: username.trim(),
          token: token.trim() || undefined,
        },
        {
          signal: abortControllerRef.current.signal,
          onStatusChange: (text) => setStatusText(text),
          onEvent: (type, data) => useCloudStore.getState().handleEvent(type, data),
          onError: (err) => {
            setIsLoading(false);
            toast.error("Stream Error", {
              description: err.message || "Pipeline error occurred",
            });
          },
          onDone: () => {
            setIsLoading(false);
          },
        }
      );
    } catch (e: any) {
      if (e?.name === "AbortError") {
        setStatusText("Stream cancelled");
      } else {
        console.error("Stream error:", e);
        setStatusText(`Connection failed: ${e?.message || e}`);
        toast.error("Stream connection failed", {
          description: e?.message || "Could not reach backend",
        });
      }
    } finally {
      setIsLoading(false);
    }
  }, [abortStream, resetStore, token, username]);

  const handleGenerate = useCallback(() => {
    if (!username.trim()) {
      toast.error("Please enter a valid GitHub username");
      return;
    }
    streamResponse();
  }, [streamResponse, username]);

  useEffect(() => {
    return () => {
      abortStream();
    };
  }, [abortStream]);

  return { isLoading, statusText, handleGenerate, abortStream };
}
