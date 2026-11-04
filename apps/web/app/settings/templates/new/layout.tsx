import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "محرر القالب — FeeDesk",
};

export default function TemplateEditorLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
