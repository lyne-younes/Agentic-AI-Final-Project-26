/** A score out of 100 as a small ring: the track is a lighter step of the fill's hue. */
export function ScoreRing({ score, label = "Best score" }: { score: number; label?: string }) {
  const radius = 16;
  const circumference = 2 * Math.PI * radius;
  return (
    <span className="score-ring" title={`${label} ${Math.round(score)}%`}>
      <svg width={40} height={40} viewBox="0 0 40 40" aria-hidden="true">
        <circle className="score-ring-track" cx={20} cy={20} r={radius} />
        <circle
          className="score-ring-fill"
          cx={20}
          cy={20}
          r={radius}
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - score / 100)}
        />
      </svg>
      <span className="score-ring-value">
        {Math.round(score)}
        <span className="visually-hidden">% {label.toLowerCase()}</span>
      </span>
    </span>
  );
}
