import Link from "next/link";
import { RunAnalysisButton } from "@/components/actions";
import { Meter } from "@/components/meter";
import {
  DeletePaperButton,
  PaperUploadForm,
  SyllabusUploadForm,
} from "@/components/upload-forms";
import {
  apiGet,
  type CoverageRow,
  type FrequencyRow,
  type Paper,
  type Topic,
} from "@/lib/api";

export default async function SubjectPage({
  params,
}: {
  params: Promise<{ subject: string }>;
}) {
  const subject = decodeURIComponent((await params).subject);
  const encoded = encodeURIComponent(subject);

  const [papers, frequency, coverage, syllabus] = await Promise.all([
    apiGet<Paper[]>(`/papers?subject=${encoded}`),
    apiGet<FrequencyRow[]>(`/analysis/${encoded}/frequency`),
    apiGet<CoverageRow[]>(`/analysis/${encoded}/coverage`),
    apiGet<Topic[]>(`/syllabus/${encoded}`),
  ]);

  if (!papers.ok) {
    return (
      <>
        <h1>{subject}</h1>
        <p className="notice error">{papers.error}</p>
      </>
    );
  }

  const sorted = [...papers.data].sort((a, b) => a.year - b.year);
  const analyzed = frequency.ok;

  return (
    <>
      <div className="page-head">
        <div className="grow">
          <p className="eyebrow">Subject</p>
          <h1>{subject}</h1>
          <p className="page-sub">
            {sorted.length} paper{sorted.length === 1 ? "" : "s"} on file
            {syllabus.ok ? " · syllabus loaded (Mode 2)" : " · no syllabus (Mode 1)"}
          </p>
        </div>
        <div className="btn-row">
          <Link className="btn secondary" href={`/subjects/${encoded}/predict`}>
            Predicted paper →
          </Link>
        </div>
      </div>

      {analyzed && (
        <section className="section">
          <div className="stat-grid">
            <div className="stat">
              <div className="label">Papers</div>
              <div className="value">{sorted.length}</div>
              <div className="hint">
                {sorted.length > 0
                  ? `${Math.min(...sorted.map((p) => p.year))}–${Math.max(...sorted.map((p) => p.year))}`
                  : "none yet"}
              </div>
            </div>
            <div className="stat">
              <div className="label">Question groups</div>
              <div className="value">{frequency.data.length}</div>
              <div className="hint">after dedup</div>
            </div>
            <div className="stat">
              <div className="label">Top probability</div>
              <div className="value">
                {Math.round((frequency.data[0]?.p_weighted ?? 0) * 100)}%
              </div>
              <div className="hint">most likely question</div>
            </div>
            <div className="stat">
              <div className="label">Mode</div>
              <div className="value">{syllabus.ok ? "2" : "1"}</div>
              <div className="hint">{syllabus.ok ? "syllabus-constrained" : "pattern only"}</div>
            </div>
          </div>
        </section>
      )}

      <div className="layout-cols">
        <div>
          <section className="section">
            <h2>Most probable questions</h2>
            {analyzed ? (
              <div className="table-card">
              <table className="data">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Question</th>
                    <th>Asked</th>
                    <th>Probability (recency-weighted)</th>
                    <th className="num">Marks</th>
                  </tr>
                </thead>
                <tbody>
                  {frequency.data.map((row, index) => (
                    <tr key={row.canonical_group_id}>
                      <td className="rank">{index + 1}</td>
                      <td>{row.question_text}</td>
                      <td className="years">
                        {row.years_appeared.join(", ")}
                        <br />
                        {row.appearances}× asked
                      </td>
                      <td>
                        <Meter value={row.p_weighted} />
                      </td>
                      <td className="num">{row.marks ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            ) : sorted.length === 0 ? (
              <p className="notice empty">
                No papers yet for {subject}. Upload 3+ years of question papers,
                then run analysis to see what repeats.
              </p>
            ) : (
              <div className="notice">
                <p style={{ margin: "0 0 10px" }}>
                  {sorted.length} paper{sorted.length === 1 ? "" : "s"} uploaded but not
                  analyzed yet. Analysis embeds every question, merges reworded
                  duplicates, and computes how often each one really appears.
                </p>
                <RunAnalysisButton subject={subject} />
              </div>
            )}
          </section>

          {analyzed && (
            <section className="section">
              <h2>Syllabus coverage</h2>
              {coverage.ok ? (
                <div className="card">
                  {coverage.data.map((row) => (
                    <div className="topic-row" key={row.topic}>
                      <span className={`chip ${row.status}`}>
                        <span className="dot" />
                        {row.status}
                      </span>
                      <span className="topic-name">
                        {row.topic}
                        {row.chapter ? (
                          <span className="topic-meta"> · {row.chapter}</span>
                        ) : null}
                      </span>
                      <span className="topic-meta">
                        {row.question_count === 0
                          ? "never asked"
                          : `${row.question_count} q · ${row.years_covered.join(", ")}`}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="notice empty">
                  Upload the official syllabus to see which topics are hot, which are
                  cold, and which are due for a surprise (Mode 2).
                </p>
              )}
            </section>
          )}

          {analyzed && (
            <section className="section">
              <RunAnalysisButton subject={subject} />
            </section>
          )}
        </div>

        <aside>
          <div className="card" style={{ marginBottom: 16 }}>
            <h2>Papers on file</h2>
            {sorted.length === 0 ? (
              <p className="notice empty">None yet.</p>
            ) : (
              <div className="pill-row" style={{ marginBottom: 14 }}>
                {sorted.map((paper) => (
                  <span className="pill" key={paper.id}>
                    {paper.year}
                    {paper.exam_session ? ` ${paper.exam_session}` : ""}
                    <DeletePaperButton paperId={paper.id} />
                  </span>
                ))}
              </div>
            )}
            <PaperUploadForm subject={subject} />
          </div>

          <div className="card">
            <h2>Syllabus</h2>
            {syllabus.ok && (
              <p className="page-sub" style={{ fontSize: 13, marginBottom: 10 }}>
                {syllabus.data.length} topics loaded. Uploading again replaces them.
              </p>
            )}
            <SyllabusUploadForm subject={subject} />
          </div>
        </aside>
      </div>
    </>
  );
}
