import { Dices, Swords } from "lucide-react";
import { useEffect, useState, type CSSProperties } from "react";
import { Link } from "react-router";
import { courseColor } from "../../lib/courseColor";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import "./challenge.css";
import { pickChallenge, type Challenge, type QuizStats } from "./stats";

// Ticks slow down towards the end, like a wheel settling.
const TICK_DELAYS = [50, 50, 55, 60, 65, 70, 80, 90, 105, 120, 140, 165, 195, 230];

interface ChallengePickerProps {
  open: boolean;
  onClose: () => void;
  pool: QuizStats[];
}

/** "Pick my next challenge": spins through the quizzes and lands on a weighted pick. */
export function ChallengePicker({ open, onClose, pool }: ChallengePickerProps) {
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [showing, setShowing] = useState<QuizStats | null>(null);
  const [spinning, setSpinning] = useState(false);
  const [spinId, setSpinId] = useState(0);

  useEffect(() => {
    if (open) setSpinId((id) => id + 1);
  }, [open]);

  useEffect(() => {
    if (!open || spinId === 0) return;
    const picked = pickChallenge(pool);
    setChallenge(null);
    if (!picked) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion || pool.length === 1) {
      setShowing(picked.stats);
      setChallenge(picked);
      return;
    }

    setSpinning(true);
    const timers: number[] = [];
    let elapsed = 0;
    TICK_DELAYS.forEach((delay, tick) => {
      elapsed += delay;
      timers.push(
        window.setTimeout(() => {
          const last = tick === TICK_DELAYS.length - 1;
          setShowing(last ? picked.stats : pool[Math.floor(Math.random() * pool.length)]);
          if (last) {
            setSpinning(false);
            setChallenge(picked);
          }
        }, elapsed),
      );
    });
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [open, spinId, pool]);

  const style = showing
    ? ({ "--course-color": courseColor(showing.entry.course_id) } as CSSProperties)
    : undefined;

  return (
    <Modal open={open} onClose={onClose} title="Your next challenge" size="sm">
      {pool.length === 0 ? (
        <p className="text-muted">
          No quizzes here yet. Generate one from a course's Chat tab, then come back for a
          challenge.
        </p>
      ) : (
        <div className="challenge">
          <div
            className={`challenge-reel${spinning ? " challenge-reel-spinning" : ""}${challenge ? " challenge-reel-landed" : ""}`}
            style={style}
            aria-live="polite"
            aria-busy={spinning}
          >
            {showing && (
              <>
                <span className="challenge-title">{showing.entry.title}</span>
                <span className="challenge-course">
                  <span className="course-dot" aria-hidden="true" />
                  {showing.entry.course_name} · {capitalize(showing.entry.difficulty)}
                </span>
              </>
            )}
          </div>
          <p className="challenge-reason">{challenge ? challenge.reason : "Picking…"}</p>
          <div className="modal-actions">
            <Button
              variant="ghost"
              disabled={spinning}
              onClick={() => setSpinId((id) => id + 1)}
            >
              <Dices size={16} />
              Spin again
            </Button>
            {challenge ? (
              <Link
                to={`/courses/${challenge.stats.entry.course_id}/study-tools/quiz/${challenge.stats.entry.quiz_id}`}
                className="btn btn-accent"
              >
                <Swords size={16} />
                Accept challenge
              </Link>
            ) : (
              <Button variant="accent" disabled>
                <Swords size={16} />
                Accept challenge
              </Button>
            )}
          </div>
        </div>
      )}
    </Modal>
  );
}

function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}
