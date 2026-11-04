import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "إصدار القالب — FeeDesk",
};

export default function TemplateVersionLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
