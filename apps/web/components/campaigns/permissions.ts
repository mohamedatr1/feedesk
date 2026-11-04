"use client";

import { useEffect, useState } from "react";
import { ensureMe, getCachedMe } from "@/lib/session";

/**
 * The M3 contract grants staff every campaign permission except approve, plus
 * `templates.view`. `campaigns.approve` is deliberately absent from the staff
 * fallback: only `/auth/me` can grant it, and only for a staff user with the
 * per-user approval flag (FND-08). These fallbacks cover the brief moment
 * before `/auth/me` resolves; the API remains authoritative.
 */
const STAFF_FALLBACK = new Set([
  "campaigns.view",
  "campaigns.create",
  "campaigns.edit",
  "campaigns.preview",
  "campaigns.submit",
  "messages.view",
  "templates.view",
  "imports.view",
]);

const ADMIN_FALLBACK = new Set([
  ...STAFF_FALLBACK,
  "campaigns.approve",
  "templates.manage",
]);

export function hasPermission(
  permissions: string[] | null,
  role: string,
  code: string,
): boolean {
  if (permissions) return permissions.includes(code) || permissions.includes("*");
  if (role === "admin") return ADMIN_FALLBACK.has(code);
  return STAFF_FALLBACK.has(code);
}

/** Reads the cached session from /auth/me; no extra request after boot. */
export function usePermissions(): string[] | null {
  // Seed from the resolved session so a staff approver does not flash the
  // conservative fallback on the first frame. The value still comes from
  // /auth/me; the fallback only applies when no session is cached yet.
  const [permissions, setPermissions] = useState<string[] | null>(
    () => getCachedMe()?.permissions ?? null,
  );

  useEffect(() => {
    let mounted = true;
    ensureMe()
      .then((me) => {
        if (mounted) setPermissions(me.permissions);
      })
      .catch(() => {
        if (mounted) setPermissions([]);
      });
    return () => {
      mounted = false;
    };
  }, []);

  return permissions;
}
