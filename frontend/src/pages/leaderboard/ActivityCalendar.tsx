import { useMemo, useRef, useState, type KeyboardEvent } from "react";
import { activityLevel, calendarWeeks, dayKey } from "./stats";

const WEEKS = 13;
const DAY_LABELS = ["Mon", "", "Wed", "", "Fri", "", ""];
const longDate = new Intl.DateTimeFormat(undefined, {
  weekday: "short",
  month: "short",
  day: "numeric",
});
const monthLabel = new Intl.DateTimeFormat(undefined, { month: "short" });

interface ActivityCalendarProps {
  counts: Map<string, number>; // attempts per local day, already filtered
  selectedDay: string | null;
  onSelectDay: (day: string | null) => void;
}

/** The last 13 weeks, one cell per day shaded by attempts. Picking a day filters the list. */
export function ActivityCalendar({ counts, selectedDay, onSelectDay }: ActivityCalendarProps) {
  const columns = useMemo(() => calendarWeeks(WEEKS), []);
  const days = useMemo(() => columns.flat(), [columns]);
  const todayIndex = days.reduce((last, day, index) => (day ? index : last), 0);
  const [focusIndex, setFocusIndex] = useState(todayIndex);
  const [hovered, setHovered] = useState<number | null>(null);
  const cellRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const total = days.reduce((sum, day) => sum + (day ? (counts.get(dayKey(day)) ?? 0) : 0), 0);
  const activeDays = days.filter((day) => day && counts.has(dayKey(day))).length;

  function move(event: KeyboardEvent, index: number) {
    const step = { ArrowUp: -1, ArrowDown: 1, ArrowLeft: -7, ArrowRight: 7 }[event.key];
    if (step === undefined) return;
    event.preventDefault();
    const next = index + step;
    if (next < 0 || next >= days.length || days[next] === null) return;
    setFocusIndex(next);
    cellRefs.current[next]?.focus();
  }

  const tip = hovered !== null ? days[hovered] : null;
  const tipCount = tip ? (counts.get(dayKey(tip)) ?? 0) : 0;

  return (
    <section className="lb-card calendar-card" aria-labelledby="calendar-heading">
      <div className="lb-card-header">
        <h2 id="calendar-heading" className="lb-section-title">
          Activity
        </h2>
        <span className="text-subtle">
          {total} {total === 1 ? "attempt" : "attempts"} on {activeDays}{" "}
          {activeDays === 1 ? "day" : "days"} · last {WEEKS} weeks
        </span>
      </div>

      <div className="calendar">
        <div className="calendar-months" aria-hidden="true">
          {columns.map((column, index) => {
            const first = column[0];
            const previous = columns[index - 1]?.[0];
            const show = first && (!previous || previous.getMonth() !== first.getMonth());
            return <span key={index}>{show ? monthLabel.format(first) : ""}</span>;
          })}
        </div>
        <div className="calendar-body">
          <div className="calendar-weekdays" aria-hidden="true">
            {DAY_LABELS.map((label, index) => (
              <span key={index}>{label}</span>
            ))}
          </div>
          <div className="calendar-grid" role="group" aria-label="Attempts per day">
            {days.map((day, index) => {
              if (!day) return <span key={index} className="calendar-cell calendar-cell-future" />;
              const key = dayKey(day);
              const count = counts.get(key) ?? 0;
              const selected = selectedDay === key;
              return (
                <button
                  key={index}
                  ref={(element) => {
                    cellRefs.current[index] = element;
                  }}
                  type="button"
                  className={`calendar-cell heat-${activityLevel(count)}`}
                  tabIndex={index === focusIndex ? 0 : -1}
                  aria-pressed={selected}
                  aria-label={`${longDate.format(day)}: ${count} ${count === 1 ? "attempt" : "attempts"}`}
                  onClick={() => onSelectDay(selected ? null : key)}
                  onKeyDown={(event) => move(event, index)}
                  onFocus={() => {
                    setFocusIndex(index);
                    setHovered(index);
                  }}
                  onBlur={() => setHovered(null)}
                  onPointerEnter={() => setHovered(index)}
                  onPointerLeave={() => setHovered(null)}
                  style={{ gridColumn: Math.floor(index / 7) + 1, gridRow: (index % 7) + 1 }}
                />
              );
            })}
            {tip && hovered !== null && (
              <div
                className="chart-tooltip calendar-tooltip"
                style={{
                  gridColumn: Math.floor(hovered / 7) + 1,
                  gridRow: (hovered % 7) + 1,
                }}
                aria-hidden="true"
              >
                <strong>
                  {tipCount} {tipCount === 1 ? "attempt" : "attempts"}
                </strong>
                <span>{longDate.format(tip)}</span>
              </div>
            )}
          </div>
        </div>
        <div className="calendar-legend" aria-hidden="true">
          <span>Less</span>
          {[0, 1, 2, 3, 4].map((level) => (
            <span key={level} className={`calendar-cell heat-${level}`} />
          ))}
          <span>More</span>
          <span className="calendar-legend-hint">Pick a day to filter</span>
        </div>
      </div>
    </section>
  );
}
