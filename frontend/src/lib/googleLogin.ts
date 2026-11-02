"use client";

import { loginWithGoogleAccessToken, type AuthUser } from "@/lib/api";

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

/**
 * Open Google account picker and exchange the access token for a MongolWrite session.
 */
export async function loginWithGooglePopup(clientId: string): Promise<AuthUser> {
  if (!clientId.trim()) {
    throw new Error("Google нэвтрэлт бэлэн биш");
  }
  await loadGis();
  if (!window.google?.accounts?.oauth2) {
    throw new Error("Google бэлэн биш");
  }

  return new Promise<AuthUser>((resolve, reject) => {
    const client = window.google!.accounts.oauth2.initTokenClient({
      client_id: clientId,
      scope: "openid email profile",
      callback: (response) => {
        if (response.error || !response.access_token) {
          if (response.error === "popup_closed_by_user" || response.error === "access_denied") {
            reject(new Error("Нэвтрэлт цуцлагдлаа"));
            return;
          }
          reject(new Error("Нэвтэрч чадсангүй"));
          return;
        }
        void loginWithGoogleAccessToken(response.access_token)
          .then((result) => {
            window.dispatchEvent(new Event("mw-auth-changed"));
            resolve(result.user);
          })
          .catch((err) => {
            reject(err instanceof Error ? err : new Error("Нэвтэрч чадсангүй"));
          });
      },
      error_callback: () => {
        reject(new Error("Нэвтрэлт цуцлагдлаа"));
      },
    });
    client.requestAccessToken({ prompt: "select_account" });
  });
}
