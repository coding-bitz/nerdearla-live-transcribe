import React, { useState } from "react";
import { ExecutiveSummaryData } from "../api/client";

interface SummaryViewProps {
  summary: ExecutiveSummaryData | null;
  onRequestSummary: () => Promise<void> | void;
  hasTranscripts: boolean;
  isConnected: boolean;
}

export const SummaryView: React.FC<SummaryViewProps> = ({
  summary,
  onRequestSummary,
  hasTranscripts,
  isConnected,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setIsLoading(true);
    setLocalError(null);
    try {
      await onRequestSummary();
    } catch (err: any) {
      setLocalError(err.message || "Failed to generate executive summary");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="panel summary-view-panel">
      <div className="panel-header">
        <h3>Executive Summary</h3>
        <button
          className="btn btn-sm btn-primary"
          disabled={!hasTranscripts || isLoading || !isConnected}
          onClick={handleGenerate}
        >
          {isLoading ? "Generating with Gemini..." : "Generate Summary"}
        </button>
      </div>

      {localError && (
        <div className="error-banner">
          <strong>Summary Error:</strong> {localError}
        </div>
      )}

      {!summary ? (
        <div className="empty-state">
          {hasTranscripts
            ? "Transcript segments are available. Click 'Generate Summary' to produce an executive overview."
            : "Collect transcript segments during the talk to generate an executive summary."}
        </div>
      ) : (
        <div className="summary-content">
          <h4 className="summary-title">{summary.title}</h4>

          <div className="summary-metadata">
            <span className="badge badge-info">Level: {summary.technicalLevel}</span>
            <span className="badge badge-info">Read time: {summary.estimatedReadingTime}</span>
            {summary.hashtags.map((tag) => (
              <span key={tag} className="badge badge-outline">
                {tag}
              </span>
            ))}
          </div>

          <p className="summary-body">{summary.summary}</p>

          <div className="summary-section">
            <h5>Key Takeaways:</h5>
            <ul>
              {summary.keyTakeaways.map((takeaway, i) => (
                <li key={i}>{takeaway}</li>
              ))}
            </ul>
          </div>

          <div className="summary-section">
            <h5>Topics:</h5>
            <div className="tags-container">
              {summary.topics.map((topic, i) => (
                <span key={i} className="tag">
                  {topic}
                </span>
              ))}
            </div>
          </div>

          <div className="summary-section">
            <h5>Mentioned Resources:</h5>
            {summary.resources && summary.resources.length > 0 ? (
              <ul>
                {summary.resources.map((res, i) => (
                  <li key={i}>{res}</li>
                ))}
              </ul>
            ) : (
              <p className="empty-state-text">No external tools or links were explicitly mentioned.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
