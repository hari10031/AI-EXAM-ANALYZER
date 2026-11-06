"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { API } from "@/lib/api";

export function RunAnalysisButton({ subject }: { subject: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <div>
      <button
        className="btn"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          setError(null);
          try {
            const res = await fetch(`${API}/analysis/${encodeURIComponent(subject)}/run`, {
              method: "POST",
            });
            if (res.ok) {
              router.refresh();
            } else {
              const body = await res.json().catch(() => null);
              setError(body?.detail ?? `${res.status} ${res.statusText}`);
            }
          } catch {
            setError(`Backend not reachable at ${API}.`);
          }
          setBusy(false);
        }}
      >
        {busy ? "Analyzing…" : "Run analysis"}
      </button>
      {error && <p className="notice error" style={{ marginTop: 10 }}>{error}</p>}
    </div>
  );
}

export function PredictButtons({ subject }: { subject: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(generate: boolean) {
    setBusy(generate ? "gen" : "offline");
    setError(null);
    try {
      const res = await fetch(
        `${API}/predict/${encodeURIComponent(subject)}?generate=${generate}`,
        { method: "POST" },
      );
      if (res.ok) {
        const body = await res.json();
        router.push(
          `/subjects/${encodeURIComponent(subject)}/predict?run=${body.run.id}`,
        );
        router.refresh();
      } else {
        const body = await res.json().catch(() => null);
        setError(body?.detail ?? `${res.status} ${res.statusText}`);
      }
    } catch {
      setError(`Backend not reachable at ${API}.`);
    }
    setBusy(null);
  }

  return (
    <div>
      <div className="btn-row">
        <button className="btn" disabled={busy !== null} onClick={() => run(true)}>
          {busy === "gen" ? "Writing paper…" : "Predict with fresh phrasing"}
        </button>
        <button className="btn secondary" disabled={busy !== null} onClick={() => run(false)}>
          {busy === "offline" ? "Assembling…" : "Predict from past phrasings"}
        </button>
      </div>
      {error && <p className="notice error" style={{ marginTop: 10 }}>{error}</p>}
    </div>
  );
}
