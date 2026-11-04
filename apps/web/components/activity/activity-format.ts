export type ActivityTone = "neutral" | "amber" | "green" | "red";

/**
 * One vocabulary for activity rows, shared by the dashboard and the audit log.
 * An action missing from this map is rendered as its raw code, never as a
 * guessed Arabic sentence.
 */
const ACTION_LABELS: Record<string, string> = {
  "auth.login": "تسجيل دخول",
  "auth.logout": "تسجيل خروج",
  "auth.login_failed": "محاولة دخول فاشلة",
  "auth.login_blocked": "دخول محظور",
  "auth.password_change": "تغيير كلمة المرور",
  "user.create": "إنشاء مستخدم",
  "user.update": "تعديل مستخدم",
  "user.password_reset": "إعادة تعيين كلمة المرور",
  "settings.update": "تعديل الإعدادات",
  "file.download": "تنزيل ملف",
  "file.upload": "رفع ملف",
  "import.upload": "رفع كشف أقساط",
  "import.process": "معالجة كشف أقساط",
  "import.row_update": "تعديل سجل مستورد",
  "import.confirm": "تأكيد كشف أقساط",
  "import.cancel": "إلغاء كشف أقساط",
  "campaign.create": "إنشاء حملة تذكير",
  "campaign.update": "تعديل حملة تذكير",
  "campaign.preview": "معاينة حملة تذكير",
  "campaign.submit": "إرسال حملة للاعتماد",
  "campaign.approve": "اعتماد حملة تذكير",
  "campaign.cancel": "إلغاء حملة تذكير",
  "template.create": "إنشاء قالب رسالة",
  "template.update": "تعديل قالب رسالة",
  "template.activate": "تفعيل قالب رسالة",
  "message.update": "تحديث حالة رسالة",
  "message.send": "محاولة إرسال رسالة",
  "provider.credential_update": "تحديث بيانات اعتماد المزوّد",
  "provider.credential_revoke": "إلغاء بيانات اعتماد المزوّد",
  "provider.test_send": "إرسال اختباري",
};

export function activityActionLabel(action: string): string | null {
  return ACTION_LABELS[action] ?? null;
}

const ENTITY_LABELS: Record<string, string> = {
  user: "مستخدم",
  auth: "جلسة",
  school_settings: "إعدادات المدرسة",
  source_file: "ملف مصدر",
  import: "كشف أقساط",
  import_batch: "كشف أقساط",
  campaign: "حملة تذكير",
  message: "رسالة",
  message_job: "مهمة إرسال",
  template: "قالب رسالة",
  fee_balance: "سجل قسط",
  guardian: "ولي أمر",
  student: "طالب",
  provider_credential: "بيانات اعتماد المزوّد",
};

export function activityEntityLabel(entityType: string): string {
  if (!entityType) return "—";
  return ENTITY_LABELS[entityType] ?? entityType;
}

const ACTIVITY_STATUS_META: Record<string, { label: string; tone: ActivityTone }> = {
  completed: { label: "مكتملة", tone: "green" },
  complete: { label: "مكتملة", tone: "green" },
  success: { label: "ناجحة", tone: "green" },
  successful: { label: "ناجحة", tone: "green" },
  ok: { label: "ناجحة", tone: "green" },
  succeeded: { label: "ناجحة", tone: "green" },
  done: { label: "مكتملة", tone: "green" },
  sent: { label: "أُرسلت", tone: "green" },
  delivered: { label: "تم التسليم", tone: "green" },
  pending: { label: "معلّقة", tone: "amber" },
  queued: { label: "في الانتظار", tone: "amber" },
  processing: { label: "قيد التنفيذ", tone: "amber" },
  running: { label: "قيد التنفيذ", tone: "amber" },
  unknown: { label: "غير معروفة", tone: "amber" },
  failed: { label: "فاشلة", tone: "red" },
  error: { label: "فاشلة", tone: "red" },
  cancelled: { label: "ملغاة", tone: "neutral" },
  canceled: { label: "ملغاة", tone: "neutral" },
};

export function activityStatusMeta(
  status: string,
): { label: string; tone: ActivityTone } | null {
  const value = (status ?? "").trim();
  if (!value) return null;
  return ACTIVITY_STATUS_META[value] ?? ACTIVITY_STATUS_META[value.toLowerCase()] ?? null;
}

/** Short, stable identifier for tables; full ids stay in the audit log. */
export function shortId(value: string | null | undefined, length = 8): string | null {
  if (!value) return null;
  return value.slice(0, length);
}
