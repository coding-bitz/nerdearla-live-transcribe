import { useState } from "react";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { LoginPage } from "./auth/LoginPage";
import { AccessibilityToggle } from "./components/AccessibilityToggle";
import { AudioCapture } from "./components/AudioCapture";
import { ChapterList } from "./components/ChapterList";
import { ProductionPanel } from "./components/ProductionPanel";
import { SubtitleDisplay } from "./components/SubtitleDisplay";
import { SummaryView } from "./components/SummaryView";
import { TranslationDisplay } from "./components/TranslationDisplay";
import { useAudioCapture } from "./hooks/useAudioCapture";
import { useWebSocket } from "./hooks/useWebSocket";

function AuthenticatedLiveApp() {
  const { username, logout } = useAuth();

  const [sessionId, setSessionId] = useState("nerdearla-main-room");
  const [sourceLanguage, setSourceLanguage] = useState("es-ES");
  const [enableTranslation, setEnableTranslation] = useState(false);
  const [targetLanguage, setTargetLanguage] = useState("en");

  const {
    connectionStatus,
    isConnected,
    isReady,
    error: wsError,
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
    emergencyStop: wsEmergencyStop,
    connect,
    disconnect,
    sendAudioChunk,
    startTranslation,
    stopTranslation,
    requestLiveSummary,
    requestLiveAccessibility,
    clearError,
  } = useWebSocket();

  const {
    isRecording,
    error: audioError,
    volume,
    startCapture,
    stopCapture,
  } = useAudioCapture();

  const handleConnect = () => {
    connect(sessionId, {
      sourceLanguage,
      enableTranslation,
      targetLanguage,
    });
  };

  const handleDisconnect = () => {
    stopCapture();
    disconnect();
  };

  const handleLogout = () => {
    stopCapture();
    disconnect();
    logout();
  };

  const handleStartCapture = async () => {
    try {
      await startCapture((_pcmBytes, base64Data) => {
        sendAudioChunk(base64Data);
      });
    } catch {
      // Audio hook sets error state
    }
  };

  const handleToggleTranslation = (enable: boolean) => {
    setEnableTranslation(enable);
    if (enable) {
      startTranslation(targetLanguage);
    } else {
      stopTranslation();
    }
  };

  const handleChangeTargetLanguage = (lang: string) => {
    setTargetLanguage(lang);
    if (enableTranslation) {
      startTranslation(lang);
    }
  };

  const handleEmergencyStop = () => {
    stopCapture();
    wsEmergencyStop();
  };

  const latestSubtitleText =
    finalSubtitles.length > 0 ? finalSubtitles[finalSubtitles.length - 1].text : "";

  const activeError = wsError ? `${wsError.code}: ${wsError.message}` : audioError;

  return (
    <div className="app-container">
      <header className="app-header">
        <div>
          <h1>Nerdearla Live Subtitles</h1>
        </div>

        <div className="header-user-controls">
          <span className="user-badge">Operator: {username}</span>
          <button className="btn btn-sm btn-outline" onClick={handleLogout}>
            Sign Out
          </button>
          <div className="header-badges">
            <span className="badge badge-info">Google Cloud Run</span>
            <span className="badge badge-outline">Gemini Enterprise Live</span>
          </div>
        </div>
      </header>

      {activeError && (
        <div className="global-error-banner">
          <div>
            <span className="error-code">Error:</span>
            <span>{activeError}</span>
          </div>
          <button className="btn btn-sm btn-outline" onClick={clearError}>
            Dismiss
          </button>
        </div>
      )}

      <div className="top-controls-grid">
        <AudioCapture
          sessionId={sessionId}
          setSessionId={setSessionId}
          sourceLanguage={sourceLanguage}
          setSourceLanguage={setSourceLanguage}
          connectionStatus={connectionStatus}
          isReady={isReady}
          isRecording={isRecording}
          volume={volume}
          onConnect={handleConnect}
          onDisconnect={handleDisconnect}
          onStartCapture={handleStartCapture}
          onStopCapture={stopCapture}
        />

        <ProductionPanel
          bufferDelayMs={bufferDelayMs}
          setBufferDelayMs={setBufferDelayMs}
          isPaused={isPaused}
          togglePause={togglePause}
          emergencyStop={handleEmergencyStop}
          chunkCount={finalSubtitles.length}
          volumeRms={volume}
          isConnected={isConnected}
        />
      </div>

      <div className="subtitles-grid">
        <SubtitleDisplay
          finalSubtitles={finalSubtitles}
          interimSubtitle={interimSubtitle}
          isReady={isReady}
        />

        <TranslationDisplay
          translations={translations}
          enableTranslation={enableTranslation}
          targetLanguage={targetLanguage}
          isConnected={isConnected}
          onToggleTranslation={handleToggleTranslation}
          onChangeTargetLanguage={handleChangeTargetLanguage}
        />
      </div>

      <div className="details-grid">
        <ChapterList chapters={chapters} />

        <SummaryView
          summary={summary}
          onRequestSummary={requestLiveSummary}
          hasTranscripts={finalSubtitles.length > 0}
          isConnected={isConnected}
        />

        <AccessibilityToggle
          accessibility={accessibility}
          latestSubtitleText={latestSubtitleText}
          onRequestAccessibility={requestLiveAccessibility}
          isConnected={isConnected}
        />
      </div>
    </div>
  );
}

function AppRoot() {
  const { authState } = useAuth();

  if (authState !== "AUTHENTICATED") {
    return <LoginPage />;
  }

  return <AuthenticatedLiveApp />;
}

export function App() {
  return (
    <AuthProvider>
      <AppRoot />
    </AuthProvider>
  );
}

export default App;
