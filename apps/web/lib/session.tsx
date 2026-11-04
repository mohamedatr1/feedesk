"use client";

import { createContext, useContext } from "react";
import { api, type Me, type SchoolSettings, type User } from "@/lib/api";

/**
 * Module-level session cache.
 *
 * `Protected` is mounted by every page, so a plain `api.me()` call there would
 * re-fetch `/auth/me` (and `/settings`) and re-mount the whole shell on every
 * client-side navigation. Caching the session and the school settings keeps
 * the shell stable and lets the page body own its own loading state.
 *
 * The cache is cleared on logout and after a password change, and primed on
 * login and after a settings save.
 */
let meCache: Me | null = null;
let settingsCache: SchoolSettings | null = null;
let mePromise: Promise<Me> | null = null;
let settingsPromise: Promise<SchoolSettings> | null = null;

export function getCachedMe(): Me | null {
  return meCache;
}

export function getCachedSettings(): SchoolSettings | null {
  return settingsCache;
}

export function primeSession(me: Me): void {
  meCache = me;
  mePromise = Promise.resolve(me);
}

export function primeSettings(settings: SchoolSettings): void {
  settingsCache = settings;
  settingsPromise = Promise.resolve(settings);
}

export function clearSession(): void {
  meCache = null;
  settingsCache = null;
  mePromise = null;
  settingsPromise = null;
}

export function ensureMe(): Promise<Me> {
  if (meCache) return Promise.resolve(meCache);
  if (!mePromise) {
    mePromise = api
      .me()
      .then((me) => {
        meCache = me;
        return me;
      })
      .catch((error: unknown) => {
        mePromise = null;
        throw error;
      });
  }
  return mePromise;
}

export function ensureSettings(): Promise<SchoolSettings> {
  if (settingsCache) return Promise.resolve(settingsCache);
  if (!settingsPromise) {
    settingsPromise = api
      .getSettings()
      .then((settings) => {
        settingsCache = settings;
        return settings;
      })
      .catch((error: unknown) => {
        settingsPromise = null;
        throw error;
      });
  }
  return settingsPromise;
}

export type SessionValue = {
  user: User;
  settings: SchoolSettings | null;
};

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({
  user,
  settings,
  children,
}: SessionValue & { children: React.ReactNode }) {
  return (
    <SessionContext.Provider value={{ user, settings }}>{children}</SessionContext.Provider>
  );
}

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) {
    throw new Error("useSession must be used inside <Protected>.");
  }
  return value;
}
