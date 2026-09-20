"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  authLogout,
  authMe,
  loginWithGoogleAccessToken,
  type AuthUser,
} from "@/lib/api";

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
  const menuRef = useRef<HTMLDivElement>(null);
  const tokenClientRef = useRef<TokenClient | null>(null);

  const refresh = useCallback(async () => {
    const me = await authMe();
    setUser(me.user);
    setClientId(me.google_client_id);
    setReady(true);
  }, []);

  useEffect(() => {
    void refresh().catch(() => setReady(true));
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
                setMenuOpen(false);
              } catch (err) {
                setError(err instanceof Error ? err.message : "Нэвтэрч чадсангүй");
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
  }, [clientId, user]);

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
    } finally {
      setBusy(false);
    }
  }

  if (!ready) return null;

  if (user) {
    return (
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
    );
  }

  if (!clientId) return null;

  return (
    <div className="mw-auth">
      <button
        type="button"
        className="mw-btn mw-auth-login"
        onClick={startGoogleLogin}
        disabled={busy}
      >
        {busy ? "…" : "Нэвтрэх"}
      </button>
      {error ? <span className="mw-auth-error">{error}</span> : null}
    </div>
  );
}
