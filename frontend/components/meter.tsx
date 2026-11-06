/** Probability meter: thin single-hue bar (magnitude), square baseline,
 *  4px rounded data-end; value stays in ink, never in the data color. */
export function Meter({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div className="meter" role="img" aria-label={`${pct} percent`}>
      <div className="track">
        <div className="fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="val">{pct}%</span>
    </div>
  );
}
