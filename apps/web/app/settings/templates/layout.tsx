import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "قوالب الرسائل — FeeDesk",
};

export default function TemplatesLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
