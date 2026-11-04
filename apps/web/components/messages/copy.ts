"use client";

import { useCallback, useEffect, useState } from "react";

/** Copy text with a legacy fallback; never throws, never uses alert(). */
export async function copyTextToClipboard(text: string): Promise<boolean> {
  try {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // Fall through to the selection-based fallback.
  }

  try {
    if (typeof document === "undefined") return false;
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(area);
    return ok;
  } catch {
    return false;
  }
}

/**
 * Copy feedback for a card. `status` mounts empty and only fills on an event,
 * so nothing is announced on first render.
 */
export function useCopyFeedback(resetMs = 4000) {
  const [status, setStatus] = useState<string>("");

  useEffect(() => {
    if (!status) return;
    const timer = window.setTimeout(() => setStatus(""), resetMs);
    return () => window.clearTimeout(timer);
  }, [status, resetMs]);

  const copy = useCallback(async (value: string, success: string) => {
    const ok = await copyTextToClipboard(value);
    setStatus(ok ? success : "تعذر النسخ. حدّد النص وانسخه يدويًا.");
    return ok;
  }, []);

  return { status, copy };
}
