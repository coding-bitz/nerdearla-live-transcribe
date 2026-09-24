import { useCallback, useEffect, useRef, useState } from "react";
import {
  AccessibilityData,
  ChapterData,
  ErrorPayload,
  ExecutiveSummaryData,
} from "../api/client";

export interface ConnectOptions {
  sourceLanguage?: string;
  enableTranslation?: boolean;
  targetLanguage?: string;
}

export interface SubtitleItem {
  text: string;
  timestamp: number;
}

export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<ErrorPayload | null>(null);

  const [interimSubtitle, setInterimSubtitle] = useState("");
  const [finalSubtitles, setFinalSubtitles] = useState<SubtitleItem[]>([]);
  const [translations, setTranslations] = useState<SubtitleItem[]>([]);
  const [chapters, setChapters] = useState<ChapterData[]>([]);
  const [summary, setSummary] = useState<ExecutiveSummaryData | null>(null);
  const [accessibility, setAccessibility] = useState<AccessibilityData | null>(null);

  // Production buffer state
  const [bufferDelayMs, setBufferDelayMs] = useState(0);
  const [isPaused, setIsPaused] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const bufferQueueRef = useRef<Array<{ action: () => void; releaseAt: number }>>([]);
  const isPausedRef = useRef(isPaused);
  isPausedRef.current = isPaused;

  // Process delayed production buffer queue
  useEffect(() => {
    const interval = setInterval(() => {
      if (isPausedRef.current) return;

      const now = Date.now();
      const pending = bufferQueueRef.current;
      const executable: Array<() => void> = [];
      const remaining: typeof pending = [];

      for (const item of pending) {
        if (item.releaseAt <= now) {
          executable.push(item.action);
        } else {
          remaining.push(item);
        }
      }

      bufferQueueRef.current = remaining;
      executable.forEach((fn) => fn());
    }, 100);

    return () => clearInterval(interval);
  }, []);

  const scheduleBufferedAction = useCallback(
    (action: () => void) => {
      if (bufferDelayMs <= 0 && !isPausedRef.current) {
        action();
      } else {
        bufferQueueRef.current.push({
          action,
          releaseAt: Date.now() + bufferDelayMs,
        });
      }
    },
    [bufferDelayMs]
  );

  const connect = useCallback(
    (sessionId: string, options: ConnectOptions = {}) => {
      if (wsRef.current) {
        wsRef.current.close();
      }

      setError(null);
      setIsReady(false);

      const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const defaultHost = window.location.hostname === "localhost" ? "localhost:8080" : window.location.host;
      const wsHost = import.meta.env.VITE_WS_URL || `${wsProtocol}//${defaultHost}`;

      const params = new URLSearchParams();
      if (options.sourceLanguage) params.set("source_language", options.sourceLanguage);
      if (options.enableTranslation) params.set("translate", "true");
      if (options.targetLanguage) params.set("target_language", options.targetLanguage);

      const wsUrl = `${wsHost}/ws/${encodeURIComponent(sessionId)}?${params.toString()}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);

          if (payload.type === "ready") {
            setIsReady(true);
          } else if (payload.type === "transcription") {
            if (payload.subtype === "interim") {
              setInterimSubtitle(payload.text);
            } else if (payload.subtype === "final") {
              setInterimSubtitle("");
              scheduleBufferedAction(() => {
                setFinalSubtitles((prev) => [
                  ...prev,
                  { text: payload.text, timestamp: payload.timestamp },
                ]);
              });
            }
          } else if (payload.type === "translation") {
            scheduleBufferedAction(() => {
              setTranslations((prev) => [
                ...prev,
                { text: payload.text, timestamp: payload.timestamp },
              ]);
            });
          } else if (payload.type === "chapter") {
            setChapters((prev) => [...prev, payload.chapter]);
          } else if (payload.type === "summary") {
            setSummary(payload.summary);
          } else if (payload.type === "accessibility") {
            setAccessibility(payload.accessibility);
          } else if (payload.type === "error") {
            setError(payload);
          }
        } catch {
          // Ignore non-json frames
        }
      };

      ws.onerror = () => {
        setError({
          type: "error",
          code: "WEBSOCKET_ERROR",
          message: "WebSocket connection encountered an error",
          retryable: true,
        });
      };

      ws.onclose = () => {
        setIsConnected(false);
        setIsReady(false);
      };
    },
    [scheduleBufferedAction]
  );

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "stop" }));
      }
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
    setIsReady(false);
  }, []);

  const sendAudioChunk = useCallback((base64Data: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "audio", data: base64Data }));
    }
  }, []);

  const startTranslation = useCallback((targetLanguage: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({ type: "start_translation", target_language: targetLanguage })
      );
    }
  }, []);

  const stopTranslation = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "stop_translation" }));
    }
  }, []);

  const requestLiveSummary = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "request_summary" }));
    }
  }, []);

  const requestLiveAccessibility = useCallback((text: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "request_accessibility", text }));
    }
  }, []);

  const emergencyStop = useCallback(() => {
    // Instantly wipe pending production queue
    bufferQueueRef.current = [];
    setInterimSubtitle("");
    disconnect();
  }, [disconnect]);

  const togglePause = useCallback(() => {
    setIsPaused((prev) => !prev);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    isConnected,
    isReady,
    error,
    interimSubtitle,
    finalSubtitles,
    translations,
    chapters,
    summary,
    accessibility,
    bufferDelayMs,
    isPaused,
    setBufferDelayMs,
    togglePause,
    emergencyStop,
    connect,
    disconnect,
    sendAudioChunk,
    startTranslation,
    stopTranslation,
    requestLiveSummary,
    requestLiveAccessibility,
    clearError,
  };
}
