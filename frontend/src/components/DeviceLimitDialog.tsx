"use client";

import { useEffect } from "react";
import { createPortal } from "react-dom";

export const DEVICE_LIMIT_TITLE = "Төхөөрөмжийн хязгаар";
export const DEVICE_LIMIT_BODY =
  "Нэг бүртгэлээр зэрэг зөвхөн 2 төхөөрөмжөөс нэвтэрч болно.";
export const DEVICE_LIMIT_HINT =
  "Өөр төхөөрөмж дээрээсээ «Гарах» дарж нэвтрэлтээ хаагаад энд дахин оролдоно уу.";
/** Fallback when API omits detail — keep in sync with backend copy. */
export const DEVICE_LIMIT_FALLBACK = `${DEVICE_LIMIT_BODY} ${DEVICE_LIMIT_HINT}`;

export function isDeviceLimitMessage(message: string | null | undefined): boolean {
  if (!message) return false;
  const text = message.toLocaleLowerCase("mn");
  if (text.includes("device_limit")) return true;
  if (text.includes("2 төхөөрөмж") || text.includes("хоёр төхөөрөмж")) return true;
  return text.includes("төхөөрөмж") && text.includes("хязгаар");
}

type Props = {
  open: boolean;
  onClose: () => void;
};

export function DeviceLimitDialog({ open, onClose }: Props) {
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open || typeof document === "undefined") return null;

  return createPortal(
    <div
      className="mw-device-overlay"
      role="presentation"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className="mw-device-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="mw-device-limit-title"
        aria-describedby="mw-device-limit-body"
      >
        <button
          type="button"
          className="mw-device-close"
          onClick={onClose}
          aria-label="Хаах"
        >
          ×
        </button>
        <div className="mw-device-icon" aria-hidden>
          <svg viewBox="0 0 56 56" width="56" height="56" fill="none">
            <rect
              x="8"
              y="14"
              width="26"
              height="32"
              rx="5"
              stroke="currentColor"
              strokeWidth="2"
            />
            <rect
              x="22"
              y="8"
              width="26"
              height="32"
              rx="5"
              fill="color-mix(in srgb, var(--accent) 12%, #fff)"
              stroke="currentColor"
              strokeWidth="2"
            />
            <circle cx="35" cy="34" r="2" fill="currentColor" />
          </svg>
        </div>
        <h2 id="mw-device-limit-title">{DEVICE_LIMIT_TITLE}</h2>
        <p id="mw-device-limit-body" className="mw-device-lead">
          {DEVICE_LIMIT_BODY}
        </p>
        <p className="mw-device-hint">{DEVICE_LIMIT_HINT}</p>
        <button type="button" className="mw-device-ok" onClick={onClose}>
          Ойлголоо
        </button>
      </div>
    </div>,
    document.body,
  );
}
