import { Navigate, Route, Routes } from "react-router";
import { RequireAuth } from "./auth/RequireAuth";
import { AppLayout } from "./components/layout/AppLayout";
import { ChatPage } from "./pages/course/chat/ChatPage";
import { CourseLayout } from "./pages/course/CourseLayout";
import { MaterialsPage } from "./pages/course/materials/MaterialsPage";
import { NotesPage } from "./pages/course/notes/NotesPage";
import { FlashcardSetPage } from "./pages/course/study-tools/FlashcardSetPage";
import { QuizPage } from "./pages/course/study-tools/QuizPage";
import { StudyToolsPage } from "./pages/course/study-tools/StudyToolsPage";
import { CoursesPage } from "./pages/courses/CoursesPage";
import { LeaderboardPage } from "./pages/leaderboard/LeaderboardPage";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { PlannerPage } from "./pages/planner/PlannerPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/courses" replace />} />
          <Route path="/courses" element={<CoursesPage />} />
          <Route path="/courses/:courseId" element={<CourseLayout />}>
            <Route index element={<Navigate to="materials" replace />} />
            <Route path="materials" element={<MaterialsPage />} />
            <Route path="notes" element={<NotesPage />} />
            <Route path="study-tools" element={<StudyToolsPage />} />
            <Route path="study-tools/quiz/:quizId" element={<QuizPage />} />
            <Route path="study-tools/flashcards/:setId" element={<FlashcardSetPage />} />
            {/* One route for /chat and /chat/:sessionId, so starting a chat doesn't remount the page. */}
            <Route path="chat/:sessionId?" element={<ChatPage />} />
          </Route>
          {/* One route for /planner and /planner/:sessionId, so starting a plan doesn't remount. */}
          <Route path="/planner/:sessionId?" element={<PlannerPage />} />
          {/* Global like the planner: ranks quizzes across every course. */}
          <Route path="/leaderboard" element={<LeaderboardPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
