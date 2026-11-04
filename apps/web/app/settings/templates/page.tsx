import { TemplatesListView } from "@/components/templates/TemplatesListView";

export default async function TemplatesPage({
  searchParams,
}: {
  searchParams: Promise<{ saved?: string | string[] }>;
}) {
  const params = await searchParams;
  const raw = typeof params.saved === "string" ? Number.parseInt(params.saved, 10) : NaN;
  const savedVersion = Number.isFinite(raw) && raw > 0 ? raw : null;

  return <TemplatesListView savedVersion={savedVersion} />;
}
