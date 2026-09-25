import React from "react";
import { WsConnectionStatus } from "../hooks/useWebSocket";

interface AudioCaptureProps {
  sessionId: string;
  setSessionId: (id: string) => void;
  sourceLanguage: string;
  setSourceLanguage: (lang: string) => void;
  connectionStatus: WsConnectionStatus;
  isReady: boolean;
  isRecording: boolean;
  volume: number;
  onConnect: () => void;
  onDisconnect: () => void;
  onStartCapture: () => void;
  onStopCapture: () => void;
}

export const AudioCapture: React.FC<AudioCaptureProps> = ({
  sessionId,
  setSessionId,
  sourceLanguage,
  setSourceLanguage,
  connectionStatus,
  isRecording,
  volume,
  onConnect,
  onDisconnect,
  onStartCapture,
  onStopCapture,
}) => {
  const isConnected = connectionStatus !== "DISCONNECTED" && connectionStatus !== "CLOSED";

  const renderStatusBadge = () => {
    switch (connectionStatus) {
      case "DISCONNECTED":
        return <span className="badge badge-inactive">Disconnected</span>;
      case "CONNECTING":
        return <span className="badge badge-warning">Connecting to Backend...</span>;
      case "CONNECTED_BACKEND":
        return <span className="badge badge-info">Connected to Backend</span>;
      case "GEMINI_CONNECTING":
        return <span className="badge badge-warning">Connecting to Gemini...</span>;
      case "GEMINI_READY":
        return <span className="badge badge-success">Gemini Ready</span>;
      case "STREAMING":
        return <span className="badge badge-success">Streaming Audio</span>;
      case "ERROR":
        return <span className="badge badge-danger">Connection Error</span>;
      case "CLOSED":
        return <span className="badge badge-inactive">Session Closed</span>;
    }
  };

  const canStartMicrophone = connectionStatus === "GEMINI_READY" && !isRecording;

  return (
    <div className="panel audio-capture-panel">
      <h3>Audio & Session Controls</h3>

      <div className="form-row">
        <label htmlFor="sessionId">Session ID:</label>
        <input
          id="sessionId"
          type="text"
          value={sessionId}
          disabled={isConnected}
          onChange={(e) => setSessionId(e.target.value)}
          placeholder="e.g. nerdearla-room-1"
        />
      </div>

      <div className="form-row">
        <label htmlFor="sourceLang">Source Language:</label>
        <select
          id="sourceLang"
          value={sourceLanguage}
          disabled={isConnected}
          onChange={(e) => setSourceLanguage(e.target.value)}
        >
          <option value="es-ES">Spanish (es-ES)</option>
          <option value="en-US">English (en-US)</option>
          <option value="pt-BR">Portuguese (pt-BR)</option>
        </select>
      </div>

      <div className="status-indicators">
        <div className="status-item">
          <span>Connection:</span>
          {renderStatusBadge()}
        </div>
        <div className="status-item">
          <span>Format:</span>
          <span className="badge badge-info">PCM16 @ 16kHz (Mono)</span>
        </div>
      </div>

      <div className="volume-meter-wrapper">
        <div className="volume-label">Mic Level:</div>
        <div className="volume-bar-track">
          <div
            className="volume-bar-fill"
            style={{ width: `${Math.round(Math.min(100, volume * 100))}%` }}
          />
        </div>
      </div>

      <div className="button-group">
        {!isConnected ? (
          <button className="btn btn-primary" onClick={onConnect} disabled={!sessionId.trim()}>
            Connect Session
          </button>
        ) : (
          <button className="btn btn-secondary" onClick={onDisconnect}>
            Disconnect
          </button>
        )}

        {canStartMicrophone && (
          <button className="btn btn-success" onClick={onStartCapture}>
            Start Microphone
          </button>
        )}

        {isRecording && (
          <button className="btn btn-warning" onClick={onStopCapture}>
            Stop Microphone
          </button>
        )}
      </div>
    </div>
  );
};
