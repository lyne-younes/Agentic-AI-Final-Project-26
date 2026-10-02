import { CornerDownRight, GraduationCap, Layers, NotepadText, SquareStack } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";
import { Link } from "react-router";
import type { ChatMessage, CreatedItem, QuizFormat } from "../../../api/types";
import { useAuth } from "../../../auth/AuthContext";
import { Markdown } from "../../../components/Markdown";
import { initials, pluralize } from "../../../lib/format";

interface ChatMessageListProps {
  messages: ChatMessage[];
  pendingQuestion: string | null; // shown optimistically while the agent works
  /** Course chats link result cards to the course's Study Tools and Notes; the planner has none. */
  courseId?: number;
  /** Sends a suggested follow-up question. Offered under the latest reply only. */
  onFollowUp?: (question: string) => void;
}

// Agent-attribution badge: which agent(s) contributed.
const AGENT_LABELS: Record<string, string> = {
  qa_agent: "Q&A",
  study_tools_agent: "Study Tools",
  summary_agent: "Summary",
  study_planner_agent: "Study Planner",
  verifier_agent: "Verifier", // checked a quiz or flashcard set against the materials
  plan_verifier: "Plan Verifier", // checked a study plan against the calendar and sleep hours
  orchestrator: "Assistant", // the orchestrator asked its own clarifying question
};

const QUESTION_LABELS: Record<QuizFormat, string> = {
  mcq: "multiple-choice question",
  true_false: "true/false question",
  short_answer: "short-answer question",
  mixed: "mixed-format question",
};

export function ChatMessageList({
  messages,
  pendingQuestion,
  courseId,
  onFollowUp,
}: ChatMessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, pendingQuestion]);

  // Suggestions belong to the conversation's latest reply; older ones would be stale.
  const last = messages.at(-1);
  const followUps =
    onFollowUp && pendingQuestion === null && last?.role === "assistant"
      ? (last.follow_ups ?? [])
      : [];

  return (
    <div>
      <ol className="chat-messages" aria-live="polite">
        {messages.map((message) => (
          <MessageItem
            key={message.id}
            role={message.role}
            content={message.content}
            handledBy={message.handled_by}
            items={courseId === undefined ? [] : (message.created_items ?? [])}
            courseId={courseId}
          />
        ))}
        {followUps.length > 0 && onFollowUp && (
          <li className="chat-follow-ups">
            <p className="chat-follow-ups-label" id="follow-ups-label">
              Ask next
            </p>
            <div className="chat-follow-ups-list" role="group" aria-labelledby="follow-ups-label">
              {followUps.map((question) => (
                <button
                  key={question}
                  type="button"
                  className="chat-chip chat-follow-up"
                  onClick={() => onFollowUp(question)}
                >
                  <CornerDownRight size={14} aria-hidden="true" />
                  {question}
                </button>
              ))}
            </div>
          </li>
        )}
        {pendingQuestion !== null && (
          <>
            <MessageItem role="user" content={pendingQuestion} />
            <li className="chat-message chat-message-assistant">
              <AssistantAvatar />
              <div className="chat-thinking" role="status">
                <span className="chat-thinking-dots" aria-hidden="true">
                  <span />
                  <span />
                  <span />
                </span>
                Searching your materials…
              </div>
            </li>
          </>
        )}
      </ol>
      <div ref={endRef} />
    </div>
  );
}

function MessageItem({
  role,
  content,
  handledBy = null,
  items = [],
  courseId,
}: {
  role: ChatMessage["role"];
  content: string;
  handledBy?: string[] | null;
  items?: CreatedItem[];
  courseId?: number;
}) {
  if (role === "user") {
    return (
      <li className="chat-message chat-message-user">
        <div className="chat-bubble">{content}</div>
        <UserAvatar />
      </li>
    );
  }
  return (
    <li className="chat-message chat-message-assistant">
      <AssistantAvatar />
      <div className="chat-answer">
        <Markdown>{content}</Markdown>
        {courseId !== undefined &&
          items.map((item) => (
            <ResultCard key={`${item.kind}-${item.id}`} item={item} courseId={courseId} />
          ))}
        {handledBy && handledBy.length > 0 && (
          <div className="chat-agent-badges" aria-label="Handled by">
            {handledBy.map((agent) => (
              <span key={agent} className="chat-agent-badge">
                {AGENT_LABELS[agent] ?? agent}
              </span>
            ))}
          </div>
        )}
      </div>
    </li>
  );
}

/** What a turn created, with a way straight into it. */
function ResultCard({ item, courseId }: { item: CreatedItem; courseId: number }) {
  const base = `/courses/${courseId}`;
  let icon: ReactNode;
  let meta: string;
  let primary: { to: string; label: string };
  let secondary: { to: string; label: string } | null = null;

  if (item.kind === "quiz") {
    icon = <Layers size={20} />;
    const questions = pluralize(item.count ?? 0, QUESTION_LABELS[item.format ?? "mixed"]);
    const difficulty = item.difficulty ? capitalize(item.difficulty) : null;
    meta = difficulty ? `${questions} · ${difficulty}` : questions;
    primary = { to: `${base}/study-tools/quiz/${item.id}`, label: "Start quiz" };
    secondary = { to: `${base}/study-tools`, label: "Open in Study Tools" };
  } else if (item.kind === "flashcards") {
    icon = <SquareStack size={20} />;
    meta = pluralize(item.count ?? 0, "card");
    primary = { to: `${base}/study-tools/flashcards/${item.id}`, label: "Study cards" };
    secondary = { to: `${base}/study-tools`, label: "Open in Study Tools" };
  } else {
    icon = <NotepadText size={20} />;
    meta = "Saved to Notes";
    primary = { to: `${base}/notes`, label: "Open in Notes" };
  }

  return (
    <div className="chat-result-card">
      <span className="chat-result-icon" aria-hidden="true">
        {icon}
      </span>
      <div className="chat-result-text">
        <p className="chat-result-title">{item.title}</p>
        <p className="chat-result-meta">{meta}</p>
      </div>
      <div className="chat-result-actions">
        {secondary && (
          <Link to={secondary.to} className="btn btn-sm btn-ghost">
            {secondary.label}
          </Link>
        )}
        <Link to={primary.to} className="btn btn-sm btn-accent">
          {primary.label}
        </Link>
      </div>
    </div>
  );
}

function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function AssistantAvatar() {
  return (
    <span className="chat-avatar chat-avatar-assistant" aria-hidden="true">
      <GraduationCap size={16} />
    </span>
  );
}

function UserAvatar() {
  const { user } = useAuth();
  return (
    <span className="chat-avatar chat-avatar-user" aria-hidden="true">
      {initials(user?.name)}
    </span>
  );
}
