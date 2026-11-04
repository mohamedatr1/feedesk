import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const maxDuration = 60;

/**
 * Runtime bridge to the private FastAPI service.
 *
 * Vercel injects the internal service URL into API_URL through the service
 * binding in vercel.json. Bindings are only available to functions at request
 * time, so the environment is read per request rather than captured at build
 * time.
 */
function apiOrigin(): string {
  return (
    process.env.API_URL ||
    process.env.API_INTERNAL_URL ||
    "http://127.0.0.1:8000"
  );
}

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
  "host",
  "content-length",
  "accept-encoding",
  "content-encoding",
]);

function upstreamUrl(request: NextRequest, segments: string[]): URL {
  const path = segments.map((segment) => encodeURIComponent(segment)).join("/");
  const url = new URL(`/api/${path}`, apiOrigin());
  url.search = request.nextUrl.search;
  return url;
}

function upstreamHeaders(request: NextRequest): Headers {
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  });
  headers.set("x-forwarded-host", request.nextUrl.host);
  headers.set("x-forwarded-proto", request.nextUrl.protocol.replace(":", ""));
  return headers;
}

function responseHeaders(upstream: Response): Headers {
  const headers = new Headers();
  upstream.headers.forEach((value, key) => {
    const name = key.toLowerCase();
    if (name === "set-cookie" || HOP_BY_HOP_HEADERS.has(name)) return;
    headers.set(key, value);
  });

  // Multiple Set-Cookie headers must survive independently; combining them
  // would corrupt cookie attributes such as Expires and SameSite.
  const getSetCookie = (
    upstream.headers as Headers & { getSetCookie?: () => string[] }
  ).getSetCookie;
  const cookies = getSetCookie ? getSetCookie.call(upstream.headers) : [];
  for (const cookie of cookies) {
    headers.append("set-cookie", cookie);
  }
  return headers;
}

async function proxy(request: NextRequest, segments: string[]): Promise<Response> {
  const init: RequestInit & { duplex?: "half" } = {
    method: request.method,
    headers: upstreamHeaders(request),
    redirect: "manual",
    cache: "no-store",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    const contentType = request.headers.get("content-type") ?? "";
    const contentLength = Number(request.headers.get("content-length") ?? "0");
    const bufferSmallBody =
      contentType.includes("application/json") ||
      contentType.includes("application/x-www-form-urlencoded") ||
      (contentLength > 0 && contentLength <= 1_000_000);

    if (bufferSmallBody) {
      // Buffering small bodies avoids an upstream early response (for example
      // a 401) aborting an in-flight streamed request body.
      const body = await request.arrayBuffer();
      if (body.byteLength > 0) init.body = body;
    } else if (request.body) {
      init.body = request.body;
      init.duplex = "half";
    }
  }

  // A just-created service can briefly fail its first request. GET/HEAD are
  // safe to retry once; mutating requests are never replayed.
  const attempts = request.method === "GET" || request.method === "HEAD" ? 2 : 1;
  try {
    let upstream: Response | undefined;
    for (let attempt = 1; attempt <= attempts; attempt += 1) {
      try {
        const candidate = await fetch(upstreamUrl(request, segments), init);
        if (candidate.status >= 500 && attempt < attempts) {
          await new Promise((resolve) => setTimeout(resolve, 350));
          continue;
        }
        upstream = candidate;
        break;
      } catch (error) {
        if (attempt < attempts) {
          await new Promise((resolve) => setTimeout(resolve, 350));
          continue;
        }
        console.error("API bridge fetch failed", error);
        throw error;
      }
    }
    if (!upstream) {
      throw new Error("API bridge returned no response");
    }
    try {
      return new Response(upstream.body, {
        status: upstream.status,
        statusText: upstream.statusText,
        headers: responseHeaders(upstream),
      });
    } catch (error) {
      console.error("API bridge response failed", error);
      throw error;
    }
  } catch (error) {
    console.error("API bridge request failed", error);
    return Response.json(
      {
        error: {
          code: "API_UNAVAILABLE",
          message_ar: "تعذر الوصول إلى خدمة الخادم. أعد المحاولة.",
          message_en: "The API service is unavailable. Please retry.",
        },
      },
      { status: 502 },
    );
  }
}

type RouteContext = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function POST(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function PUT(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function HEAD(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function OPTIONS(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}
