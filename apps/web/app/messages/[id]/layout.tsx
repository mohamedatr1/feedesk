import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "تفاصيل الرسالة — FeeDesk",
};

export default function MessageDetailLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
