from __future__ import annotations

# Exclusion and warning copy shared by the API, audit metadata, and UI.
MESSAGES_AR: dict[str, str] = {
    "ZERO_BALANCE": "لا يوجد رصيد متبقٍ مستحق.",
    "NEGATIVE_BALANCE": "الرصيد المتبقي سالب ولا يمكن تذكير ولي الأمر به.",
    "MISSING_CURRENCY": "عملة الرصيد غير محددة.",
    "MISSING_PHONE": "لا يوجد رقم هاتف صالح.",
    "INVALID_PHONE": "رقم الهاتف غير صالح.",
    "GUARDIAN_INACTIVE": "حساب ولي الأمر غير نشط.",
    "SHARED_PHONE": "رقم هاتف مشترك بين أكثر من ولي أمر.",
    "UNRESOLVED_VARIABLES": "قالب الرسالة يحتوي متغيرات غير معروفة أو قيمًا مطلوبة غير متاحة.",
    "TEMPLATE_INACTIVE": "قالب الرسالة غير مفعّل.",
    "TEMPLATE_NOT_FOUND": "قالب الرسالة غير موجود.",
    "NO_ELIGIBLE_RECIPIENTS": "لا يوجد مستلمون مؤهلون في هذا الاستيراد.",
    "IMPORT_NOT_CONFIRMED": "يجب اختيار استيراد مؤكد.",
    "NO_ACTIVE_TEMPLATE": "لا يوجد قالب رسائل نشط باللغة العربية.",
    "CAMPAIGN_NOT_FOUND": "الحملة غير موجودة.",
    "TEMPLATE_NOT_FOUND_404": "قالب الرسالة غير موجود.",
    "TEMPLATE_NAME_EXISTS": "اسم القالب مستخدم بالفعل بإصدار أحدث.",
    "CAMPAIGN_STATE_INVALID": "لا يمكن تنفيذ هذا الإجراء في حالة الحملة الحالية.",
    "CAMPAIGN_BLOCKED": "لا يمكن متابعة الحملة لوجود أسباب مانعة.",
    "WARNINGS_UNACKNOWLEDGED": "يجب تأكيد التحذيرات قبل الاعتماد.",
    "CAMPAIGN_CHANGED": "تم تعديل الحملة من جلسة أخرى. أعد تحميل البيانات.",
    "NO_ELIGIBLE_RECIPIENTS_SHORT": "لا يوجد مستلمون مؤهلون.",
}

# Allowed template variables, their Arabic labels, and documented fallbacks.
ALLOWED_VARIABLES: tuple[dict[str, str | None], ...] = (
    {"name": "guardian_name", "label": "اسم ولي الأمر", "fallback": None},
    {"name": "school_name", "label": "اسم المدرسة", "fallback": "المدرسة"},
    {"name": "student_name", "label": "اسم الطالب", "fallback": "الطالب"},
    {"name": "student_list", "label": "أسماء الطلاب", "fallback": "أبنائكم"},
    {"name": "amount", "label": "المبلغ المتبقي", "fallback": None},
    {"name": "currency", "label": "العملة", "fallback": None},
    {"name": "fee_period", "label": "الفصل الدراسي", "fallback": "الفصل الحالي"},
    {"name": "school_contact", "label": "بيانات التواصل مع المدرسة", "fallback": "إدارة المدرسة"},
)

ALLOWED_VARIABLE_NAMES = frozenset(str(item["name"]) for item in ALLOWED_VARIABLES)

DEFAULT_TEMPLATE_NAME = "تذكير الرسوم الدراسية"
# Student names are deliberately omitted from the default body.  Schools that
# want them must explicitly create and activate a template containing
# ``{{student_list}}``; existing active templates are never rewritten by seed.
DEFAULT_TEMPLATE_BODY = (
    "عزيزنا {{guardian_name}}، تذكير من {{school_name}} بشأن مبلغ "
    "{{amount}} {{currency}} المتبقي عن {{fee_period}}. "
    "يرجى التواصل مع {{school_contact}} إذا سبق لكم الدفع أو لديكم استفسار."
)

APPROVED_IMMUTABLE_STATUSES = frozenset(
    {"approved", "queued", "sending", "completed", "completed_with_errors"}
)
