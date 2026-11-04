import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "سجل الرسائل — FeeDesk",
};

export default function MessagesLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
