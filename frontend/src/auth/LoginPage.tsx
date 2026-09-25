import { useState, FormEvent } from "react";
import { useAuth } from "./AuthContext";

export function LoginPage() {
  const { login, error, clearError, authState } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) return;

    setIsSubmitting(true);
    try {
      await login(username, password);
    } catch {
      // Error handled in AuthContext
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="login-page-container">
      <div className="login-card">
        <div className="login-header">
          <h2>Nerdearla Live Subtitles</h2>
          <p className="login-subtitle">Operator Authentication</p>
        </div>

        {error && (
          <div className="error-banner">
            <strong>Authentication Failed:</strong> {error}
            <button className="btn btn-sm btn-outline error-dismiss" onClick={clearError}>
              Dismiss
            </button>
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="login-username">Operator Username</label>
            <input
              id="login-username"
              type="text"
              autoComplete="username"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter operator username"
              disabled={isSubmitting || authState === "AUTH_LOADING"}
            />
          </div>

          <div className="form-group">
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              disabled={isSubmitting || authState === "AUTH_LOADING"}
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary login-btn"
            disabled={isSubmitting || authState === "AUTH_LOADING" || !username.trim() || !password}
          >
            {isSubmitting || authState === "AUTH_LOADING" ? "Authenticating..." : "Sign In"}
          </button>
        </form>

        <div className="login-footer">
          <span className="badge badge-outline">Stateless Argon2id + JWT</span>
          <span className="badge badge-info">Google Cloud Run</span>
        </div>
      </div>
    </div>
  );
}
