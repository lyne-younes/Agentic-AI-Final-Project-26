import { CalendarDays, CalendarPlus, ExternalLink, LoaderCircle, PenLine } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useChatMessages } from "../../api/chat";
import { ApiError } from "../../api/client";
import { useCourses } from "../../api/courses";
import {
  useCreatePlannerSession,
  usePlannerSessions,
  useSendPlannerMessage,
} from "../../api/planner";
import { useAuth } from "../../auth/AuthContext";
import { EmptyState } from "../../components/ui/EmptyState";
import { ErrorState } from "../../components/ui/ErrorState";
import { ChatComposer, focusChatInput } from "../course/chat/ChatComposer";
import { ChatLayout } from "../course/chat/ChatLayout";
import { ChatMessageList } from "../course/chat/ChatMessageList";
import { ChatSessionList } from "../course/chat/ChatSessionList";
import { ChatSuggestions, type Suggestion } from "../course/chat/ChatSuggestions";
import "../course/chat/chat.css";

/** Google Calendar's week view; `authuser` picks the signed-in account. */
function googleCalendarUrl(email: string | undefined): string {
  const base = "https://calendar.google.com/calendar/r/week";
  return email ? `${base}?authuser=${encodeURIComponent(email)}` : base;
}

// Synthetic prompts, sent through the same agent endpoint as anything the student types.
const QUICK_ACTIONS: Suggestion[] = [
  {
    label: "Plan next week",
    icon: <CalendarPlus size={15} />,
    prompt: "Plan my study sessions for next week",
  },
  {
    label: "Plan the next 3 days",
    icon: <CalendarPlus size={15} />,
    prompt: "Plan my study sessions for the next 3 days",
  },
];

// Offered on an empty chat; they fill the input so the student can adjust them first.
const STARTERS = ["I have an exam on Friday — help me prepare", "I'm free most evenings, plan around that"];

/** Study Planner: global across all courses. Serves /planner and /planner/:sessionId. */
export function PlannerPage() {
  const navigate = useNavigate();
  const { sessionId: sessionParam } = useParams();
  const parsedId = sessionParam === undefined ? null : Number(sessionParam);
  const invalidSession = parsedId !== null && !Number.isInteger(parsedId);
  const sessionId = invalidSession ? null : parsedId;

  const { user } = useAuth();
  const sessions = usePlannerSessions();
  const messages = useChatMessages(sessionId);
  const courses = useCourses();
  const createSession = useCreatePlannerSession();
  const sendMessage = useSendPlannerMessage();

  const [draft, setDraft] = useState("");
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);

  useEffect(() => setSendError(null), [sessionId]);

  async function send(quickPrompt?: string) {
    const content = (quickPrompt ?? draft).trim();
    if (!content || pendingQuestion !== null) return;
    if (quickPrompt === undefined) setDraft("");
    setSendError(null);
    setPendingQuestion(content);
    try {
      let targetId = sessionId;
      if (targetId === null) {
        // Created on the first message, so empty planner chats don't pile up.
        const session = await createSession.mutateAsync();
        targetId = session.id;
        navigate(`/planner/${session.id}`, { replace: true });
      }
      await sendMessage.mutateAsync({ sessionId: targetId, content });
    } catch (error) {
      if (quickPrompt === undefined) setDraft(content); // nothing was saved; hand it back
      setSendError(
        error instanceof Error ? error.message : "Something went wrong. Please try again.",
      );
    } finally {
      setPendingQuestion(null);
    }
  }

  const notFound =
    invalidSession || (messages.error instanceof ApiError && messages.error.status === 404);
  const conversation = messages.data ?? [];
  const activeCourses = (courses.data ?? []).filter((course) => course.status === "active");
  const empty = conversation.length === 0 && pendingQuestion === null;
  const starters: Suggestion[] = STARTERS.map((starter) => ({
    label: starter,
    icon: <PenLine size={15} />,
    onPick: () => {
      setDraft(starter);
      focusChatInput();
    },
  }));

  let body: ReactNode;
  if (notFound) {
    body = (
      <EmptyState
        icon={<CalendarDays size={30} />}
        tone="slate"
        title="Plan not found"
        description="It may have been deleted."
        actions={
          <Link to="/planner" className="btn btn-primary">
            Start a new plan
          </Link>
        }
      />
    );
  } else if (messages.error) {
    body = <ErrorState message={messages.error.message} onRetry={() => void messages.refetch()} />;
  } else if (pendingQuestion === null && sessionId !== null && messages.isPending) {
    body = (
      <div className="chat-loading">
        <LoaderCircle size={22} className="spin" />
      </div>
    );
  } else if (empty) {
    body = <PlannerIntro activeCourseCount={activeCourses.length} />;
  } else {
    body = <ChatMessageList messages={conversation} pendingQuestion={pendingQuestion} />;
  }

  return (
    <ChatLayout
      label="Study planner"
      className="fill-viewport"
      history={
        <ChatSessionList
          basePath="/planner"
          sessions={sessions.data ?? []}
          loading={sessions.isPending}
          emptyHint="Your study plans will appear here."
          newLabel="New plan"
        />
      }
    >
      <div className="chat-scroll">
        <div className="chat-column">{body}</div>
      </div>
      {!notFound && (
        <div className="chat-footer">
          <div className="chat-column">
            {sendError && (
              <p className="form-error chat-error" role="alert">
                {sendError}
              </p>
            )}
            <ChatSuggestions
              suggestions={empty && activeCourses.length > 0 ? [...QUICK_ACTIONS, ...starters] : QUICK_ACTIONS}
              disabled={pendingQuestion !== null}
              onSend={(prompt) => void send(prompt)}
            >
              {/* Not a prompt: opens the real calendar, so it sits apart from the chips. */}
              <a
                href={googleCalendarUrl(user?.email)}
                target="_blank"
                rel="noopener noreferrer"
                className="chat-chip chat-chip-link"
              >
                <ExternalLink size={15} />
                Open Google Calendar
              </a>
            </ChatSuggestions>
            <ChatComposer
              value={draft}
              onChange={setDraft}
              onSend={() => void send()}
              busy={pendingQuestion !== null}
              placeholder="Ask for a study plan, e.g. “plan my revision for next week”"
            />
          </div>
        </div>
      )}
    </ChatLayout>
  );
}

function PlannerIntro({ activeCourseCount }: { activeCourseCount: number }) {
  return (
    <div className="chat-intro">
      <span className="chat-intro-icon" aria-hidden="true">
        <CalendarDays size={24} />
      </span>
      <h2>Plan your study time</h2>
      <p>
        The planner reads your Google Calendar to find your exams, deadlines and free time, then
        schedules study sessions across all your active courses. Your existing events are never
        changed. Study sessions are added only once you confirm, and a new exam or deadline only
        when you ask for it.
      </p>
      {activeCourseCount === 0 && (
        <p className="chat-intro-hint">
          You have no active courses yet. <Link to="/courses">Create one first</Link> so there's
          something to plan around.
        </p>
      )}
    </div>
  );
}
