import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "كشوف الأقساط — FeeDesk",
};

export default function StatementsLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
