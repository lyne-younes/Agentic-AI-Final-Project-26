# Import every model here so Base.metadata is complete for Alembic.
from app.models.chat import (
    ChatMessage,
    ChatSession,
    ChatSessionSource,
    ChatSessionType,
    MessageRole,
)
from app.models.course import Course, CourseStatus
from app.models.flashcard import Flashcard, FlashcardSet
from app.models.material import IndexingStatus, Material, MaterialType
from app.models.material_chunk import MaterialChunk
from app.models.quiz import (
    QuestionType,
    Quiz,
    QuizAttempt,
    QuizDifficulty,
    QuizFormat,
    QuizQuestion,
)
from app.models.study_plan import (
    CalendarEventResolution,
    StudentPreferences,
    StudyPlan,
    StudyPlanSession,
    StudyPlanStatus,
)
from app.models.summary import Summary, SummaryHistory
from app.models.user import User, UserSession

__all__ = [
    "CalendarEventResolution",
    "ChatMessage",
    "ChatSession",
    "ChatSessionSource",
    "ChatSessionType",
    "Course",
    "CourseStatus",
    "Flashcard",
    "FlashcardSet",
    "IndexingStatus",
    "Material",
    "MaterialChunk",
    "MaterialType",
    "MessageRole",
    "QuestionType",
    "Quiz",
    "QuizAttempt",
    "QuizDifficulty",
    "QuizFormat",
    "QuizQuestion",
    "StudentPreferences",
    "StudyPlan",
    "StudyPlanSession",
    "StudyPlanStatus",
    "Summary",
    "SummaryHistory",
    "User",
    "UserSession",
]
