import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "تسجيل الدخول — FeeDesk",
};

export default function LoginLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
