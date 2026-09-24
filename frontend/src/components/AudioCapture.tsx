import React from "react";

interface AudioCaptureProps {
  sessionId: string;
  setSessionId: (id: string) => void;
  sourceLanguage: string;
  setSourceLanguage: (lang: string) => void;
  isConnected: boolean;
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
  isConnected,
  isReady,
  isRecording,
  volume,
  onConnect,
  onDisconnect,
  onStartCapture,
  onStopCapture,
}) => {
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
          <span className={`badge ${isConnected ? (isReady ? "badge-success" : "badge-warning") : "badge-inactive"}`}>
            {isConnected ? (isReady ? "Ready" : "Connecting...") : "Disconnected"}
          </span>
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

        {isConnected && isReady && (
          !isRecording ? (
            <button className="btn btn-success" onClick={onStartCapture}>
              Start Microphone
            </button>
          ) : (
            <button className="btn btn-warning" onClick={onStopCapture}>
              Stop Microphone
            </button>
          )
        )}
      </div>
    </div>
  );
};
