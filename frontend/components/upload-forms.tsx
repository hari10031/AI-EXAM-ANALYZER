"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { API } from "@/lib/api";

async function postForm(path: string, form: FormData): Promise<string | null> {
  try {
    const res = await fetch(`${API}${path}`, { method: "POST", body: form });
    if (res.ok) return null;
    const body = await res.json().catch(() => null);
    return body?.detail ?? `${res.status} ${res.statusText}`;
  } catch {
    return `Backend not reachable at ${API}.`;
  }
}

export function PaperUploadForm({ subject }: { subject?: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formEl = event.currentTarget;
    setBusy(true);
    setError(null);
    const err = await postForm("/papers", new FormData(formEl));
    setBusy(false);
    if (err) {
      setError(err);
    } else {
      formEl.reset();
      router.refresh();
    }
  }

  return (
    <form className="form-grid" onSubmit={onSubmit}>
      {subject ? (
        <input type="hidden" name="subject" value={subject} />
      ) : (
        <label className="field">
          Subject code
          <input type="text" name="subject" placeholder="CS301" required />
        </label>
      )}
      <label className="field">
        Year
        <input type="number" name="year" min={1990} max={2100} placeholder="2025" required />
      </label>
      <label className="field">
        Session (optional)
        <input type="text" name="exam_session" placeholder="May" />
      </label>
      <label className="field">
        Question paper (PDF or image)
        <input type="file" name="file" accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp,.webp" required />
      </label>
      <div>
        <button className="btn" disabled={busy}>
          {busy ? "Reading paper…" : "Upload paper"}
        </button>
      </div>
      {error && <p className="notice error">{error}</p>}
    </form>
  );
}

export function SyllabusUploadForm({ subject }: { subject: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formEl = event.currentTarget;
    setBusy(true);
    setError(null);
    const err = await postForm("/syllabus", new FormData(formEl));
    setBusy(false);
    if (err) {
      setError(err);
    } else {
      formEl.reset();
      router.refresh();
    }
  }

  return (
    <form className="form-grid" onSubmit={onSubmit}>
      <input type="hidden" name="subject" value={subject} />
      <label className="field">
        Official syllabus (PDF or image)
        <input type="file" name="file" accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp,.webp" required />
      </label>
      <div>
        <button className="btn secondary" disabled={busy}>
          {busy ? "Reading syllabus…" : "Upload syllabus"}
        </button>
      </div>
      {error && <p className="notice error">{error}</p>}
    </form>
  );
}

export function DeletePaperButton({ paperId }: { paperId: number }) {
  const router = useRouter();
  return (
    <button
      type="button"
      aria-label="Remove paper"
      title="Remove paper"
      onClick={async () => {
        if (!confirm("Remove this paper and its questions?")) return;
        await fetch(`${API}/papers/${paperId}`, { method: "DELETE" });
        router.refresh();
      }}
    >
      ✕
    </button>
  );
}
