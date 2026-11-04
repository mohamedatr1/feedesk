import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "الرئيسية — FeeDesk",
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
