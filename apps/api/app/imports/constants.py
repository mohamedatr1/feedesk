from __future__ import annotations

CANONICAL_FIELDS: tuple[str, ...] = (
    "guardian_name",
    "guardian_phone",
    "student_name",
    "total_fee",
    "amount_paid",
    "remaining_balance",
    "currency",
    "fee_period",
)

REQUIRED_FIELDS: tuple[str, ...] = ("guardian_name", "remaining_balance", "currency")

# Arabic and English header variants.  Keys are canonical fields; values are raw
# header texts that are normalized before comparison.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "guardian_name": (
        "اسم ولي الأمر",
        "اسم ولي الامر",
        "اسم الولي",
        "ولي الأمر",
        "ولي الامر",
        "الولي",
        "الأب",
        "الاب",
        "الأم",
        "الام",
        "الاسم",
        "اسم الأب",
        "Guardian Name",
        "Guardian",
    ),
    "guardian_phone": (
        "رقم الهاتف",
        "الهاتف",
        "رقم الموبايل",
        "الموبايل",
        "رقم الجوال",
        "الجوال",
        "هاتف",
        "موبايل",
        "جوال",
        "Phone Number",
        "Phone",
        "Mobile",
        "Telephone",
    ),
    "student_name": (
        "اسم الطالب",
        "اسم الطالبة",
        "الطالب",
        "الطالبة",
        "الطلاب",
        "Student Name",
        "Student",
    ),
    "total_fee": (
        "إجمالي القسط",
        "اجمالي القسط",
        "إجمالي الرسوم",
        "اجمالي الرسوم",
        "الرسوم الإجمالية",
        "الإجمالي",
        "الاجمالي",
        "قيمة القسط",
        "المطلوب",
        "Total Fee",
        "Total",
    ),
    "amount_paid": (
        "المدفوع",
        "الواصل",
        "المسدد",
        "المبلغ المدفوع",
        "Amount Paid",
        "Paid",
    ),
    "remaining_balance": (
        "المتبقي",
        "الرصيد",
        "المستحق",
        "الباقي",
        "المتبقي من القسط",
        "Remaining Balance",
        "Remaining",
        "Balance",
    ),
    "currency": (
        "العملة",
        "العملة المستخدمة",
        "Currency",
    ),
    "fee_period": (
        "الفصل",
        "الفصل الدراسي",
        "الشهر",
        "الفترة",
        "Term",
        "Period",
    ),
}

