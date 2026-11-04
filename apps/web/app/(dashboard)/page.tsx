import { Protected } from "@/components/Protected";
import { DashboardView } from "@/components/dashboard/DashboardView";

export default function DashboardPage() {
  return (
    <Protected active="/">
      <DashboardView />
    </Protected>
  );
}
