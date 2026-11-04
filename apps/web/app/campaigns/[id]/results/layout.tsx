import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "نتائج الرسائل — FeeDesk",
};

export default function CampaignResultsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
