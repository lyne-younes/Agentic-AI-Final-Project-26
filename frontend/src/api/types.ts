// Mirrors the backend's Pydantic response models (backend/app/*/schemas.py).

export type CourseStatus = "active" | "completed";

export interface Course {
  id: number;
  name: string;
  semester: string;
  year: number;
  description: string | null;
  icon_url: string | null;
  status: CourseStatus;
  created_at: string;
  material_count: number;
}

/** GET /courses adds what a library card shows; the single-course endpoints don't. */
export interface CourseListItem extends Course {
  materials_pending: number;
  materials_failed: number;
  quiz_count: number;
  flashcard_set_count: number;
  last_activity_at: string | null;
  last_chat_session_id: number | null;
  last_chat_at: string | null;
}

export interface CourseInput {
  name: string;
  semester: string;
  year: number;
  description: string | null;
}

export type MaterialType = "pdf" | "docx" | "text_file" | "authored_note";

export type IndexingStatus = "pending" | "indexed" | "failed";

export interface Material {
  id: number;
  course_id: number;
  type: MaterialType;
  title: string;
  tags: string[];
  indexing_status: IndexingStatus;
  created_at: string;
  updated_at: string;
}

export interface MaterialDetail extends Material {
  raw_text: string;
}

export interface MaterialUpdate {
  title?: string;
  tags?: string[];
  content?: string; // authored notes only
}

export interface ChatSession {
  id: number;
  course_id: number | null;
  type: "course_chat" | "study_planner";
  title: string;
  created_at: string;
  last_message_at: string | null;
}

/** Content an assistant message's turn created, shown as a result card in the chat. */
export interface CreatedItem {
  kind: "quiz" | "flashcards" | "summary";
  id: number;
  title: string;
  count: number | null; // questions or cards
  format: QuizFormat | null; // quizzes only
  difficulty: QuizDifficulty | null; // quizzes only
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  handled_by: string[] | null;
  follow_ups: string[] | null; // Q&A's suggested next questions (assistant messages only)
  created_at: string;
  created_items: CreatedItem[];
}

/** Reply from POST /chat/sessions/{id}/messages. */
export interface AgentReply {
  status: "done" | "needs_clarification";
  message: string;
  handled_by: string[] | null;
  follow_ups: string[];
}

export interface Summary {
  id: number;
  course_id: number;
  content: string;
  is_edited: boolean;
  updated_at: string;
}

export interface SummaryHistoryEntry {
  id: number;
  content: string;
  version_number: number;
  archived_at: string;
}

export type QuizFormat = "mcq" | "true_false" | "short_answer" | "mixed";
export type QuizDifficulty = "easy" | "medium" | "hard";
export type QuestionType = "mcq" | "true_false" | "short_answer";

export interface Quiz {
  id: number;
  course_id: number;
  title: string;
  format: QuizFormat;
  difficulty: QuizDifficulty;
  created_at: string;
}

/** GET /courses/{id}/quizzes adds what a Study Tools row shows. */
export interface QuizListItem extends Quiz {
  question_count: number;
  attempt_count: number;
  best_score: number | null; // null until the first attempt
  last_score: number | null;
  last_attempt_at: string | null;
}

export interface QuizQuestion {
  id: number;
  question_text: string;
  question_type: QuestionType;
  options: string[] | null;
  order: number;
}

export interface QuizDetail extends Quiz {
  questions: QuizQuestion[];
}

export type ChatSource = "quiz_explain" | "quiz_flashcards";

/** A chat the quiz page opened for an attempt, and for flashcards the set it made there. */
export interface AttemptStudyLink {
  kind: ChatSource;
  chat_session_id: number;
  created_at: string;
  flashcard_set: { id: number; title: string; card_count: number } | null;
}

export interface QuizAttempt {
  id: number;
  score: number;
  attempted_at: string;
  has_answers: boolean; // false for attempts taken before answers were saved (score only)
  study_links: AttemptStudyLink[]; // oldest first
}

export interface QuizAnswerInput {
  question_id: number;
  answer: string;
}

export interface QuizAnswerResult {
  question_id: number;
  given_answer: string;
  correct_answer: string;
  is_correct: boolean;
}

/** A graded attempt: what submitting returns, and what reviewing a past attempt returns. */
export interface QuizAttemptResult {
  id: number;
  score: number;
  attempted_at: string;
  has_answers: boolean; // false (and `answers` empty) for a score-only attempt
  answers: QuizAnswerResult[];
}

export interface FlashcardSet {
  id: number;
  course_id: number;
  title: string;
  created_at: string;
}

export interface FlashcardSetListItem extends FlashcardSet {
  card_count: number;
}

export interface Flashcard {
  id: number;
  front_text: string;
  back_text: string;
  order: number;
}

export interface FlashcardSetDetail extends FlashcardSet {
  cards: Flashcard[];
}

/** GET /leaderboard: one quiz with its whole attempt history (oldest first). */
export interface LeaderboardEntry {
  quiz_id: number;
  title: string;
  course_id: number;
  course_name: string;
  course_status: CourseStatus;
  format: QuizFormat;
  difficulty: QuizDifficulty;
  question_count: number;
  created_at: string;
  attempts: QuizAttempt[];
}
