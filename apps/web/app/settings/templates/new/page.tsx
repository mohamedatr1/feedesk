import { TemplateEditorView } from "@/components/templates/TemplateEditorView";

export default async function NewTemplatePage({
  searchParams,
}: {
  searchParams: Promise<{ from?: string | string[] }>;
}) {
  const params = await searchParams;
  const fromId = typeof params.from === "string" && params.from ? params.from : null;

  return <TemplateEditorView fromId={fromId} />;
}
