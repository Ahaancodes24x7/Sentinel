import type { z, ZodTypeAny } from "zod";
import { ApiError } from "./errors";
import { getToken } from "./token";
import { resolveMock } from "./mocks";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "true";

interface FetchOpts<S extends ZodTypeAny> {
  schema: S;
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  /** Attach the bearer token. Default true. */
  auth?: boolean;
  query?: Record<string, string | number | boolean | undefined | null>;
  /** Skip Zod validation (rare — e.g. GET /ontology free-form YAML). */
  raw?: boolean;
}

function buildQuery(query?: FetchOpts<ZodTypeAny>["query"]): string {
  if (!query) return "";
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}

/**
 * The one entry point for backend calls. Returns parsed, typed data or throws
 * a typed {@link ApiError}. Never returns a half-validated object.
 */
export async function apiFetch<S extends ZodTypeAny>(
  path: string,
  opts: FetchOpts<S>
): Promise<z.infer<S>> {
  const { schema, method = "GET", body, auth = true, query, raw = false } = opts;
  const qs = buildQuery(query);

  if (USE_MOCKS) {
    const data = await resolveMock(path, { method, query, body });
    return raw ? (data as z.infer<S>) : parse(schema, data, path);
  }

  let res: Response;
  try {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (auth) {
      const token = getToken();
      if (token) headers.Authorization = `Bearer ${token}`;
    }
    res = await fetch(`${BASE_URL}${path}${qs}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
    });
  } catch (e) {
    throw new ApiError({
      code: "NETWORK",
      message:
        "Could not reach the Sentinel backend. Is the API running, or set NEXT_PUBLIC_USE_MOCKS=true for an offline demo.",
      status: 0,
    });
  }

  if (!res.ok) {
    throw await toApiError(res);
  }

  const json = await res.json().catch(() => {
    throw new ApiError({
      code: "SCHEMA_MISMATCH",
      message: `Response body from ${path} was not valid JSON.`,
      status: res.status,
    });
  });

  return raw ? (json as z.infer<S>) : parse(schema, json, path);
}

function parse<S extends ZodTypeAny>(
  schema: S,
  data: unknown,
  path: string
): z.infer<S> {
  const result = schema.safeParse(data);
  if (!result.success) {
    throw new ApiError({
      code: "SCHEMA_MISMATCH",
      message: `Response from ${path} did not match the expected contract.`,
      status: 200,
      issues: result.error.issues,
    });
  }
  return result.data;
}

async function toApiError(res: Response): Promise<ApiError> {
  let code = "HTTP_ERROR";
  let message = `Request failed (${res.status}).`;
  try {
    const body = await res.json();
    if (body?.error) {
      code = body.error.code ?? code;
      message = body.error.message ?? message;
    } else if (typeof body?.detail === "string") {
      message = body.detail;
    }
  } catch {
    /* non-JSON error body */
  }
  if (res.status === 401) code = "UNAUTHORIZED";
  if (res.status === 403) code = "FORBIDDEN";
  if (res.status === 404 && code === "HTTP_ERROR") code = "NOT_FOUND";
  if (res.status >= 500 && code === "HTTP_ERROR") code = "SERVER_ERROR";
  return new ApiError({ code, message, status: res.status });
}
