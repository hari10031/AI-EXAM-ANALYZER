import Link from "next/link";
import { apiGet, type FrequencyRow, type Paper } from "@/lib/api";

const SAMPLE_LINES = [
  { p: 100, marks: 7, text: "Explain the functions of each phase of the compiler." },
  { p: 72, marks: 7, text: "Explain the construction of the LR parsing table." },
  { p: 61, marks: 2, text: "Define bottom-up parsing with an example." },
];

const FEATURES = [
  {
    tag: "Probabilities",
    title: "Numbers you can defend",
    text: "Every probability is frequency math over real past papers — appeared 4 of 5 years means 80%. The AI never invents a percentage.",
  },
  {
    tag: "Deduplication",
    title: "Reworded ≠ new",
    text: "Examiners rephrase the same question for years. Semantic matching merges the rewordings so the counts stay honest.",
  },
  {
    tag: "Structure",
    title: "Your exam's exact format",
    text: "The blueprint engine learns which slots repeat — 1(a) shorts, 3(b) numericals — and detects concepts that rotate year over year.",
  },
  {
    tag: "Surprises",
    title: "Cold-topic warnings",
    text: "Upload the syllabus and heavily-weighted topics that were never asked get flagged before they ambush you.",
  },
  {
    tag: "Study guide",
    title: "Ranked, not random",
    text: "A frequency-ranked list of what to study first, with the years each question appeared and its typical marks.",
  },
  {
    tag: "Offline mode",
    title: "Predict without quota",
    text: "The paper can be assembled from historical phrasings alone — no AI call, no API key, same probabilities.",
  },
];

function HeroSheet({ lines, subject }: { lines: typeof SAMPLE_LINES; subject: string | null }) {
  return (
    <div className="hero-visual" aria-hidden="true">
      <div className="hero-sheet-back" />
      <div className="hero-sheet">
        <div className="hs-head">{subject ?? "CS301"} — Model Question Paper</div>
        {lines.map((line, index) => (
          <div className="hs-line" key={index}>
            <span className="hs-stamp">{line.p}%</span>
            <span className="t">
              {index + 1}. {line.text}
            </span>
            <span className="m">[{line.marks}M]</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default async function Landing() {
  // the hero sheet demos the product with the user's own data when it exists
  let heroLines = SAMPLE_LINES;
  let heroSubject: string | null = null;
  const papers = await apiGet<Paper[]>("/papers");
  if (papers.ok && papers.data.length > 0) {
    heroSubject = papers.data[0].subject;
    const frequency = await apiGet<FrequencyRow[]>(
      `/analysis/${encodeURIComponent(heroSubject)}/frequency`,
    );
    if (frequency.ok && frequency.data.length > 0) {
      heroLines = frequency.data.slice(0, 3).map((row) => ({
        p: Math.round(row.p_weighted * 100),
        marks: row.marks ?? 7,
        text:
          row.question_text.length > 64
            ? `${row.question_text.slice(0, 61)}…`
            : row.question_text,
      }));
    }
  }

  return (
    <>
      <section className="hero">
        <div>
          <p className="eyebrow">Pattern analysis for university exams</p>
          <h1 className="hero-title">
            Your next exam paper, <span className="grad-text">predicted</span>.
          </h1>
          <p className="hero-sub">
            Upload past papers and get back a mock paper with an honest
            probability on every question. Frequency math decides the numbers —
            AI only writes the words.
          </p>
          <div className="btn-row">
            <Link className="btn" href="/dashboard">
              Open dashboard
            </Link>
            <a className="btn secondary" href="#how">
              See how it works
            </a>
          </div>
        </div>
        <HeroSheet lines={heroLines} subject={heroSubject} />
      </section>

      <section className="section" id="features">
        <p className="eyebrow">Why it works</p>
        <h2>Built on recurrence, not vibes</h2>
        <div className="feature-grid">
          {FEATURES.map((feature) => (
            <div className="feature" key={feature.tag}>
              <div className="tag">{feature.tag}</div>
              <h3>{feature.title}</h3>
              <p>{feature.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="section" id="how">
        <p className="eyebrow">Workflow</p>
        <h2>Three steps to a predicted paper</h2>
        <div className="steps">
          <div className="step">
            <div className="no">01</div>
            <h3>Upload past papers</h3>
            <p>
              PDFs or photos. Text is extracted and every question — including
              2(a), 2(b) sub-parts — is parsed into a structured bank.
            </p>
          </div>
          <div className="step">
            <div className="no">02</div>
            <h3>Analyze the pattern</h3>
            <p>
              Reworded repeats are merged by meaning, then each question&rsquo;s
              recurrence over the years becomes its probability.
            </p>
          </div>
          <div className="step">
            <div className="no">03</div>
            <h3>Get the predicted paper</h3>
            <p>
              A mock paper in your exam&rsquo;s exact format, a stamp on every
              question, and surprise flags for untested syllabus topics.
            </p>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="cta-band">
          <h2>
            Stop guessing what to study <span className="grad-text">tonight</span>.
          </h2>
          <p>Three or more years of past papers is all it takes.</p>
          <Link className="btn" href="/dashboard">
            Open dashboard
          </Link>
        </div>
      </section>

      <footer className="footer">
        <span>Exam Paper Predictor — a study prioritization tool</span>
        <span>Predictions reflect historical recurrence, not guarantees.</span>
      </footer>
    </>
  );
}
