from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.auth.dependencies import CurrentUser, DbSession
from app.chat import created_items
from app.courses.dependencies import OwnedCourse
from app.models import ChatSession, ChatSessionSource, Course, Quiz, QuizAttempt, QuizQuestion
from app.quizzes.schemas import (
    AttemptStudyLink,
    LeaderboardEntry,
    LinkedFlashcardSet,
    QuizAnswerResult,
    QuizAttemptCreate,
    QuizAttemptOut,
    QuizAttemptResult,
    QuizDetail,
    QuizListItem,
    QuizOut,
    QuizQuestionOut,
)

router = APIRouter(tags=["quizzes"])


async def get_owned_quiz(quiz_id: int, user: CurrentUser, db: DbSession) -> Quiz:
    quiz = await db.scalar(
        select(Quiz)
        .join(Course, Course.id == Quiz.course_id)
        .where(Quiz.id == quiz_id, Course.user_id == user.id)
    )
    if quiz is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quiz not found")
    return quiz


OwnedQuiz = Annotated[Quiz, Depends(get_owned_quiz)]


@router.get("/courses/{course_id}/quizzes")
async def list_quizzes(course: OwnedCourse, db: DbSession) -> list[QuizListItem]:
    question_count = (
        select(func.count())
        .where(QuizQuestion.quiz_id == Quiz.id)
        .correlate(Quiz)
        .scalar_subquery()
    )
    attempts = (
        select(
            QuizAttempt.quiz_id,
            func.count().label("attempt_count"),
            func.max(QuizAttempt.score).label("best_score"),
            func.max(QuizAttempt.attempted_at).label("last_attempt_at"),
        )
        .group_by(QuizAttempt.quiz_id)
        .subquery()
    )
    last_score = (
        select(QuizAttempt.score)
        .where(QuizAttempt.quiz_id == Quiz.id)
        .order_by(QuizAttempt.attempted_at.desc(), QuizAttempt.id.desc())
        .limit(1)
        .correlate(Quiz)
        .scalar_subquery()
    )
    rows = await db.execute(
        select(
            Quiz,
            question_count,
            attempts.c.attempt_count,
            attempts.c.best_score,
            last_score,
            attempts.c.last_attempt_at,
        )
        .outerjoin(attempts, attempts.c.quiz_id == Quiz.id)
        .where(Quiz.course_id == course.id)
        .order_by(Quiz.created_at.desc(), Quiz.id.desc())
    )
    return [
        QuizListItem(
            **QuizOut.model_validate(quiz).model_dump(),
            question_count=questions,
            attempt_count=attempt_count or 0,
            best_score=float(best) if best is not None else None,
            last_score=float(last) if last is not None else None,
            last_attempt_at=last_at,
        )
        for quiz, questions, attempt_count, best, last, last_at in rows.all()
    ]


@router.get("/leaderboard")
async def leaderboard(user: CurrentUser, db: DbSession) -> list[LeaderboardEntry]:
    """Every quiz across the student's courses, with all its attempts (if any)."""
    question_count = (
        select(func.count())
        .where(QuizQuestion.quiz_id == Quiz.id)
        .correlate(Quiz)
        .scalar_subquery()
    )
    rows = (
        await db.execute(
            select(Quiz, Course, question_count)
            .join(Course, Course.id == Quiz.course_id)
            .where(Course.user_id == user.id)
            .order_by(Quiz.id)
        )
    ).all()
    attempts = await db.scalars(
        select(QuizAttempt)
        .where(QuizAttempt.quiz_id.in_([quiz.id for quiz, _, _ in rows]))
        .order_by(QuizAttempt.attempted_at, QuizAttempt.id)
    )
    by_quiz: dict[int, list[QuizAttemptOut]] = {}
    for attempt in attempts:
        by_quiz.setdefault(attempt.quiz_id, []).append(
            QuizAttemptOut(
                id=attempt.id,
                score=float(attempt.score),
                attempted_at=attempt.attempted_at,
                has_answers=attempt.answers is not None,
            )
        )
    return [
        LeaderboardEntry(
            quiz_id=quiz.id,
            title=quiz.title,
            course_id=course.id,
            course_name=course.name,
            course_status=course.status,
            format=quiz.format,
            difficulty=quiz.difficulty,
            question_count=count,
            created_at=quiz.created_at,
            attempts=by_quiz.get(quiz.id, []),
        )
        for quiz, course, count in rows
    ]


@router.get("/quizzes/{quiz_id}")
async def get_quiz(quiz: OwnedQuiz, db: DbSession) -> QuizDetail:
    questions = await db.scalars(
        select(QuizQuestion).where(QuizQuestion.quiz_id == quiz.id).order_by(QuizQuestion.order)
    )
    return QuizDetail(
        **QuizOut.model_validate(quiz).model_dump(),
        questions=[QuizQuestionOut.model_validate(question) for question in questions],
    )


