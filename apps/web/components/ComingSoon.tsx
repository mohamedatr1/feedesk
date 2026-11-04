import type { LucideIcon } from "lucide-react";
import { Protected } from "@/components/Protected";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";

export function ComingSoon({
  active,
  title,
  subtitle,
  description,
  icon,
  requireAdmin = false,
}: {
  active: string;
  title: string;
  subtitle: string;
  description: string;
  icon: LucideIcon;
  requireAdmin?: boolean;
}) {
  return (
    <Protected active={active} requireAdmin={requireAdmin}>
      <PageHeader title={title} subtitle={subtitle} />
      <div className="fd-card">
        <EmptyState icon={icon} title="قيد التنفيذ" description={description} />
      </div>
    </Protected>
  );
}
