import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "تغيير كلمة المرور — FeeDesk",
};

export default function ChangePasswordLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
