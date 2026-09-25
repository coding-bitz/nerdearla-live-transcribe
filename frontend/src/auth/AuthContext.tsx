import { createContext, useCallback, useContext, useState, ReactNode } from "react";
import { loginUser } from "./authApi";

export type AuthState = "AUTH_LOADING" | "UNAUTHENTICATED" | "AUTHENTICATED" | "AUTH_ERROR";

export interface AuthContextType {
  authState: AuthState;
  token: string | null;
  username: string | null;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  // Access token is strictly held in memory and never stored in localStorage or cookies
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [authState, setAuthState] = useState<AuthState>("UNAUTHENTICATED");
  const [error, setError] = useState<string | null>(null);

  const login = useCallback(async (user: string, pass: string) => {
    setAuthState("AUTH_LOADING");
    setError(null);
    try {
      const res = await loginUser(user, pass);
      setToken(res.access_token);
      setUsername(user.trim());
      setAuthState("AUTHENTICATED");
    } catch (err: any) {
      setToken(null);
      setUsername(null);
      setAuthState("AUTH_ERROR");
      setError(err.message || "Invalid username or password");
      throw err;
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUsername(null);
    setAuthState("UNAUTHENTICATED");
    setError(null);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
    if (authState === "AUTH_ERROR") {
      setAuthState("UNAUTHENTICATED");
    }
  }, [authState]);

  return (
    <AuthContext.Provider
      value={{
        authState,
        token,
        username,
        error,
        login,
        logout,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
