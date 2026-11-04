import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "إدارة المستخدمين — FeeDesk",
};

export default function UsersSettingsLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
