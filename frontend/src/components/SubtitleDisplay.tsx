import React, { useEffect, useRef } from "react";
import { SubtitleItem } from "../hooks/useWebSocket";

interface SubtitleDisplayProps {
  finalSubtitles: SubtitleItem[];
  interimSubtitle: string;
  isReady: boolean;
}

export const SubtitleDisplay: React.FC<SubtitleDisplayProps> = ({
  finalSubtitles,
  interimSubtitle,
  isReady,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [finalSubtitles, interimSubtitle]);

  return (
    <div className="panel subtitle-display-panel">
      <div className="panel-header">
        <h3>Live Subtitles (Original)</h3>
        <span className="badge badge-info">{finalSubtitles.length} segments</span>
      </div>

      <div className="subtitles-scroll-container" ref={scrollRef}>
        {finalSubtitles.length === 0 && !interimSubtitle && (
          <div className="empty-state">
            {isReady ? "Awaiting spoken audio from microphone..." : "Connect session to begin live transcription."}
          </div>
        )}

        {finalSubtitles.map((sub, index) => (
          <div key={`${sub.timestamp}-${index}`} className="subtitle-entry final-subtitle">
            <span className="subtitle-time">
              {new Date(sub.timestamp).toLocaleTimeString([], { hour12: false, minute: "2-digit", second: "2-digit" })}
            </span>
            <span className="subtitle-text">{sub.text}</span>
          </div>
        ))}

        {interimSubtitle && (
          <div className="subtitle-entry interim-subtitle">
            <span className="subtitle-time">live</span>
            <span className="subtitle-text">{interimSubtitle}</span>
          </div>
        )}
      </div>
    </div>
  );
};
