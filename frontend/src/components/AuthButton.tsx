"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { authLogout, authMe, loginWithGoogle, type AuthUser } from "@/lib/api";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
            auto_select?: boolean;
            cancel_on_tap_outside?: boolean;
          }) => void;
          prompt: (momentListener?: (notification: {
            isNotDisplayed: () => boolean;
            isSkippedMoment: () => boolean;
            getNotDisplayedReason?: () => string;
          }) => void) => void;
          renderButton: (
            parent: HTMLElement,
            options: Record<string, string | number | boolean>,
          ) => void;
        };
      };
    };
  }
}

function loadGis(): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  if (window.google?.accounts?.id) return Promise.resolve();
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

  async function onCredential(credential: string) {
    setBusy(true);
    setError(null);
    try {
      const result = await loginWithGoogle(credential);
      setUser(result.user);
      setMenuOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Нэвтэрч чадсангүй");
    } finally {
      setBusy(false);
    }
  }

  async function startGoogleLogin() {
    if (!clientId || busy) return;
    setBusy(true);
    setError(null);
    try {
      await loadGis();
      if (!window.google?.accounts?.id) throw new Error("Google бэлэн биш");
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: (response) => {
          void onCredential(response.credential);
        },
        auto_select: false,
        cancel_on_tap_outside: true,
      });
      window.google.accounts.id.prompt((notification) => {
        if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
          setBusy(false);
          setError("Google цонх нээгдсэнгүй. Popup/cookie зөвшөөрнө үү.");
        }
      });
    } catch (err) {
      setBusy(false);
      setError(err instanceof Error ? err.message : "Нэвтэрч чадсангүй");
    }
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
        onClick={() => void startGoogleLogin()}
        disabled={busy}
      >
        {busy ? "…" : "Нэвтрэх"}
      </button>
      {error ? <span className="mw-auth-error">{error}</span> : null}
    </div>
  );
}
