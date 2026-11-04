"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Search, X } from "lucide-react";
import {
  MESSAGE_FILTER_GROUPS,
  MESSAGE_STATUS_META,
  messagesHref,
} from "@/components/messages/message-format";

export type CampaignOption = { id: string; name: string; date?: string | null };

function optionLabel(campaign: CampaignOption): string {
  return campaign.date ? `${campaign.name} — ${campaign.date}` : campaign.name;
}

export function MessagesFilterBar({
  campaignId,
  status,
  q,
  campaigns,
  selectedCampaignName,
  busy = false,
}: {
  campaignId: string;
  status: string;
  q: string;
  campaigns: CampaignOption[];
  selectedCampaignName: string | null;
  busy?: boolean;
}) {
  const router = useRouter();
  const [term, setTerm] = useState(q);
  const termRef = useRef(term);
  termRef.current = term;

  // Keep the field in step with back/forward navigation.
  useEffect(() => {
    setTerm(q);
  }, [q]);

  useEffect(() => {
    if (term === q) return;
    const timer = window.setTimeout(() => {
      router.replace(messagesHref({ campaign_id: campaignId, status, q: term }));
    }, 400);
    return () => window.clearTimeout(timer);
  }, [term, q, campaignId, status, router]);

  const hasFilters = Boolean(q || campaignId || status);
  const optionsIncludeSelected = campaigns.some((item) => item.id === campaignId);

  return (
    <div className="mb-4">
      <form
        role="search"
        aria-label="تصفية الرسائل"
        className="grid gap-2 lg:grid-cols-[minmax(0,1fr)_220px_200px_auto] lg:items-center"
        onSubmit={(event) => {
          event.preventDefault();
          router.replace(
            messagesHref({ campaign_id: campaignId, status, q: termRef.current }),
          );
        }}
      >
        <div className="relative">
          <label htmlFor="message-q" className="sr-only">
            ابحث باسم ولي الأمر أو رقم الهاتف
          </label>
          <Search
            size={16}
            aria-hidden
            className="pointer-events-none absolute inset-y-0 start-3 my-auto text-[var(--fd-ink-subtle)]"
          />
          <input
            id="message-q"
            type="search"
            className="fd-input h-11 ps-9 pe-10"
            placeholder="ابحث باسم ولي الأمر أو رقم الهاتف"
            autoComplete="off"
            value={term}
            onChange={(event) => setTerm(event.target.value)}
          />
          {busy ? (
            <Loader2
              size={14}
              aria-hidden
              className="pointer-events-none absolute inset-y-0 end-3 my-auto animate-spin text-[var(--fd-ink-subtle)]"
            />
          ) : (
            term && (
              <button
                type="button"
                className="absolute inset-y-0 end-0 flex h-11 w-11 items-center justify-center text-[var(--fd-ink-muted)] hover:text-[var(--fd-ink)]"
                aria-label="مسح البحث"
                onClick={() => {
                  setTerm("");
                  router.replace(
                    messagesHref({ campaign_id: campaignId, status, q: "" }),
                  );
                }}
              >
                <X size={15} aria-hidden />
              </button>
            )
          )}
        </div>

        <div>
          <label htmlFor="message-campaign" className="sr-only">
            الحملة
          </label>
          <select
            id="message-campaign"
            className="fd-input h-11"
            value={campaignId}
            onChange={(event) =>
              router.push(
                messagesHref({
                  campaign_id: event.target.value,
                  status,
                  q: termRef.current,
                }),
              )
            }
          >
            <option value="">الحملة: الكل</option>
            {!optionsIncludeSelected && campaignId && selectedCampaignName && (
              <option value={campaignId}>{selectedCampaignName}</option>
            )}
            {campaigns.map((campaign) => (
              <option key={campaign.id} value={campaign.id}>
                {optionLabel(campaign)}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="message-status" className="sr-only">
            الحالة
          </label>
          <select
            id="message-status"
            className="fd-input h-11"
            value={status}
            onChange={(event) =>
              router.push(
                messagesHref({
                  campaign_id: campaignId,
                  status: event.target.value,
                  q: termRef.current,
                }),
              )
            }
          >
            <option value="">الحالة: الكل</option>
            {MESSAGE_FILTER_GROUPS.map((group) => (
              <optgroup key={group.label} label={group.label}>
                {group.statuses.map((value) => (
                  <option key={value} value={value}>
                    {MESSAGE_STATUS_META[value]?.filterLabel ?? value}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>

        <div className="flex min-h-11 items-center">
          {hasFilters && (
            <a
              href="/messages"
              className="inline-flex min-h-11 items-center px-2 text-[12px] font-medium text-[var(--fd-brand)] hover:underline"
            >
              مسح عوامل التصفية
            </a>
          )}
        </div>
      </form>

      {hasFilters && (
        <p className="mt-2 text-[12px] text-[var(--fd-ink-muted)]">
          تصفية:
          {campaignId && selectedCampaignName && (
            <>
              {" "}
              حملة «<bdi dir="auto">{selectedCampaignName}</bdi>»
            </>
          )}
          {status && (
            <>
              {campaignId && selectedCampaignName ? " · " : " "}
              الحالة: {MESSAGE_STATUS_META[status]?.label ?? "—"}
            </>
          )}
          {q && (
            <>
              {campaignId || status ? " · " : " "}
              البحث: «<bdi dir="auto">{q}</bdi>»
            </>
          )}
        </p>
      )}
    </div>
  );
}
