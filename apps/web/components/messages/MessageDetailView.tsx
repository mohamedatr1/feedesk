"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ChevronLeft, Lock, MessageSquare, RefreshCw } from "lucide-react";
import {
  ApiError,
  api,
  formatDateTime,
  type MessageDetail,
} from "@/lib/api";
import { useSession } from "@/lib/session";
import { Protected } from "@/components/Protected";
import { EmptyState } from "@/components/EmptyState";
import { HistoryNotice } from "@/components/messages/HistoryNotice";
import { MessageStatusPill } from "@/components/messages/MessageStatusPill";
import { MessageBodyCard } from "@/components/messages/MessageBodyCard";
import { MessageDestinationCard } from "@/components/messages/MessageDestinationCard";
import { MessageStatusCard } from "@/components/messages/MessageStatusCard";
import { ProviderReferences } from "@/components/messages/ProviderReferences";
import { AttemptsCard } from "@/components/messages/AttemptsCard";
import { RedactedPayload } from "@/components/messages/RedactedPayload";
import { formatMessageMoney } from "@/components/messages/message-format";

function absenceCopy(status: string): string | null {
  switch (status) {
    case "failed":
      return "لا يوجد إجراء إعادة إرسال. أصلح سبب الفشل — غالبًا رقم الهاتف أو بيانات المستلم — ثم أنشئ حملة جديدة.";
    case "unknown":
      return "لم نتأكد من نتيجة آخر محاولة. قد تكون الرسالة وصلت، وإعادة إرسالها قد ترسل نسخة ثانية. لذلك لا تُعاد تلقائيًا ولا يدويًا في هذه المرحلة.";
    case "provider_accepted":
    case "queued_by_provider":
      return "قبول المزوّد لا يعني التسليم. لا يصل تحديث تلقائي لحالة التسليم في هذه المرحلة.";
    case "delivered":
      return "هذه الرسالة مؤكدة التسليم. لا يوجد ما يلزم فعله.";
    case "pending":
      return "لم تُرسل إلى المزوّد بعد. لا يوجد إجراء مطلوب منك.";
    case "cancelled":
      return "أُلغيت الرسالة مع إلغاء الحملة. لا يمكن إعادتها.";
    default:
      return null;
  }
}

export function MessageDetailView({ messageId }: { messageId: string }) {
  return (
    <Protected active="/messages">
      <MessageDetailContent messageId={messageId} />
    </Protected>
  );
}

