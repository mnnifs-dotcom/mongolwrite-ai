"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  authLogout,
  authMe,
  loginWithGoogleAccessToken,
  type AuthUser,
} from "@/lib/api";
import {
  DeviceLimitDialog,
  isDeviceLimitMessage,
} from "@/components/DeviceLimitDialog";

type TokenClient = {
  requestAccessToken: (override?: { prompt?: string }) => void;
};

declare global {
  interface Window {
    google?: {
      accounts: {
        oauth2: {
          initTokenClient: (config: {
            client_id: string;
            scope: string;
            callback: (response: { access_token?: string; error?: string }) => void;
            error_callback?: (error: { type?: string; message?: string }) => void;
          }) => TokenClient;
        };
      };
    };
  }
}

function loadGis(): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  if (window.google?.accounts?.oauth2) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const existing = document.querySelector('script[data-mw-gis="1"]');
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("GIS load failed")));
      return;
    }
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.dataset.mwGis = "1";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("GIS load failed"));
    document.head.appendChild(script);
  });
}

export function AuthButton() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [clientId, setClientId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deviceLimitOpen, setDeviceLimitOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const tokenClientRef = useRef<TokenClient | null>(null);

  const showAuthError = useCallback((message: string) => {
    if (isDeviceLimitMessage(message)) {
      setError(null);
      setDeviceLimitOpen(true);
      return;
    }
    setError(message);
  }, []);

  const refresh = useCallback(async () => {
    try {
      const me = await authMe();
      setUser(me.user);
      setClientId(me.google_client_id);
      setError(null);
      setDeviceLimitOpen(false);
    } catch (err) {
      setUser(null);
      const message = err instanceof Error ? err.message : "Нэвтэрч чадсангүй";
      if (isDeviceLimitMessage(message)) {
        try {
          await authLogout();
        } catch {
          /* ignore */
        }
      }
      showAuthError(message);
      try {
        const { getSettings } = await import("@/lib/api");
        const settings = await getSettings();
        if (settings.google_client_id) setClientId(settings.google_client_id);
      } catch {
        /* ignore */
      }
    } finally {
      setReady(true);
    }
  }, [showAuthError]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!menuOpen) return;
    const onDoc = (event: MouseEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [menuOpen]);

  useEffect(() => {
    if (!clientId || user) return;
    let cancelled = false;
    void (async () => {
      try {
        await loadGis();
        if (cancelled || !window.google?.accounts?.oauth2) return;
        tokenClientRef.current = window.google.accounts.oauth2.initTokenClient({
          client_id: clientId,
          scope: "openid email profile",
          callback: (response) => {
            if (response.error || !response.access_token) {
              setBusy(false);
              if (response.error && response.error !== "popup_closed_by_user") {
                setError("Нэвтэрч чадсангүй");
              }
              return;
            }
            void (async () => {
              try {
                const result = await loginWithGoogleAccessToken(response.access_token!);
                setUser(result.user);
                setError(null);
                setDeviceLimitOpen(false);
                setMenuOpen(false);
                window.dispatchEvent(new Event("mw-auth-changed"));
              } catch (err) {
                showAuthError(err instanceof Error ? err.message : "Нэвтэрч чадсангүй");
              } finally {
                setBusy(false);
              }
            })();
          },
          error_callback: () => {
            setBusy(false);
          },
        });
      } catch {
        if (!cancelled) setError("Google бэлэн биш");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [clientId, user, showAuthError]);

  function startGoogleLogin() {
    if (!clientId || busy) return;
    setBusy(true);
    setError(null);
    const client = tokenClientRef.current;
    if (!client) {
      setBusy(false);
      setError("Google бэлэн биш");
      return;
    }
    client.requestAccessToken({ prompt: "select_account" });
  }

  async function onLogout() {
    setBusy(true);
    try {
      await authLogout();
      setUser(null);
      setMenuOpen(false);
      window.dispatchEvent(new Event("mw-auth-changed"));
    } finally {
      setBusy(false);
    }
  }

  const dialog = (
    <DeviceLimitDialog
      open={deviceLimitOpen}
      onClose={() => setDeviceLimitOpen(false)}
    />
  );

  if (!ready) return dialog;

  if (user) {
    return (
      <>
        <div className="mw-auth" ref={menuRef}>
          <button
            type="button"
            className="mw-auth-user"
            onClick={() => setMenuOpen((open) => !open)}
            aria-expanded={menuOpen}
          >
            {user.picture ? (
              <img src={user.picture} alt="" className="mw-auth-avatar" referrerPolicy="no-referrer" />
            ) : (
              <span className="mw-auth-initial">{(user.name || user.email || "?").slice(0, 1)}</span>
            )}
            <span className="mw-auth-name">{user.name || user.email}</span>
          </button>
          {menuOpen ? (
            <div className="mw-auth-menu">
              <p className="mw-auth-plan">{user.plan_name}</p>
              <p className="mw-auth-email">{user.email}</p>
              <a href="/tolbor" className="mw-auth-upgrade">
                Төлбөрийн багц
              </a>
              <button type="button" className="mw-btn" onClick={() => void onLogout()} disabled={busy}>
                Гарах
              </button>
            </div>
          ) : null}
        </div>
        {dialog}
      </>
    );
  }

  if (!clientId) return dialog;

  return (
    <>
      <div className="mw-auth">
        <button
          type="button"
          className="mw-auth-login"
          onClick={startGoogleLogin}
          disabled={busy}
          aria-label="Google-ээр нэвтрэх"
          title="Google бүртгэлээр нэвтрэх"
        >
          <span className="mw-auth-google" aria-hidden>
            <svg viewBox="0 0 24 24" width="18" height="18">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18A10.96 10.96 0 0 0 1 12c0 1.77.42 3.45 1.18 4.93l3.66-2.84z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
          </span>
          <span className="mw-auth-login-text">
            {busy ? "Нэвтэрч байна…" : "Нэвтрэх"}
          </span>
        </button>
        {error ? <span className="mw-auth-error">{error}</span> : null}
      </div>
      {dialog}
    </>
  );
}
