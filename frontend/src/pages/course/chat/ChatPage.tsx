import {
  Layers,
  Lightbulb,
  LoaderCircle,
  MessageSquare,
  NotepadText,
  SquareStack,
} from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useLocation, useNavigate, useOutletContext, useParams } from "react-router";
import {
  useChatMessages,
  useChatSessions,
  useCreateChatSession,
  useSendMessage,
  type ChatOrigin,
} from "../../../api/chat";
import { ApiError } from "../../../api/client";
import { useMaterials } from "../../../api/materials";
import type { Course } from "../../../api/types";
import { EmptyState } from "../../../components/ui/EmptyState";
import { ErrorState } from "../../../components/ui/ErrorState";
import "./chat.css";
import { ChatComposer, focusChatInput } from "./ChatComposer";
import { ChatLayout } from "./ChatLayout";
import { ChatMessageList } from "./ChatMessageList";
import { ChatSessionList } from "./ChatSessionList";
import { ChatSuggestions, type Suggestion } from "./ChatSuggestions";

// Action buttons: send a pre-written prompt through the same messages endpoint.
const QUICK_ACTIONS: Suggestion[] = [
  { label: "Summarize this course", icon: <NotepadText size={15} />, prompt: "Summarize this course" },
  { label: "Generate a quiz", icon: <Layers size={15} />, prompt: "Generate a quiz for this course" },
  {
    label: "Generate flashcards",
    icon: <SquareStack size={15} />,
    prompt: "Generate flashcards for this course",
  },
];

/**
 * Another page can open a new chat with a message already on its way, e.g. the quiz results'
 * "Explain my mistakes": `navigate(".../chat", { state: { prompt } })`.
 */
export interface ChatLaunchState {
  prompt?: string;
  /** Recorded on the new chat, so the quiz attempt it came from can link back to it. */
  origin?: ChatOrigin;
}

/** Course chat: session list + active conversation. Serves /chat and /chat/:sessionId. */
export function ChatPage() {
  const course = useOutletContext<Course>();
  const navigate = useNavigate();
  const { sessionId: sessionParam } = useParams();
  const parsedId = sessionParam === undefined ? null : Number(sessionParam);
  const invalidSession = parsedId !== null && !Number.isInteger(parsedId);
  const sessionId = invalidSession ? null : parsedId;

  const sessions = useChatSessions(course.id);
  const messages = useChatMessages(sessionId);
  const materials = useMaterials(course.id);
  const createSession = useCreateChatSession(course.id);
  const sendMessage = useSendMessage(course.id);

  const [draft, setDraft] = useState("");
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);

  useEffect(() => setSendError(null), [sessionId]);

  // Send a prompt handed over by another page, once (cleared from router state first).
  const location = useLocation();
  const launched = useRef(false);
  useEffect(() => {
    const launch = location.state as ChatLaunchState | null;
    if (!launch?.prompt || launched.current) return;
    launched.current = true;
    navigate(location.pathname, { replace: true, state: null });
    void send(launch.prompt, launch.origin);
    // Keyed on the router state only: send() changes every render and must not re-trigger this.
  }, [location.state]);

  async function send(quickPrompt?: string, origin?: ChatOrigin) {
    const content = (quickPrompt ?? draft).trim();
    if (!content || pendingQuestion !== null) return;
    if (quickPrompt === undefined) setDraft("");
    setSendError(null);
    setPendingQuestion(content);
    try {
      let targetId = sessionId;
      if (targetId === null) {
        // A new chat is created on its first message, so empty chats don't pile up.
        const session = await createSession.mutateAsync(origin);
        targetId = session.id;
        navigate(`/courses/${course.id}/chat/${session.id}`, { replace: true });
      }
      await sendMessage.mutateAsync({ sessionId: targetId, content });
    } catch (error) {
      if (quickPrompt === undefined) setDraft(content); // nothing saved, hand it back for a retry
      setSendError(error instanceof Error ? error.message : "Something went wrong. Please try again.");
    } finally {
      setPendingQuestion(null);
    }
  }

  const notFound =
    invalidSession || (messages.error instanceof ApiError && messages.error.status === 404);
  const conversation = messages.data ?? [];
  const firstMaterial = materials.data?.[0]?.title;
  const empty = conversation.length === 0 && pendingQuestion === null;

  let body: ReactNode;
  if (notFound) {
    body = (
      <EmptyState
        icon={<MessageSquare size={30} />}
        tone="slate"
        title="Chat not found"
        description="It may have been deleted, or it belongs to a different course."
        actions={
          <Link to={`/courses/${course.id}/chat`} className="btn btn-primary">
            Start a new chat
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
    body = <ChatIntro course={course} hasMaterials={(materials.data ?? []).length > 0} />;
  } else {
    body = (
      <ChatMessageList
        messages={conversation}
        pendingQuestion={pendingQuestion}
        courseId={course.id}
        onFollowUp={(question) => void send(question)}
      />
    );
  }

  // An empty chat also offers to explain something; it fills the input rather than sending.
  const explain: Suggestion = {
    label: "Explain a concept",
    icon: <Lightbulb size={15} />,
    onPick: () => {
      setDraft(firstMaterial ? `Explain the key ideas in "${firstMaterial}"` : "Explain ");
      focusChatInput();
    },
  };

  return (
    <ChatLayout
      label="Course chat"
      history={
        <ChatSessionList
          basePath={`/courses/${course.id}/chat`}
          sessions={sessions.data ?? []}
          loading={sessions.isPending}
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
              suggestions={empty ? [...QUICK_ACTIONS, explain] : QUICK_ACTIONS}
              disabled={pendingQuestion !== null}
              onSend={(prompt) => void send(prompt)}
            />
            <ChatComposer
              value={draft}
              onChange={setDraft}
              onSend={() => void send()}
              busy={pendingQuestion !== null}
              placeholder={`Ask a question about ${course.name}`}
            />
          </div>
        </div>
      )}
    </ChatLayout>
  );
}

function ChatIntro({ course, hasMaterials }: { course: Course; hasMaterials: boolean }) {
  return (
    <div className="chat-intro">
      <span className="chat-intro-icon" aria-hidden="true">
        <MessageSquare size={24} />
      </span>
      <h2>Ask anything about {course.name}</h2>
      <p>
        Answers come from your uploaded materials. When something isn't covered, the assistant tells
        you it's answering from general knowledge.
      </p>
      {!hasMaterials && (
        <p className="chat-intro-hint">
          This course has no materials yet.{" "}
          <Link to={`/courses/${course.id}/materials`}>Upload some first</Link> so the assistant has
          something to work from.
        </p>
      )}
    </div>
  );
}
