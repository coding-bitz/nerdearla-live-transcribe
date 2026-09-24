import React, { useState } from "react";
import { AccessibilityData } from "../api/client";

interface AccessibilityToggleProps {
  accessibility: AccessibilityData | null;
  latestSubtitleText: string;
  onRequestAccessibility: (text: string) => Promise<void> | void;
  isConnected: boolean;
}

export const AccessibilityToggle: React.FC<AccessibilityToggleProps> = ({
  accessibility,
  latestSubtitleText,
  onRequestAccessibility,
  isConnected,
}) => {
  const [enabled, setEnabled] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleEnhance = async () => {
    if (!latestSubtitleText.trim()) return;
    setIsLoading(true);
    setLocalError(null);
    try {
      await onRequestAccessibility(latestSubtitleText);
    } catch (err: any) {
      setLocalError(err.message || "Failed to generate accessibility enhancement");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="panel accessibility-panel">
      <div className="panel-header">
        <h3>Accessibility Enhancements</h3>
        <label className="switch-label">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
          />
          <span>Accessibility Mode</span>
        </label>
      </div>

      {enabled && (
        <div className="accessibility-controls">
          <button
            className="btn btn-sm btn-outline"
            disabled={!latestSubtitleText || isLoading || !isConnected}
            onClick={handleEnhance}
          >
            {isLoading ? "Enhancing..." : "Enhance Latest Subtitle"}
          </button>

          {localError && (
            <div className="error-banner">
              <strong>No se pudo generar esta función.</strong>
              <p>{localError}</p>
            </div>
          )}

          {accessibility ? (
            <div className="accessibility-result">
              <div className="enhanced-text-card">
                <strong>Enhanced Text:</strong>
                <p className="enhanced-text">{accessibility.enhancedText}</p>
              </div>

              {accessibility.soundDescriptions && accessibility.soundDescriptions.length > 0 && (
                <div className="sound-descriptions">
                  <strong>Non-speech cues:</strong>
                  {accessibility.soundDescriptions.map((desc, i) => (
                    <span key={i} className="badge badge-warning">
                      {desc}
                    </span>
                  ))}
                </div>
              )}

              {accessibility.speakerTone && (
                <div className="speaker-tone">
                  <strong>Speaker tone:</strong> {accessibility.speakerTone}
                </div>
              )}
            </div>
          ) : (
            <div className="empty-state">
              {latestSubtitleText
                ? "Click 'Enhance Latest Subtitle' to add descriptive acoustic cues and punctuation."
                : "No subtitles available to enhance yet."}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
