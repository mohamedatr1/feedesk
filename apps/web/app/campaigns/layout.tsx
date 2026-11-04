import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "الحملات — FeeDesk",
};

export default function CampaignsLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
