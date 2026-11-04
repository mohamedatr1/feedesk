import { TemplateVersionDetailView } from "@/components/templates/TemplateVersionDetailView";

export default async function TemplateVersionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return <TemplateVersionDetailView templateId={id} />;
}
