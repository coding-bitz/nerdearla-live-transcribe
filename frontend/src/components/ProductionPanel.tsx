import React from "react";

interface ProductionPanelProps {
  bufferDelayMs: number;
  setBufferDelayMs: (ms: number) => void;
  isPaused: boolean;
  togglePause: () => void;
  emergencyStop: () => void;
  chunkCount: number;
  volumeRms: number;
  isConnected: boolean;
}

export const ProductionPanel: React.FC<ProductionPanelProps> = ({
  bufferDelayMs,
  setBufferDelayMs,
  isPaused,
  togglePause,
  emergencyStop,
  chunkCount,
  volumeRms,
  isConnected,
}) => {
  return (
    <div className="panel production-panel">
      <div className="panel-header">
        <h3>Broadcast Production Controls</h3>
        <span className={`badge ${isPaused ? "badge-warning" : "badge-success"}`}>
          {isPaused ? "BROADCAST PAUSED" : "LIVE AIRING"}
        </span>
      </div>

      <div className="production-controls-grid">
        <div className="control-group">
          <label>Broadcast Delay: {(bufferDelayMs / 1000).toFixed(1)}s</label>
          <div className="delay-presets">
            {[0, 1000, 2000, 3000, 5000].map((ms) => (
              <button
                key={ms}
                className={`btn btn-sm ${bufferDelayMs === ms ? "btn-primary" : "btn-outline"}`}
                onClick={() => setBufferDelayMs(ms)}
              >
                {ms === 0 ? "0s (Real-time)" : `${ms / 1000}s`}
              </button>
            ))}
          </div>
        </div>

        <div className="control-group action-buttons">
          <button
            className={`btn ${isPaused ? "btn-success" : "btn-secondary"}`}
            disabled={!isConnected}
            onClick={togglePause}
          >
            {isPaused ? "Resume Broadcast" : "Pause Output"}
          </button>

          <button
            className="btn btn-danger"
            disabled={!isConnected}
            onClick={emergencyStop}
          >
            EMERGENCY CUT
          </button>
        </div>

        <div className="metrics-row">
          <div className="metric-item">
            <span>Audio Chunks:</span>
            <strong>{chunkCount}</strong>
          </div>
          <div className="metric-item">
            <span>RMS Level:</span>
            <strong>{(volumeRms * 100).toFixed(1)}%</strong>
          </div>
          <div className="metric-item">
            <span>Buffer Delay:</span>
            <strong>{bufferDelayMs} ms</strong>
          </div>
        </div>
      </div>
    </div>
  );
};