function MessageDetailContent({ messageId }: { messageId: string }) {
  const { settings } = useSession();
  const [message, setMessage] = useState<MessageDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [forbidden, setForbidden] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  const formatted = useCallback(
    (value: string | null) =>
      value
        ? formatDateTime(value, { locale: settings?.locale, timeZone: settings?.timezone })
        : "—",
    [settings?.locale, settings?.timezone],
  );

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    setNotFound(false);
    setForbidden(false);

    api
      .getMessage(messageId)
      .then((data) => {
        if (mounted) setMessage(data);
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        if (err instanceof ApiError && err.status === 404) {
          setNotFound(true);
        } else if (err instanceof ApiError && err.status === 403) {
          setForbidden(true);
        } else if (err instanceof ApiError && err.status === 401) {
          setError("انتهت الجلسة. سجّل الدخول مرة أخرى.");
        } else {
          setError(err instanceof ApiError ? err.messageAr : "تعذر تحميل الرسالة.");
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [messageId, reloadKey]);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  if (notFound) {
    return (
      <div className="fd-card">
        <EmptyState
          icon={MessageSquare}
          title="لم نجد هذه الرسالة"
          description="قد يكون الرابط قديمًا أو أن الرسالة غير متاحة لحسابك."
          action={
            <Link href="/messages" className="fd-btn fd-btn-secondary h-11">
              العودة إلى سجل الرسائل
            </Link>
          }
        />
      </div>
    );
  }

  if (forbidden) {
    return (
      <div className="fd-card">
        <EmptyState
          icon={Lock}
          title="لا تملك صلاحية عرض هذه الرسالة."
          description="تواصل مع مدير النظام إن كنت تحتاج الوصول إلى هذه الرسالة."
          action={
            <Link href="/messages" className="fd-btn fd-btn-secondary h-11">
              العودة إلى سجل الرسائل
            </Link>
          }
        />
      </div>
    );
  }

  if (loading && !message) {
    return (
      <div className="max-w-[1080px] space-y-4" aria-busy="true">
        <div className="fd-skeleton h-7 w-56" />
        <div className="fd-skeleton h-9 w-2/5" />
        <div className="fd-skeleton h-11 w-full" />
        <div className="fd-skeleton h-40 w-full" />
        <div className="grid gap-4 md:grid-cols-2">
          <div className="fd-skeleton h-56" />
          <div className="fd-skeleton h-56" />
        </div>
      </div>
    );
  }

  if (!message) {
    return (
      <div
        role="alert"
        className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-4 py-3 text-[12px] text-[var(--fd-red-text)]"
      >
        <span>تعذر تحميل الرسالة. {error ?? ""}</span>
        <button
          type="button"
          onClick={reload}
          className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
        >
          <RefreshCw size={14} aria-hidden />
          إعادة المحاولة
        </button>
      </div>
    );
  }

  const absence = absenceCopy(message.internal_status);

  return (
    <div className="max-w-[1080px]">
      <nav aria-label="مسار التصفح" className="mb-3">
        <ol className="flex flex-wrap items-center gap-1 text-[12px] text-[var(--fd-ink-muted)]">
          <li>
            <Link href="/messages" className="hover:text-[var(--fd-ink)] hover:underline">
              سجل الرسائل
            </Link>
          </li>
          <li aria-hidden>
            <ChevronLeft size={14} className="rtl:rotate-180" />
          </li>
          <li aria-current="page" className="min-w-0 text-[var(--fd-ink)]">
            تفاصيل الرسالة
          </li>
        </ol>
      </nav>

      <div className="mb-4">
        <div className="flex flex-wrap items-center gap-3">
          <h1
            tabIndex={-1}
            className="text-[30px] font-bold leading-tight text-[var(--fd-ink)] focus:outline-none"
          >
            رسالة إلى <bdi dir="auto">{message.guardian_name || "مستلم"}</bdi>
          </h1>
          <MessageStatusPill status={message.internal_status} />
        </div>
        <p className="mt-1 text-[14px] text-[var(--fd-ink-muted)]">
          الحملة:{" "}
          <Link
            href={`/campaigns/${message.campaign_id}`}
            className="hover:text-[var(--fd-ink)] hover:underline"
          >
            <bdi dir="auto">{message.campaign_name}</bdi>
          </Link>
          {" · "}
          <bdi dir="ltr" className="tabular-nums">
            {formatMessageMoney(message.amount, message.currency)}
          </bdi>
          {" · "}
          <bdi dir="ltr" lang="en">
            {message.channel === "sms" ? "SMS" : message.channel || "—"}
          </bdi>
        </p>
        <p className="mt-1 text-[12px] text-[var(--fd-ink-subtle)]">
          أُنشئت <bdi dir="ltr">{formatted(message.created_at)}</bdi>
          {" · "}آخر تحديث <bdi dir="ltr">{formatted(message.updated_at)}</bdi>
        </p>
      </div>

      <HistoryNotice className="mb-4" />

      {error && (
        <div
          role="alert"
          className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-4 py-3 text-[12px] text-[var(--fd-red-text)]"
        >
          <span>تعذر تحميل الرسالة. {error}</span>
          <button
            type="button"
            onClick={reload}
            className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
          >
            إعادة المحاولة
          </button>
        </div>
      )}

      <div className="space-y-4">
        <MessageBodyCard body={message.message_body_snapshot} />

        <div className="grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
          <MessageDestinationCard message={message} />
          <MessageStatusCard message={message} formatted={formatted} />
        </div>

        <div className="grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
          <ProviderReferences message={message} />
          <AttemptsCard message={message} formatted={formatted} />
        </div>

        <RedactedPayload payload={message.provider_payload_redacted} />
      </div>

      {absence && (
        <p className="mt-4 text-[12.5px] leading-6 text-[var(--fd-ink-muted)]">{absence}</p>
      )}

      <div className="mt-6">
        <Link href="/messages" className="fd-btn fd-btn-secondary h-11">
          العودة إلى سجل الرسائل
        </Link>
      </div>
    </div>
  );
}
