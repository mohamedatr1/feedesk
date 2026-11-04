import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "حملة جديدة — FeeDesk",
};

export default function NewCampaignLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
