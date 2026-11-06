export const API =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export interface Paper {
  id: number;
  subject: string;
  year: number;
  exam_session: string | null;
  examiner: string | null;
  source_file: string;
  uploaded_at: string;
}

export interface FrequencyRow {
  canonical_group_id: number;
  question_text: string;
  appearances: number;
  years_appeared: number[];
  p_base: number;
  p_weighted: number;
  marks: number | null;
}

export interface CoverageRow {
  topic: string;
  chapter: string | null;
  syllabus_weight: number | null;
  status: "hot" | "warm" | "cold";
  score: number;
  question_count: number;
  years_covered: number[];
}

export interface Topic {
  id: number;
  name: string;
  chapter: string | null;
  syllabus_weight: number | null;
}

export interface PredictionItem {
  question_number: number | null;
  part: string | null;
  marks: number | null;
  question_text: string;
  probability: number | null;
  basis: string;
  rationale: string | null;
  canonical_group_id: number | null;
  topic: string | null;
}

export interface PredictionRun {
  id: number;
  subject: string;
  mode: string;
  generated: boolean;
  created_at: string;
  items: PredictionItem[];
}

export interface RunSummary {
  id: number;
  subject: string;
  mode: string;
  generated: boolean;
  created_at: string;
}

export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; status: number | null; error: string };

/** Server-side fetch that never throws: connection failures and API errors both
 *  come back as a value the page can render. */
export async function apiGet<T>(path: string): Promise<ApiResult<T>> {
  try {
    const res = await fetch(`${API}${path}`, { cache: "no-store" });
    if (!res.ok) {
      let detail = `${res.status} ${res.statusText}`;
      try {
        const body = await res.json();
        if (body?.detail) detail = String(body.detail);
      } catch {
        /* non-JSON error body */
      }
      return { ok: false, status: res.status, error: detail };
    }
    return { ok: true, data: (await res.json()) as T };
  } catch {
    return {
      ok: false,
      status: null,
      error: `Backend not reachable at ${API}. Start it with: uvicorn app.main:app (in backend/).`,
    };
  }
}
