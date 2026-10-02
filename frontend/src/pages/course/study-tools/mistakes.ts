/** Messages the quiz results page sends to the course chat ("explain" / "make flashcards"). */

export interface Mistake {
  question: string;
  given: string;
  correct: string;
}

// The chat accepts 4000 characters (MessageCreate in backend/app/chat/schemas.py).
const MAX_MESSAGE = 3800;
const MAX_FIELD = 280;
const MAX_ITEMS = 10;
// Room for the longest intro: its fixed wording plus a clipped quiz title.
const INTRO_ROOM = 200 + MAX_FIELD;

function clip(text: string): string {
  const flat = text.replace(/\s+/g, " ").trim();
  return flat.length > MAX_FIELD ? `${flat.slice(0, MAX_FIELD - 1)}…` : flat;
}

/** The items that fit in one message after the intro, so the intro can state their true count. */
function fitting(items: string[]): string[] {
  const kept: string[] = [];
  let length = INTRO_ROOM;
  for (const item of items.slice(0, MAX_ITEMS)) {
    const line = `\n${kept.length + 1}. ${item}`;
    if (length + line.length > MAX_MESSAGE) break;
    kept.push(item);
    length += line.length;
  }
  return kept;
}

function numbered(intro: string, items: string[]): string {
  return [intro, ...items.map((item, index) => `${index + 1}. ${item}`)].join("\n");
}

export function explainMistakesPrompt(quizTitle: string, mistakes: Mistake[]): string {
  const items = fitting(
    mistakes.map(
      (m) =>
        `Question: ${clip(m.question)}\n   My answer: ${clip(m.given)}\n   Correct answer: ${clip(m.correct)}`,
    ),
  );
  const intro =
    items.length === 1
      ? `I got this question wrong in the quiz "${clip(quizTitle)}". Explain why the correct answer is right and where my answer went wrong, using my course materials:`
      : `I got these ${items.length} questions wrong in the quiz "${clip(quizTitle)}". For each one, explain why the correct answer is right and where my answer went wrong, using my course materials:`;
  return numbered(intro, items);
}

export function mistakesFlashcardsPrompt(quizTitle: string, mistakes: Mistake[]): string {
  const items = fitting(
    mistakes.map((m) => `${clip(m.question)} (correct answer: ${clip(m.correct)})`),
  );
  const cards = items.length === 1 ? "1 flashcard" : `${items.length} flashcards`;
  const intro = `Make ${cards} from my mistakes in the quiz "${clip(quizTitle)}", one card for each of these questions:`;
  return numbered(intro, items);
}
