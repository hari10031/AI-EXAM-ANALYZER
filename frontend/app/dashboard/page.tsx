import Link from "next/link";
import { PaperUploadForm } from "@/components/upload-forms";
import { apiGet, type Paper } from "@/lib/api";

export const metadata = { title: "Dashboard — Exam Paper Predictor" };

export default async function Dashboard() {
  const papers = await apiGet<Paper[]>("/papers");

  if (!papers.ok) {
    return (
      <>
        <h1>Dashboard</h1>
        <p className="notice error">{papers.error}</p>
      </>
    );
  }

  const subjects = new Map<string, Paper[]>();
  for (const paper of papers.data) {
    const list = subjects.get(paper.subject) ?? [];
    list.push(paper);
    subjects.set(paper.subject, list);
  }
  const allYears = papers.data.map((p) => p.year);

  return (
    <>
      <div className="page-head">
        <div className="grow">
          <p className="eyebrow">Dashboard</p>
          <h1>Your subjects</h1>
          <p className="page-sub">
            Each subject is its own question bank. Three or more years of papers
            makes the patterns worth trusting.
          </p>
        </div>
      </div>

      {subjects.size > 0 && (
        <section className="section">
          <div className="stat-grid">
            <div className="stat">
              <div className="label">Subjects</div>
              <div className="value">{subjects.size}</div>
              <div className="hint">question banks</div>
            </div>
            <div className="stat">
              <div className="label">Papers</div>
              <div className="value">{papers.data.length}</div>
              <div className="hint">on file</div>
            </div>
            <div className="stat">
              <div className="label">Coverage</div>
              <div className="value">
                {Math.min(...allYears)}–{Math.max(...allYears)}
              </div>
              <div className="hint">exam years</div>
            </div>
          </div>
        </section>
      )}

      <div className="layout-cols">
        <div>
          {subjects.size === 0 ? (
            <p className="notice empty">
              No papers yet. Upload the first past paper to start a subject.
            </p>
          ) : (
            <div className="subject-grid">
              {[...subjects.entries()].map(([subject, list]) => {
                const years = list.map((p) => p.year);
                return (
                  <Link
                    key={subject}
                    className="subject-card"
                    href={`/subjects/${encodeURIComponent(subject)}`}
                  >
                    <div className="code">{subject}</div>
                    <div className="meta">
                      {list.length} paper{list.length === 1 ? "" : "s"} ·{" "}
                      {Math.min(...years)}–{Math.max(...years)}
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </div>

        <aside>
          <div className="card">
            <h2>Add a past paper</h2>
            <PaperUploadForm />
          </div>
        </aside>
      </div>
    </>
  );
}
