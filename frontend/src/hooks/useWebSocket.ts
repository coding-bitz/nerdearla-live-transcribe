import { useCallback, useEffect, useRef, useState } from "react";
import {
  AccessibilityData,
  ChapterData,
  ErrorPayload,
  ExecutiveSummaryData,
} from "../api/client";

export type WsConnectionStatus =
  | "DISCONNECTED"
  | "CONNECTING"
  | "CONNECTED_BACKEND"
  | "AUTHENTICATING"
  | "AUTHENTICATED"
  | "GEMINI_CONNECTING"
  | "GEMINI_READY"
  | "STREAMING"
  | "ERROR"
  | "CLOSED";

export interface ConnectOptions {
  sourceLanguage?: string;
  enableTranslation?: boolean;
  targetLanguage?: string;
}

export interface SubtitleItem {
  text: string;
  timestamp: number;
}

export interface UseWebSocketProps {
  token?: string | null;
  onAuthExpired?: () => void;
}

const MAX_RECONNECT_ATTEMPTS = 5;

export function useWebSocket({ token = null, onAuthExpired }: UseWebSocketProps = {}) {
  const [connectionStatus, setConnectionStatus] = useState<WsConnectionStatus>("DISCONNECTED");
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

  const tokenRef = useRef<string | null>(token);
  tokenRef.current = token;

  const onAuthExpiredRef = useRef<(() => void) | undefined>(onAuthExpired);
  onAuthExpiredRef.current = onAuthExpired;

  const manualDisconnectRef = useRef(false);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const activeSessionIdRef = useRef<string | null>(null);
  const activeOptionsRef = useRef<ConnectOptions>({});

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

  const cleanupSocket = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.onopen = null;
      wsRef.current.onmessage = null;
      wsRef.current.onerror = null;
      wsRef.current.onclose = null;
      try {
        wsRef.current.close();
      } catch {
        // Ignore close errors during cleanup
      }
      wsRef.current = null;
    }
  }, []);

  const internalConnect = useCallback(
    (sessionId: string, options: ConnectOptions = {}) => {
      cleanupSocket();
      setError(null);
      setIsReady(false);
      setConnectionStatus("CONNECTING");

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
        reconnectAttemptsRef.current = 0;
        setConnectionStatus("CONNECTED_BACKEND");

        // Immediately transmit authentication message
        if (tokenRef.current) {
          setConnectionStatus("AUTHENTICATING");
          ws.send(JSON.stringify({ type: "auth", token: tokenRef.current }));
        } else {
          setConnectionStatus("ERROR");
          setError({
            type: "error",
            code: "AUTH_REQUIRED",
            message: "Authentication token missing. Please sign in again.",
            retryable: false,
          });
        }
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);

          if (payload.type === "status") {
            const status = payload.status as WsConnectionStatus;
            setConnectionStatus(status);
            if (status === "GEMINI_READY") {
              setIsReady(true);
            } else if (status === "CLOSED" || status === "ERROR") {
              setIsReady(false);
            }
          } else if (payload.type === "auth_success") {
            setConnectionStatus("AUTHENTICATED");
          } else if (payload.type === "ready") {
            setIsReady(true);
            setConnectionStatus("GEMINI_READY");
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
            setConnectionStatus("ERROR");

            if (payload.code === "AUTH_EXPIRED" || payload.code === "AUTH_INVALID_TOKEN") {
              manualDisconnectRef.current = true;
              if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
                reconnectTimeoutRef.current = null;
              }
              if (onAuthExpiredRef.current) {
                onAuthExpiredRef.current();
              }
            }
          }
        } catch {
          // Ignore non-json frames
        }
      };

      ws.onerror = () => {
        setConnectionStatus("ERROR");
        setError({
          type: "error",
          code: "BACKEND_UNAVAILABLE",
          message: "Backend service is unreachable. Verify backend server is running and accessible.",
          retryable: true,
        });
      };

      ws.onclose = () => {
        setIsReady(false);

        if (manualDisconnectRef.current || !tokenRef.current) {
          setConnectionStatus("DISCONNECTED");
          return;
        }

        // Controlled exponential backoff reconnection
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current += 1;
          const attempt = reconnectAttemptsRef.current;
          const delay = Math.min(1000 * Math.pow(2, attempt - 1), 10000);
          setConnectionStatus("CONNECTING");

          reconnectTimeoutRef.current = setTimeout(() => {
            if (!manualDisconnectRef.current && activeSessionIdRef.current && tokenRef.current) {
              internalConnect(activeSessionIdRef.current, activeOptionsRef.current);
            }
          }, delay);
        } else {
          setConnectionStatus("DISCONNECTED");
          setError({
            type: "error",
            code: "RECONNECT_FAILED",
            message: "Connection to backend lost after maximum retry attempts.",
            retryable: true,
          });
        }
      };
    },
    [cleanupSocket, scheduleBufferedAction]
  );

  const connect = useCallback(
    (sessionId: string, options: ConnectOptions = {}) => {
      manualDisconnectRef.current = false;
      reconnectAttemptsRef.current = 0;
      activeSessionIdRef.current = sessionId;
      activeOptionsRef.current = options;

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      internalConnect(sessionId, options);
    },
    [internalConnect]
  );

  const disconnect = useCallback(() => {
    manualDisconnectRef.current = true;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify({ type: "stop" }));
      } catch {
        // Ignore send errors during shutdown
      }
    }

    cleanupSocket();
    setIsReady(false);
    setConnectionStatus("DISCONNECTED");
  }, [cleanupSocket]);

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
    connectionStatus,
    isConnected: connectionStatus !== "DISCONNECTED" && connectionStatus !== "CLOSED",
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
