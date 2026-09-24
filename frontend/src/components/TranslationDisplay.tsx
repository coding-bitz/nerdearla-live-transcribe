import React, { useEffect, useRef } from "react";
import { SubtitleItem } from "../hooks/useWebSocket";

interface TranslationDisplayProps {
  translations: SubtitleItem[];
  enableTranslation: boolean;
  targetLanguage: string;
  isConnected: boolean;
  onToggleTranslation: (enable: boolean) => void;
  onChangeTargetLanguage: (lang: string) => void;
}

export const TranslationDisplay: React.FC<TranslationDisplayProps> = ({
  translations,
  enableTranslation,
  targetLanguage,
  isConnected,
  onToggleTranslation,
  onChangeTargetLanguage,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [translations]);

  return (
    <div className="panel translation-display-panel">
      <div className="panel-header">
        <h3>Live Translation</h3>
        <div className="translation-controls">
          <select
            value={targetLanguage}
            disabled={!isConnected}
            onChange={(e) => onChangeTargetLanguage(e.target.value)}
          >
            <option value="es">Spanish (es)</option>
            <option value="en">English (en)</option>
            <option value="pt">Portuguese (pt)</option>
            <option value="fr">French (fr)</option>
          </select>

          <button
            className={`btn btn-sm ${enableTranslation ? "btn-warning" : "btn-outline"}`}
            disabled={!isConnected}
            onClick={() => onToggleTranslation(!enableTranslation)}
          >
            {enableTranslation ? "Disable Translation" : "Enable Translation"}
          </button>
        </div>
      </div>

      <div className="subtitles-scroll-container" ref={scrollRef}>
        {!enableTranslation ? (
          <div className="empty-state">
            Translation is currently turned off. Enable translation above to start real-time speech translation.
          </div>
        ) : translations.length === 0 ? (
          <div className="empty-state">
            Waiting for translated speech events...
          </div>
        ) : (
          translations.map((sub, index) => (
            <div key={`${sub.timestamp}-${index}`} className="subtitle-entry translation-subtitle">
              <span className="subtitle-time">
                {new Date(sub.timestamp).toLocaleTimeString([], { hour12: false, minute: "2-digit", second: "2-digit" })}
              </span>
              <span className="subtitle-text">{sub.text}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