@router.get("/quizzes/{quiz_id}/attempts")
async def list_attempts(quiz: OwnedQuiz, db: DbSession) -> list[QuizAttemptOut]:
    attempts = list(
        await db.scalars(
            select(QuizAttempt)
            .where(QuizAttempt.quiz_id == quiz.id)
            .order_by(QuizAttempt.attempted_at.desc(), QuizAttempt.id.desc())
        )
    )
    links = await _study_links(db, quiz, [attempt.id for attempt in attempts])
    return [
        QuizAttemptOut(
            id=attempt.id,
            score=float(attempt.score),
            attempted_at=attempt.attempted_at,
            has_answers=attempt.answers is not None,
            study_links=links.get(attempt.id, []),
        )
        for attempt in attempts
    ]


async def _study_links(
    db: DbSession, quiz: Quiz, attempt_ids: list[int]
) -> dict[int, list[AttemptStudyLink]]:
    """The chats opened from these attempts, and the flashcard set each one made."""
    if not attempt_ids:
        return {}
    sessions = list(
        await db.scalars(
            select(ChatSession)
            .where(ChatSession.source_quiz_attempt_id.in_(attempt_ids))
            .order_by(ChatSession.id)
        )
    )
    flashcard_chats = [s.id for s in sessions if s.source_kind == ChatSessionSource.quiz_flashcards]
    made = await created_items.first_item_by_session(db, quiz.course_id, flashcard_chats)

    links: dict[int, list[AttemptStudyLink]] = {}
    for session in sessions:
        item = made.get(session.id)
        links.setdefault(session.source_quiz_attempt_id, []).append(
            AttemptStudyLink(
                kind=session.source_kind.value,
                chat_session_id=session.id,
                created_at=session.created_at,
                flashcard_set=(
                    LinkedFlashcardSet(id=item.id, title=item.title, card_count=item.count or 0)
                    if item is not None and item.kind == "flashcards"
                    else None
                ),
            )
        )
    return links


@router.get("/quizzes/{quiz_id}/attempts/{attempt_id}")
async def get_attempt(attempt_id: int, quiz: OwnedQuiz, db: DbSession) -> QuizAttemptResult:
    """One past attempt, graded again for review: what was answered and what was right."""
    attempt = await db.scalar(
        select(QuizAttempt).where(QuizAttempt.id == attempt_id, QuizAttempt.quiz_id == quiz.id)
    )
    if attempt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attempt not found")
    if attempt.answers is None:
        return QuizAttemptResult(
            id=attempt.id,
            score=float(attempt.score),
            attempted_at=attempt.attempted_at,
            has_answers=False,
            answers=[],
        )
    correct_by_id = dict(
        (
            await db.execute(
                select(QuizQuestion.id, QuizQuestion.correct_answer).where(
                    QuizQuestion.quiz_id == quiz.id
                )
            )
        ).all()
    )
    return QuizAttemptResult(
        id=attempt.id,
        score=float(attempt.score),
        attempted_at=attempt.attempted_at,
        answers=[
            QuizAnswerResult(
                question_id=answer["question_id"],
                given_answer=answer["given_answer"],
                correct_answer=correct_by_id.get(answer["question_id"], ""),
                is_correct=answer["is_correct"],
            )
            for answer in attempt.answers
        ],
    )


@router.post("/quizzes/{quiz_id}/attempts", status_code=status.HTTP_201_CREATED)
async def submit_attempt(
    body: QuizAttemptCreate, quiz: OwnedQuiz, db: DbSession
) -> QuizAttemptResult:
    """Grades immediately: a trimmed, case-insensitive comparison with `correct_answer`."""
    questions = list(
        await db.scalars(
            select(QuizQuestion).where(QuizQuestion.quiz_id == quiz.id).order_by(QuizQuestion.order)
        )
    )
    given_by_id = {answer.question_id: answer.answer for answer in body.answers}
    if given_by_id.keys() != {question.id for question in questions}:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Answers must cover exactly this quiz's questions, once each",
        )

    graded: list[QuizAnswerResult] = []
    correct_count = 0
    for question in questions:
        given = given_by_id[question.id]
        is_correct = _is_correct(given, question.correct_answer)
        correct_count += is_correct
        graded.append(
            QuizAnswerResult(
                question_id=question.id,
                given_answer=given,
                correct_answer=question.correct_answer,
                is_correct=is_correct,
            )
        )
    score = round(100 * correct_count / len(questions), 2) if questions else 0.0

    attempt = QuizAttempt(
        quiz_id=quiz.id,
        score=score,
        answers=[
            {
                "question_id": answer.question_id,
                "given_answer": answer.given_answer,
                "is_correct": answer.is_correct,
            }
            for answer in graded
        ],
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)
    return QuizAttemptResult(
        id=attempt.id, score=float(attempt.score), attempted_at=attempt.attempted_at, answers=graded
    )


def _is_correct(given: str, correct: str) -> bool:
    return given.strip().casefold() == correct.strip().casefold()