MESSAGES_AR: dict[str, str] = {
    "MISSING_GUARDIAN": "اسم ولي الأمر مفقود.",
    "MISSING_BALANCE": "الرصيد المتبقي مفقود.",
    "NEGATIVE_BALANCE": "الرصيد المتبقي سالب.",
    "MISSING_CURRENCY": "العملة مفقودة أو غير صالحة.",
    "AMBIGUOUS_MONEY": "القيمة المالية غير واضحة أو غير صالحة.",
    "DUPLICATE_ROW": "صف مكرر داخل الملف.",
    "MISSING_PHONE": "رقم الهاتف مفقود.",
    "INVALID_PHONE": "رقم الهاتف غير صالح.",
    "SHARED_PHONE": "رقم الهاتف مشترك مع ولي أمر آخر.",
    "TOTAL_DISCREPANCY": "الرصيد المتبقي لا يطابق الإجمالي ناقص المدفوع.",
    "ZERO_BALANCE": "الرصيد المتبقي صفر.",
    "SCANNED_PDF": "الملف يبدو ممسوحًا ضوئيًا.",
    "OCR_USED": "تم استخدام OCR لقراءة صفحة ممسوحة؛ راجع الصفوف والأعمدة يدويًا قبل التأكيد.",
    "OCR_PAGE_LIMIT": "تم بلوغ الحد الأقصى لعدد الصفحات التي تتم قراءتها باستخدام OCR.",
    "FORMULA_WITHOUT_CACHED_VALUE": "توجد معادلة بدون قيمة محفوظة.",
    "LOW_CONFIDENCE_EXTRACTION": "تم استخراج الصفوف من نص PDF وقد تكون غير دقيقة.",
    "ROW_LIMIT_REACHED": "تم بلوغ الحد الأقصى لعدد الصفوف ولم تتم معالجة بقية الملف.",
    "SHEET_EMPTY": "ورقة العمل لا تحتوي على صفوف بيانات.",
    "SHEET_NOT_FOUND": "ورقة العمل المطلوبة غير موجودة.",
    "SHEET_AUTO_SELECTED": "تم اختيار ورقة العمل تلقائيًا لأن الملف يحتوي على عدة أوراق.",
    "HEADER_NOT_FOUND": "تعذر العثور على صف ترويسة واضح؛ تم استخدام استنتاج الأعمدة من القيم.",
    "CURRENCY_FROM_SCHOOL_SETTINGS": "لم يتم العثور على العملة في الملف؛ تم استخدام عملة إعدادات المدرسة.",
    "PAGE_LIMIT_REACHED": "تم بلوغ الحد الأقصى لعدد صفحات الملف.",
    "NO_EXTRACTABLE_TEXT": "تعذر استخراج نص من الملف.",
    "INVALID_FILE_TYPE": "نوع الملف غير مدعوم. المسموح: xlsx أو pdf.",
    "FILE_TOO_LARGE": "حجم الملف أكبر من الحد المسموح.",
    "FILE_TYPE_MISMATCH": "محتوى الملف لا يطابق امتداده.",
    "XLSX_ARCHIVE_LIMIT": "أرشيف XLSX يتجاوز حدود الحجم الآمن.",
    "DUPLICATE_FILE": "تم تحميل هذا الملف سابقًا.",
    "DUPLICATE_REASON_REQUIRED": "يجب إدخال سبب لتجاوز تكرار الملف.",
    "INVALID_MAPPING": "تعيين الأعمدة غير صالح.",
    "INVALID_WORKSHEET": "ورقة العمل المطلوبة غير موجودة.",
    "WORKSHEET_REQUIRED": "يجب اختيار ورقة عمل.",
    "BLOCKING_ROWS": "توجد صفوف بأخطاء تمنع التأكيد.",
    "WARNINGS_UNACKNOWLEDGED": "يجب الإقرار بالتحذيرات قبل التأكيد.",
    "NO_CONFIRMABLE_ROWS": "لا توجد صفوف صالحة قابلة للتأكيد.",
    "IMPORT_STATE_INVALID": "حالة الاستيراد لا تسمح بهذا الإجراء.",
    "IMPORT_NOT_FOUND": "عملية الاستيراد غير موجودة.",
}

WARNING_FIELDS: dict[str, str] = {
    "MISSING_PHONE": "guardian_phone",
    "INVALID_PHONE": "guardian_phone",
    "SHARED_PHONE": "guardian_phone",
    "TOTAL_DISCREPANCY": "remaining_balance",
    "ZERO_BALANCE": "remaining_balance",
    "FORMULA_WITHOUT_CACHED_VALUE": "source",
    "LOW_CONFIDENCE_EXTRACTION": "source",
}

ERROR_FIELDS: dict[str, str] = {
    "MISSING_GUARDIAN": "guardian_name",
    "MISSING_BALANCE": "remaining_balance",
    "NEGATIVE_BALANCE": "remaining_balance",
    "MISSING_CURRENCY": "currency",
    "AMBIGUOUS_MONEY": "money",
    "DUPLICATE_ROW": "row",
}

BLOCKING_CODES: frozenset[str] = frozenset(ERROR_FIELDS)

EDITABLE_NORMALIZED_FIELDS: frozenset[str] = frozenset(
    {
        "guardian_name",
        "guardian_phone_original",
        "student_name",
        "total_fee",
        "amount_paid",
        "remaining_balance",
        "currency",
        "fee_period",
    }
)
