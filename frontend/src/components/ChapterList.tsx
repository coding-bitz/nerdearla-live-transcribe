import React from "react";
import { ChapterData } from "../api/client";

interface ChapterListProps {
  chapters: ChapterData[];
}

export const ChapterList: React.FC<ChapterListProps> = ({ chapters }) => {
  return (
    <div className="panel chapter-list-panel">
      <div className="panel-header">
        <h3>Smart Chapters</h3>
        <span className="badge badge-info">{chapters.length} detected</span>
      </div>

      <div className="chapters-container">
        {chapters.length === 0 ? (
          <div className="empty-state">
            No chapters detected yet. Chapters are automatically detected by AI every ~30s of new presentation content.
          </div>
        ) : (
          <ul className="chapters-list">
            {chapters.map((ch, index) => (
              <li key={`${ch.timestamp}-${index}`} className="chapter-item">
                <span className="chapter-number">{index + 1}</span>
                <div className="chapter-content">
                  <strong className="chapter-title">{ch.title}</strong>
                  <span className="chapter-timestamp">
                    {new Date(ch.timestamp).toLocaleTimeString([], {
                      hour12: false,
                      minute: "2-digit",
                      second: "2-digit",
                    })}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};
