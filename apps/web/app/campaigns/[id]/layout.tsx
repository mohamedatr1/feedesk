import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "تفاصيل الحملة — FeeDesk",
};

export default function CampaignDetailLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
