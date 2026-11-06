import Link from "next/link";
import { PredictButtons } from "@/components/actions";
import {
  apiGet,
  type PredictionItem,
  type PredictionRun,
  type RunSummary,
} from "@/lib/api";

function PaperSheet({ run, subject }: { run: PredictionRun; subject: string }) {
  const questions = run.items.filter((item) => item.basis !== "surprise");
  const surprises = run.items.filter((item) => item.basis === "surprise");
  const totalMarks = questions.reduce((sum, item) => sum + (item.marks ?? 0), 0);

  // group consecutive sub-parts under their question number
  const blocks: PredictionItem[][] = [];
  for (const item of questions) {
    const last = blocks[blocks.length - 1];
    if (last && last[0].question_number === item.question_number) {
      last.push(item);
    } else {
      blocks.push([item]);
    }
  }

  return (
    <div className="sheet-paper">
      <div className="sheet-head">
        <div className="institution">Predicted from {run.mode.replace("-", " ")} analysis</div>
        <div className="title">{subject} — Model Question Paper</div>
        <div className="meta">
          {run.generated ? "Freshly phrased by Gemini" : "Phrasings from past papers"}
          {totalMarks > 0 ? ` · Max marks in blueprint: ${totalMarks}` : ""}
        </div>
      </div>
      <div className="sheet-instructions">
        Margin stamps show each question&rsquo;s historical probability of appearance —
        computed from past-paper recurrence, not AI judgment.
      </div>

      {blocks.map((block) => (
        <div className="q-block" key={`${block[0].question_number}-${block[0].part ?? ""}`}>
          {block.map((item, index) => (
            <div key={`${item.question_number}-${item.part ?? index}`}>
              <div className="q-line">
                {item.probability != null && (
                  <span className="stamp">{Math.round(item.probability * 100)}%</span>
                )}
                <span className="q-no">{index === 0 ? `${item.question_number}.` : ""}</span>
                {item.part && <span className="q-part">({item.part})</span>}
                <span className="q-text">{item.question_text}</span>
                {item.marks != null && <span className="q-marks">[{item.marks}M]</span>}
              </div>
              {item.rationale && (
                <details className="q-why">
                  <summary>why this question</summary>
                  <p>{item.rationale}</p>
                </details>
              )}
            </div>
          ))}
        </div>
      ))}

      {surprises.length > 0 && (
        <div className="surprise-block">
          <div className="surprise-head">Surprise candidates — in syllabus, never asked</div>
          {surprises.map((item, index) => (
            <div key={index}>
              <div className="surprise-item">
                <span className="ast">*</span>
                <span className="q-text">{item.question_text}</span>
              </div>
              {item.rationale && (
                <details className="q-why">
                  <summary>why flagged</summary>
                  <p>{item.rationale}</p>
                </details>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default async function PredictPage({
  params,
  searchParams,
}: {
  params: Promise<{ subject: string }>;
  searchParams: Promise<{ run?: string }>;
}) {
  const subject = decodeURIComponent((await params).subject);
  const encoded = encodeURIComponent(subject);
  const { run: runParam } = await searchParams;

  const runs = await apiGet<RunSummary[]>(`/predictions/${encoded}`);
  if (!runs.ok) {
    return (
      <>
        <h1>{subject}</h1>
        <p className="notice error">{runs.error}</p>
      </>
    );
  }

  const activeId = runParam ? Number(runParam) : runs.data[0]?.id;
  const active = activeId
    ? await apiGet<PredictionRun>(`/predictions/run/${activeId}`)
    : null;

  return (
    <>
      <div className="page-head">
        <div className="grow">
          <p className="eyebrow">
            <Link href={`/subjects/${encoded}`}>{subject}</Link> · prediction
          </p>
          <h1>Predicted paper</h1>
          <p className="page-sub">
            Structure and probabilities come from the pattern engine; Gemini only
            words the questions.
          </p>
        </div>
      </div>

      <div className="layout-cols">
        <div>
          {active?.ok ? (
            <PaperSheet run={active.data} subject={subject} />
          ) : runs.data.length === 0 ? (
            <p className="notice empty">
              No predictions yet for {subject}. Run analysis first, then predict —
              &ldquo;from past phrasings&rdquo; works without an API key.
            </p>
          ) : (
            <p className="notice error">{active && !active.ok ? active.error : "Run not found."}</p>
          )}
        </div>

        <aside>
          <div className="card" style={{ marginBottom: 16 }}>
            <h2>New prediction</h2>
            <PredictButtons subject={subject} />
          </div>

          {runs.data.length > 0 && (
            <div className="card">
              <h2>Past runs</h2>
              <div className="run-list">
                {runs.data.map((summary) => (
                  <Link
                    key={summary.id}
                    className={`run-link${summary.id === activeId ? " active" : ""}`}
                    href={`/subjects/${encoded}/predict?run=${summary.id}`}
                  >
                    <span className="when">
                      {new Date(summary.created_at).toLocaleString()}
                    </span>
                    <span className="tag">
                      {summary.generated ? "gemini" : "offline"} · {summary.mode}
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </aside>
      </div>
    </>
  );
}
